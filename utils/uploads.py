import os
import re
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


PHOTO_MAX_BYTES = 20 * 1024 * 1024
PHOTO_FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png")}


def inspect_photo(upload):
    """Returns the Pillow format of a JPEG/PNG upload whose extension matches its content and size cap."""
    name = getattr(upload, "name", "") or "file"
    if file_extension(name) not in IMAGE_EXTENSIONS:
        raise ValidationError("%s: only JPG and PNG photos can be uploaded." % name)
    if upload.size > PHOTO_MAX_BYTES:
        raise ValidationError("%s: larger than %d MB." % (name, PHOTO_MAX_BYTES // (1024 * 1024)))
    try:
        upload.seek(0)
        image = Image.open(upload)
        image.verify()
        image_format = image.format
    except Exception:
        raise ValidationError("%s: not a valid JPG or PNG image." % name)
    finally:
        upload.seek(0)
    if image_format not in PHOTO_FORMATS or _IMAGE_FORMAT_BY_EXTENSION[file_extension(name)] != image_format:
        raise ValidationError("%s: the file content is not a %s image." % (name, file_extension(name).upper()))
    return image_format


SPREADSHEET_EXTENSIONS = ["xls", "xlsx"]
SPREADSHEET_MAX_BYTES = 10 * 1024 * 1024
SPREADSHEET_MAX_UNZIPPED_BYTES = 100 * 1024 * 1024
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_DTD_MARKUP = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)


def _xml_text(data):
    if data[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in data[:4]:
        return data.decode("utf-16", "ignore")
    return data.decode("utf-8", "ignore")


def validate_spreadsheet(upload):
    """A real, size-capped .xls/.xlsx. Excel never writes a DOCTYPE, and xlrd expands entities."""
    if not upload:
        raise ValidationError("Choose an .xls or .xlsx file.")
    extension = file_extension(upload.name)
    if extension not in SPREADSHEET_EXTENSIONS:
        raise ValidationError("Only .xls and .xlsx files are accepted.")
    if upload.size > SPREADSHEET_MAX_BYTES:
        raise ValidationError("The file is larger than %d MB." % (SPREADSHEET_MAX_BYTES // (1024 * 1024)))
    try:
        if extension == "xls":
            if _head(upload, len(_OLE_MAGIC)) != _OLE_MAGIC:
                raise ValidationError("This file is not a real .xls workbook.")
            return
        upload.seek(0)
        if not zipfile.is_zipfile(upload):
            raise ValidationError("This file is not a real .xlsx workbook.")
        upload.seek(0)
        with zipfile.ZipFile(upload) as archive:
            members = archive.infolist()
            if sum(member.file_size for member in members) > SPREADSHEET_MAX_UNZIPPED_BYTES:
                raise ValidationError("The workbook is too large once unpacked.")
            for member in members:
                if member.filename.endswith((".xml", ".rels")) and _DTD_MARKUP.search(_xml_text(archive.read(member))):
                    raise ValidationError("Workbooks with DOCTYPE or ENTITY declarations are not accepted.")
    finally:
        upload.seek(0)
