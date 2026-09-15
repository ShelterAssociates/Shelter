"""Building photo zips, for both the instant single-household download and the
queued slum-level export.

Zip layout is always:

    <slum name>/<household number>/<photo category>/<file>

Photos are stored with ZIP_STORED, not ZIP_DEFLATED: they are already-compressed
JPEGs, so deflating them costs real CPU on a multi-GB archive for essentially no
size saving.
"""

import io
import logging
import os
import re
import shutil
import time
import zipfile

import requests
from django.conf import settings

from avni import media as avni_media
from photos.services import sources

logger = logging.getLogger(__name__)

# Measured mean across sampled photos; used only to estimate an export's size
# before starting it, so the disk precheck can refuse early.
AVERAGE_PHOTO_BYTES = 424 * 1024
DISK_ESTIMATE_MARGIN = 1.15

DOWNLOAD_TIMEOUT_SECONDS = 60
DOWNLOAD_CHUNK_BYTES = 256 * 1024

# On 403/429 Avni is throttling us; back off rather than hammering it.
THROTTLE_BACKOFF_SECONDS = (30, 60, 120)

_UNSAFE_PATH_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def safe_path_component(value, fallback="unknown"):
    """Make one path segment safe without slugging it into unreadability --
    these folder names are read by humans opening the zip."""
    text = _UNSAFE_PATH_CHARS.sub(" ", str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(". ")
    return text or fallback


def photo_extension(photo):
    """Preserve the real extension from the source URL/path, defaulting to .jpg."""
    candidate = photo.get("raw_url") or photo.get("url") or ""
    candidate = candidate.split("?")[0]
    ext = os.path.splitext(candidate)[1].lower()
    if ext and len(ext) <= 6 and re.match(r"^\.[a-z0-9]+$", ext):
        return ext
    return ".jpg"


def zip_member_name(slum_name, household_number, photo, used_names):
    """<slum>/<household>/<category>/<file>, de-duplicated."""
    label = photo.get("label") or "Photo"
    # "Photo of Agreement 2" -> category "Photo of Agreement", file "...2.jpg"
    category = re.sub(r"\s+\d+$", "", label).strip() or label
    name = "{}/{}/{}/{}{}".format(
        safe_path_component(slum_name, "slum"),
        safe_path_component(household_number, "household"),
        safe_path_component(category, "photos"),
        safe_path_component(label, "photo"),
        photo_extension(photo),
    )
    if name in used_names:
        base, ext = os.path.splitext(name)
        index = 2
        while "{} ({}){}".format(base, index, ext) in used_names:
            index += 1
        name = "{} ({}){}".format(base, index, ext)
    used_names.add(name)
    return name


def estimate_bytes(photo_count):
    return int(photo_count * AVERAGE_PHOTO_BYTES * DISK_ESTIMATE_MARGIN)


def free_disk_bytes(path=None):
    target = path or getattr(settings, "MEDIA_ROOT", None) or "/"
    # Walk up until we hit something that exists -- MEDIA_ROOT may not be
    # created yet on a fresh checkout.
    while target and not os.path.exists(target):
        parent = os.path.dirname(target.rstrip("/"))
        if parent == target:
            break
        target = parent
    return shutil.disk_usage(target or "/").free


def check_disk_space(photo_count, path=None):
    """(ok, message). Refuses before anything is downloaded.

    Kobo photos already sit on this disk, so zipping them writes a second copy
    of the same bytes -- they are counted here, not treated as free.
    """
    min_free_gb = getattr(settings, "PHOTO_EXPORT_MIN_FREE_GB", 10)
    needed = estimate_bytes(photo_count)
    free = free_disk_bytes(path)
    remaining = free - needed
    floor = min_free_gb * 1024 ** 3
    if remaining < floor:
        return False, (
            "Not enough disk space: this export needs about {:.1f} GB, only "
            "{:.1f} GB is free, and {:.0f} GB must stay free. Free up space and "
            "re-run the export.".format(
                needed / 1024 ** 3, free / 1024 ** 3, min_free_gb
            )
        )
    return True, ""


def _fetch_avni_photo(signed_url, write_to, failures_ctx):
    """Stream one Avni photo, backing off if Avni starts throttling."""
    last_error = None
    for attempt, backoff in enumerate((0,) + THROTTLE_BACKOFF_SECONDS):
        if backoff:
            logger.warning(
                "Avni throttling (%s); backing off %ss before retry %s",
                failures_ctx, backoff, attempt,
            )
            time.sleep(backoff)
        try:
            response = requests.get(
                signed_url, stream=True, timeout=DOWNLOAD_TIMEOUT_SECONDS
            )
            if response.status_code in (403, 429):
                last_error = "Avni returned {}".format(response.status_code)
                response.close()
                continue
            if response.status_code != 200:
                response.close()
                return False, "HTTP {}".format(response.status_code)
            for chunk in response.iter_content(DOWNLOAD_CHUNK_BYTES):
                if chunk:
                    write_to.write(chunk)
            response.close()
            return True, None
        except requests.RequestException as exc:
            last_error = str(exc)
    return False, last_error or "download failed"


def write_photos_to_zip(zip_file, entries, failures, progress=None):
    """Add every photo to an open ZipFile.

    `entries` is [{slum_name, household_number, photo}]. Kobo entries are
    written first by the caller so that a legacy-heavy export finishes fast and
    an Avni outage still produces a useful zip.

    One unreachable photo is recorded in `failures` and skipped -- it must never
    abort a several-thousand-photo export.
    """
    used_names = set()
    written = 0
    total_bytes = 0

    # Sign Avni photos in one batch (one token, parallel) instead of per photo.
    avni_raw = [
        entry["photo"]["raw_url"]
        for entry in entries
        if entry["photo"].get("source") == sources.SOURCE_AVNI
    ]
    signed = avni_media.sign_urls(avni_raw) if avni_raw else {}

    for entry in entries:
        photo = entry["photo"]
        member = zip_member_name(
            entry["slum_name"], entry["household_number"], photo, used_names
        )
        context = "{}/{}".format(entry["household_number"], photo.get("label"))
        try:
            if photo.get("source") == sources.SOURCE_KOBO:
                abs_path = photo.get("abs_path")
                if not abs_path or not os.path.exists(abs_path):
                    failures.append(
                        {
                            "household": entry["household_number"],
                            "label": photo.get("label"),
                            "error": "file missing on server",
                        }
                    )
                    continue
                zip_file.write(abs_path, member)
                total_bytes += os.path.getsize(abs_path)
            else:
                raw = photo["raw_url"]
                signed_url = signed.get(raw, raw)
                buffer = io.BytesIO()
                ok, error = _fetch_avni_photo(signed_url, buffer, context)
                if not ok:
                    failures.append(
                        {
                            "household": entry["household_number"],
                            "label": photo.get("label"),
                            "error": error,
                        }
                    )
                    continue
                data = buffer.getvalue()
                zip_file.writestr(member, data)
                total_bytes += len(data)
            written += 1
            if progress and written % 50 == 0:
                progress(written, total_bytes)
        except Exception as exc:  # noqa: BLE001 - one bad photo must not stop the run
            logger.exception("Failed adding photo %s", context)
            failures.append(
                {
                    "household": entry["household_number"],
                    "label": photo.get("label"),
                    "error": str(exc),
                }
            )
    return written, total_bytes


def build_zip_bytes(entries):
    """In-memory zip, for the instant single-household download only.

    Bulk exports must never use this -- they stream to a file on disk.
    """
    failures = []
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zip_file:
        written, total_bytes = write_photos_to_zip(zip_file, entries, failures)
    return buffer.getvalue(), written, failures
