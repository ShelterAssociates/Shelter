import base64
import io
import json
import logging
import re
import zipfile
from datetime import date

import requests
from Crypto import Random
from Crypto.Cipher import AES
from PIL import Image
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from master.models import Slum


logger = logging.getLogger(__name__)

DEFAULT_IMAGE_QUALITY = 72
DEFAULT_IMAGE_MAX_WIDTH = 1600
DEFAULT_IMAGE_MAX_HEIGHT = 1600
DEFAULT_UPLOAD_TIMEOUT = 180
DEFAULT_UPLOAD_RETRY_COUNT = 2
PHOTO_CATEGORY_LABELS = {
    "mobilization": "Mobilization",
    "toilet": "Toilet",
    "mhm": "MHM",
    "gis_map": "GIS Map",
    "events": "Events",
    "other": "Other",
}


def clean_drive_name(value):
    cleaned_value = re.sub(r"[\\/:*?\"<>|]+", "_", str(value or "").strip())
    cleaned_value = re.sub(r"\s+", " ", cleaned_value)
    return cleaned_value or "Unknown"


def get_upload_context(photo_category, event_name=None):
    category_key = str(photo_category or "").strip().lower()
    if category_key not in PHOTO_CATEGORY_LABELS:
        raise ImproperlyConfigured("A valid photo category is required for photo upload.")

    details_value = clean_drive_name(event_name) if event_name else ""
    if category_key in ("events", "other") and not details_value:
        raise ImproperlyConfigured("Event name is required for Events and Other photo uploads.")

    category_folder = details_value or PHOTO_CATEGORY_LABELS[category_key]
    return {
        "category_key": category_key,
        "category_label": PHOTO_CATEGORY_LABELS[category_key],
        "category_folder": category_folder,
        "details": details_value,
    }


def build_upload_file_name(index, original_name):
    extension = ""
    original_name = str(original_name or "")
    if "." in original_name:
        extension = "." + original_name.rsplit(".", 1)[1].lower()
    if not extension:
        extension = ".jpg"
    return "{}_{}{}".format(date.today().isoformat(), index, extension)


def get_slum_hierarchy(slum):
    electoral_ward = slum.electoral_ward
    administrative_ward = electoral_ward.administrative_ward if electoral_ward else None
    city = administrative_ward.city if administrative_ward else None

    return {
        "city": clean_drive_name(city.name.city_name if city and city.name else None),
        "administrative_ward": clean_drive_name(administrative_ward.name if administrative_ward else None),
        "electoral_ward": clean_drive_name(electoral_ward.name if electoral_ward else None),
        "slum": clean_drive_name(slum.name),
    }


class BinaryAESCipher(object):
    def __init__(self):
        cipher_key = getattr(settings, "CIPHER_KEY", None)
        if not cipher_key:
            raise ImproperlyConfigured("CIPHER_KEY is required for photo upload encryption.")
        self.block_size = 16
        self.key = cipher_key.encode("utf-8")

    def encrypt_bytes(self, raw_bytes):
        raw_bytes = self._pad(raw_bytes)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw_bytes)).decode("utf-8")

    def decrypt_bytes(self, encrypted_text):
        encrypted_bytes = base64.b64decode(encrypted_text)
        iv = encrypted_bytes[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(encrypted_bytes[AES.block_size:]))

    def _pad(self, raw_bytes):
        pad_length = self.block_size - len(raw_bytes) % self.block_size
        return raw_bytes + bytes([pad_length]) * pad_length

    @staticmethod
    def _unpad(padded_bytes):
        return padded_bytes[:-padded_bytes[-1]]


def compress_uploaded_image(uploaded_file):
    uploaded_file.seek(0)
    try:
        image = Image.open(uploaded_file)
        image.load()
    except Exception:
        uploaded_file.seek(0)
        return uploaded_file.read(), uploaded_file.name, uploaded_file.content_type or "application/octet-stream"

    image_format = image.format or "JPEG"
    image_format = image_format.upper()
    if image.mode not in ("RGB", "L") and image_format in ("JPEG", "JPG"):
        image = image.convert("RGB")

    image.thumbnail((DEFAULT_IMAGE_MAX_WIDTH, DEFAULT_IMAGE_MAX_HEIGHT), Image.ANTIALIAS)

    output = io.BytesIO()
    save_kwargs = {"format": image_format}
    if image_format in ("JPEG", "JPG"):
        save_kwargs["quality"] = DEFAULT_IMAGE_QUALITY
        save_kwargs["optimize"] = True
    elif image_format == "PNG":
        save_kwargs["optimize"] = True

    image.save(output, **save_kwargs)
    content_type = uploaded_file.content_type or Image.MIME.get(image_format, "application/octet-stream")
    return output.getvalue(), uploaded_file.name, content_type


