import base64
import io
import json
import logging
import re
import zipfile
import uuid
from datetime import date, datetime

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


def clean_drive_name(value):
    cleaned_value = re.sub(r"[\\/:*?\"<>|]+", "_", str(value or "").strip())
    cleaned_value = re.sub(r"\s+", " ", cleaned_value)
    return cleaned_value or "Unknown"


def parse_photo_date(photo_date_value):
    if isinstance(photo_date_value, date):
        parsed_date = photo_date_value
    else:
        photo_date_value = str(photo_date_value or "").strip()
        if not photo_date_value:
            raise ImproperlyConfigured("photo_date is required for photo upload.")
        try:
            parsed_date = datetime.strptime(photo_date_value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ImproperlyConfigured("photo_date must be a valid date in YYYY-MM-DD format.") from exc

    if parsed_date > date.today():
        raise ImproperlyConfigured("photo_date cannot be in the future.")

    return parsed_date


def get_upload_context(photo_type_item):
    if photo_type_item is None:
        raise ImproperlyConfigured("A valid photo category is required for photo upload.")

    if hasattr(photo_type_item, "path_nodes"):
        path_nodes = photo_type_item.path_nodes()
        item_name = getattr(photo_type_item, "name", "")
    else:
        # Accept a plain string path for compatibility with older callers.
        path_nodes = []
        item_name = str(photo_type_item or "").strip()
        for part in [piece.strip() for piece in item_name.split("/") if piece.strip()]:
            path_nodes.append(type("Node", (), {"name": part})())

    path_parts = [clean_drive_name(node.name) for node in path_nodes if getattr(node, "name", None)]
    if not path_parts:
        raise ImproperlyConfigured("A valid photo category is required for photo upload.")

    path_display = " / ".join(path_parts)
    return {
        "category_label": path_parts[-1],
        "category_folder": path_parts[-1],
        "category_path": path_parts,
        "category_path_display": path_display,
        "details": item_name,
    }


def build_drive_path(
    photo_date,
    photo_type_item=None,
    slum=None,
    city=None,
    is_city_level=False,
    is_other_upload=False,
    custom_folder_name="",
):
    photo_date_value = parse_photo_date(photo_date)
    date_folder = photo_date_value.isoformat()

    if is_other_upload:
        custom_folder = clean_drive_name(custom_folder_name)
        if custom_folder == "Unknown":
            raise ImproperlyConfigured("A custom folder name is required for other photo upload.")

        folder_parts = [custom_folder, date_folder]
        return {
            "mode": "other",
            "photo_date": date_folder,
            "drive_path_parts": folder_parts,
            "drive_path_display": " / ".join(folder_parts),
            "root_folder": custom_folder,
            "city_name": "",
            "slum_folder": "",
            "category_path_parts": [],
            "category_path_display": "",
            "category_label": "",
            "category_folder": "",
            "custom_folder_name": custom_folder,
        }

    upload_context = get_upload_context(photo_type_item)
    category_path_parts = upload_context["category_path"]

    if is_city_level:
        if city is None:
            raise ImproperlyConfigured("A city is required for city level photo upload.")

        city_name = clean_drive_name(getattr(getattr(city, "name", None), "city_name", None))
        folder_parts = [city_name] + category_path_parts + [date_folder]
        return {
            "mode": "city_level",
            "photo_date": date_folder,
            "drive_path_parts": folder_parts,
            "drive_path_display": " / ".join(folder_parts),
            "root_folder": city_name,
            "city_name": city_name,
            "slum_folder": "",
            "category_path_parts": category_path_parts,
            "category_path_display": upload_context["category_path_display"],
            "category_label": upload_context["category_label"],
            "category_folder": upload_context["category_folder"],
            "custom_folder_name": "",
        }

    if slum is None:
        raise ImproperlyConfigured("A slum is required for photo upload.")

    hierarchy = get_slum_hierarchy(slum)
    slum_folder = clean_drive_name(
        "{}_{}_{}".format(
            hierarchy["slum"],
            hierarchy["administrative_ward"],
            hierarchy["electoral_ward"],
        )
    )
    folder_parts = [hierarchy["city"], slum_folder] + category_path_parts + [date_folder]
    return {
        "mode": "normal",
        "photo_date": date_folder,
        "drive_path_parts": folder_parts,
        "drive_path_display": " / ".join(folder_parts),
        "root_folder": hierarchy["city"],
        "city_name": hierarchy["city"],
        "slum_folder": slum_folder,
        "category_path_parts": category_path_parts,
        "category_path_display": upload_context["category_path_display"],
        "category_label": upload_context["category_label"],
        "category_folder": upload_context["category_folder"],
        "custom_folder_name": "",
    }


def merge_service_file_links(files, service_response):
    service_files = []
    if isinstance(service_response, dict):
        candidate_files = service_response.get("files")
        if isinstance(candidate_files, list):
            service_files = candidate_files

    files_by_name = {}
    for service_file in service_files:
        if not isinstance(service_file, dict):
            continue
        service_name = clean_drive_name(service_file.get("name") or service_file.get("file_name") or "")
        if service_name:
            files_by_name[service_name] = service_file

    for index, file_info in enumerate(files):
        service_file = {}
        by_name = files_by_name.get(clean_drive_name(file_info.get("name")))
        if isinstance(by_name, dict):
            service_file = by_name
        elif index < len(service_files) and isinstance(service_files[index], dict):
            service_file = service_files[index]

        file_info["web_view_link"] = service_file.get("web_view_link") or service_file.get("webViewLink") or ""
        file_info["web_content_link"] = service_file.get("web_content_link") or service_file.get("webContentLink") or ""
        file_info["drive_file_id"] = service_file.get("drive_file_id") or service_file.get("driveFileId") or ""

        # Keep backward compatibility with existing frontend keys.
        file_info["webViewLink"] = file_info["web_view_link"]
        file_info["webContentLink"] = file_info["web_content_link"]
        file_info["driveFileId"] = file_info["drive_file_id"]

    return files


def build_upload_file_name(original_name):
    extension = ""
    original_name = str(original_name or "")
    if "." in original_name:
        extension = "." + original_name.rsplit(".", 1)[1].lower()
    if not extension:
        extension = ".jpg"
    return "{}{}".format(uuid.uuid4(), extension)


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
            safe_file_name = clean_drive_name(build_upload_file_name(file_name))
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

    print("\n========== PHOTO UPLOAD SERVICE ==========")
    print("Upload URL:", upload_service_url)
    print("Timeout:", timeout)
    print("Retry Count:", retry_count)
    print("Payload:", payload)

    if not upload_service_url or not upload_service_secret:
        print("ERROR: Upload service configuration missing")
        raise ImproperlyConfigured(
            "PHOTO_UPLOAD_SERVICE_URL and PHOTO_UPLOAD_SERVICE_SECRET must be set in local_settings.py."
        )

    last_exception = None

    headers = {
        "X-UPLOAD-KEY": upload_service_secret,
        "Content-Type": "application/json",
    }

    print("Headers:", {
        "X-UPLOAD-KEY": "***hidden***",
        "Content-Type": "application/json",
    })

    for attempt in range(retry_count + 1):
        try:
            print(f"\nAttempt {attempt + 1}/{retry_count + 1}")

            response = requests.post(
                upload_service_url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            print("Response Status Code:", response.status_code)
            print("Response Headers:", dict(response.headers))
            print("Response Text:", response.text[:1000])

            if response.status_code in (200, 201, 202):
                print("SUCCESS: Upload service call successful")

                try:
                    response_json = response.json()
                    print("Parsed JSON Response:", response_json)
                    return response_json

                except ValueError:
                    print("WARNING: Response is not JSON")
                    return {"message": response.text}

            print(
                "ERROR: Upload service returned bad status:",
                response.status_code,
            )

            if attempt == retry_count:
                raise Exception(
                    "Upload service returned status {}: {}".format(
                        response.status_code,
                        response.text[:500],
                    )
                )

        except requests.exceptions.RequestException as exc:
            last_exception = exc

            print("EXCEPTION OCCURRED:")
            print(str(exc))

            if attempt == retry_count:
                print("ERROR: All retry attempts exhausted")
                raise

    if last_exception:
        print("Raising last exception:", str(last_exception))
        raise last_exception

    print("ERROR: Upload service failed without a response")
    raise Exception("Photo upload service failed without a response.")

def upload_photos_to_slum_drive_folder(
    slum_id=None,
    uploaded_files=None,
    photo_type_item=None,
    sponsor_project_id=None,
    photo_date=None,
    is_city_level=False,
    is_other_upload=False,
    custom_folder_name="",
    city_id=None,
):
    slum = None
    city = None
    if slum_id:
        slum = Slum.objects.select_related(
            "electoral_ward__administrative_ward__city__name"
        ).get(id=slum_id)
        if slum.electoral_ward and slum.electoral_ward.administrative_ward:
            city = slum.electoral_ward.administrative_ward.city
    elif city_id:
        from master.models import City

        city = City.objects.select_related("name").filter(id=city_id).first()

    drive_context = build_drive_path(
        photo_date=photo_date,
        photo_type_item=photo_type_item,
        slum=slum,
        city=city,
        is_city_level=is_city_level,
        is_other_upload=is_other_upload,
        custom_folder_name=custom_folder_name,
    )
    encrypted_zip, files, zip_size = build_encrypted_zip_payload(uploaded_files)

    hierarchy = drive_context["drive_path_parts"]
    location = {
        "city": drive_context["city_name"],
        "slum": drive_context["slum_folder"],
        "photo_category": drive_context["category_label"],
        "photo_category_label": drive_context["category_label"],
        "photo_category_folder": drive_context["category_folder"],
        "photo_category_path": drive_context["category_path_display"],
        "photo_date": drive_context["photo_date"],
        "event_name": "",
    }
    sponsor_name = ""
    sponsor_project_name = ""
    if sponsor_project_id:
        from sponsor.models import SponsorProject

        sponsor_project = SponsorProject.objects.select_related("sponsor").filter(id=sponsor_project_id).first()
        if sponsor_project:
            sponsor_project_name = sponsor_project.name or ""
            sponsor_name = sponsor_project.sponsor.organization_name if sponsor_project.sponsor else ""

    location.update({
        "sponsor_project": sponsor_project_name,
        "sponsor_name": sponsor_name,
        "custom_folder_name": drive_context["custom_folder_name"],
        "drive_path_display": drive_context["drive_path_display"],
        "drive_path_parts": hierarchy,
        "is_city_level": is_city_level,
        "is_other_upload": is_other_upload,
    })

    payload = {
        "slum_id": slum.id if slum else None,
        "location": location,
        "zip_file": encrypted_zip,
        "zip_file_name": clean_drive_name("{}_{}.zip".format(drive_context["root_folder"], drive_context["photo_date"])),
        "files": files,
        "meta": {
            "source": "shelter_django",
            "zip_size": zip_size,
            "file_count": len(files),
            "photo_date": drive_context["photo_date"],
            "is_city_level": is_city_level,
            "is_other_upload": is_other_upload,
            "custom_folder_name": drive_context["custom_folder_name"],
            "drive_path_display": drive_context["drive_path_display"],
            "drive_path_parts": hierarchy,
            "photo_category": drive_context["category_label"],
            "photo_category_label": drive_context["category_label"],
            "photo_category_folder": drive_context["category_folder"],
            "photo_category_path": drive_context["category_path_display"],
            "photo_category_path_parts": drive_context["category_path_parts"],
            "event_name": "",
            "sponsor_project": sponsor_project_name,
            "sponsor_name": sponsor_name,
        },
    }

    service_response = post_to_upload_service(payload)
    files = merge_service_file_links(files, service_response)
    slum_name = slum.name if slum else ""
    city_name = drive_context["city_name"]
    slum_log_value = slum.id if slum else getattr(city, "id", None)
    logger.info(
        "Photo upload forwarded for slum_id=%s city=%s slum=%s file_count=%s",
        slum_log_value,
        city_name,
        drive_context["slum_folder"] or slum_name,
        len(files),
    )

    return {
        "slum_id": slum.id if slum else None,
        "slum_name": slum_name,
        "city_id": getattr(city, "id", None),
        "city_name": drive_context["city_name"],
        "hierarchy": hierarchy,
        "drive_path_display": drive_context["drive_path_display"],
        "drive_path_parts": hierarchy,
        "photo_date": drive_context["photo_date"],
        "is_city_level": is_city_level,
        "is_other_upload": is_other_upload,
        "custom_folder_name": drive_context["custom_folder_name"],
        "photo_category": drive_context["category_label"],
        "photo_category_label": drive_context["category_label"],
        "photo_category_folder": drive_context["category_folder"],
        "photo_category_path": drive_context["category_path_display"],
        "photo_category_path_parts": drive_context["category_path_parts"],
        "event_name": "",
        "sponsor_project": sponsor_project_name,
        "sponsor_name": sponsor_name,
        "files": files,
        "upload_service_response": service_response,
    }
