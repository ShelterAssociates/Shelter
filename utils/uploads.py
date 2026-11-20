import os
import zipfile

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from PIL import Image

PDF_EXTENSIONS = ["pdf"]
DOCUMENT_EXTENSIONS = ["pdf", "jpg", "jpeg", "png"]
IMAGE_EXTENSIONS = ["jpg", "jpeg", "jfif", "png"]
ZIP_EXTENSIONS = ["zip"]
_IMAGE_FORMAT_BY_EXTENSION = {"jpg": "JPEG", "jpeg": "JPEG", "jfif": "JPEG", "png": "PNG"}


def file_extension(name):
    return os.path.splitext(name or "")[1].lower().lstrip(".")


def _head(upload, size=1024):
    upload.seek(0)
    head = upload.read(size)
    upload.seek(0)
    return head


def validate_pdf(upload):
    FileExtensionValidator(PDF_EXTENSIONS)(upload)
    if b"%PDF-" not in _head(upload):
        raise ValidationError("This file is not a valid PDF.")


def validate_image(upload):
    """Expects a file already opened by forms.ImageField (it sets `upload.image`)."""
    FileExtensionValidator(IMAGE_EXTENSIONS)(upload)
    image = getattr(upload, "image", None)
    expected = _IMAGE_FORMAT_BY_EXTENSION[file_extension(upload.name)]
    if image is None or image.format != expected:
        raise ValidationError("Upload a JPG or PNG image whose extension matches its type.")


def validate_document(upload):
    """Project documents: a real PDF, JPG/JPEG or PNG whose extension matches its content."""
    FileExtensionValidator(DOCUMENT_EXTENSIONS)(upload)
    ext = file_extension(upload.name)
    if ext == "pdf":
        validate_pdf(upload)
        return
    upload.seek(0)
    try:
        image = Image.open(upload)
        image.verify()
        detected = image.format
    except Exception:
        detected = None
    finally:
        upload.seek(0)
    if detected != _IMAGE_FORMAT_BY_EXTENSION[ext]:
        raise ValidationError("This file is not a valid %s image." % ext.upper())


def validate_zip(upload):
    FileExtensionValidator(ZIP_EXTENSIONS)(upload)
    upload.seek(0)
    is_zip = zipfile.is_zipfile(upload)
    upload.seek(0)
    if not is_zip:
        raise ValidationError("This file is not a valid ZIP archive.")