def build_encrypted_zip_payload(uploaded_files):
    zip_buffer = io.BytesIO()
    file_summaries = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for index, uploaded_file in enumerate(uploaded_files, start=1):
            compressed_bytes, file_name, content_type = compress_uploaded_image(uploaded_file)
            safe_file_name = clean_drive_name(build_upload_file_name(index, file_name))
            zip_file.writestr(safe_file_name, compressed_bytes)
            file_summaries.append({
                "name": safe_file_name,
                "original_name": clean_drive_name(file_name),
                "content_type": content_type,
                "size": len(compressed_bytes),
            })

    zip_bytes = zip_buffer.getvalue()
    encrypted_zip = BinaryAESCipher().encrypt_bytes(zip_bytes)
    return encrypted_zip, file_summaries, len(zip_bytes)


def post_to_upload_service(payload):
    upload_service_url = getattr(settings, "PHOTO_UPLOAD_SERVICE_URL", None)
    upload_service_secret = getattr(settings, "PHOTO_UPLOAD_SERVICE_SECRET", None)
    timeout = getattr(settings, "PHOTO_UPLOAD_SERVICE_TIMEOUT", DEFAULT_UPLOAD_TIMEOUT)
    retry_count = getattr(settings, "PHOTO_UPLOAD_SERVICE_RETRY_COUNT", DEFAULT_UPLOAD_RETRY_COUNT)

    if not upload_service_url or not upload_service_secret:
        raise ImproperlyConfigured(
            "PHOTO_UPLOAD_SERVICE_URL and PHOTO_UPLOAD_SERVICE_SECRET must be set in local_settings.py."
        )

    last_exception = None
    headers = {
        "X-UPLOAD-KEY": upload_service_secret,
        "Content-Type": "application/json",
    }

    for attempt in range(retry_count + 1):
        try:
            response = requests.post(
                upload_service_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            if response.status_code in (200, 201, 202):
                try:
                    return response.json()
                except ValueError:
                    return {"message": response.text}

            if attempt == retry_count:
                raise Exception(
                    "Upload service returned status {}: {}".format(
                        response.status_code,
                        response.text[:500],
                    )
                )
        except requests.exceptions.RequestException as exc:
            last_exception = exc
            logger.warning("Photo upload service attempt %s failed: %s", attempt + 1, exc)
            if attempt == retry_count:
                raise

    if last_exception:
        raise last_exception

    raise Exception("Photo upload service failed without a response.")


def upload_photos_to_slum_drive_folder(slum_id, uploaded_files, photo_category, event_name=None):
    slum = Slum.objects.select_related(
        "electoral_ward__administrative_ward__city__name"
    ).get(id=slum_id)
    hierarchy = get_slum_hierarchy(slum)
    upload_context = get_upload_context(photo_category, event_name)
    encrypted_zip, files, zip_size = build_encrypted_zip_payload(uploaded_files)

    location = dict(hierarchy)
    location.update({
        "photo_category": upload_context["category_key"],
        "photo_category_label": upload_context["category_label"],
        "photo_category_folder": upload_context["category_folder"],
        "event_name": upload_context["details"],
    })

    payload = {
        "slum_id": slum.id,
        "location": location,
        "zip_file": encrypted_zip,
        "zip_file_name": "{}_{}_{}.zip".format(
            hierarchy["city"],
            hierarchy["slum"],
            upload_context["category_folder"],
        ),
        "files": files,
        "meta": {
            "source": "shelter_django",
            "zip_size": zip_size,
            "file_count": len(files),
            "photo_category": upload_context["category_key"],
            "photo_category_label": upload_context["category_label"],
            "photo_category_folder": upload_context["category_folder"],
            "event_name": upload_context["details"],
        },
    }

    service_response = post_to_upload_service(payload)
    logger.info(
        "Photo upload forwarded for slum_id=%s city=%s slum=%s file_count=%s",
        slum.id,
        hierarchy["city"],
        hierarchy["slum"],
        len(files),
    )

    return {
        "slum_id": slum.id,
        "slum_name": slum.name,
        "hierarchy": [
            hierarchy["city"],
            hierarchy["administrative_ward"],
            hierarchy["electoral_ward"],
            hierarchy["slum"],
            upload_context["category_folder"],
        ],
        "photo_category": upload_context["category_key"],
        "photo_category_label": upload_context["category_label"],
        "photo_category_folder": upload_context["category_folder"],
        "event_name": upload_context["details"],
        "files": files,
        "upload_service_response": service_response,
    }
