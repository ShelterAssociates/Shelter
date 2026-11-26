"""When a batch zip is deleted, and what the pages show once it is gone."""

import datetime
import os

from django.conf import settings
from django.utils import timezone

CLEANUP_HOUR = 5
EXPIRED_MESSAGE = "This download has been deleted by the nightly cleanup. Generate it again from the batch page."


def export_root():
    return os.path.join(settings.MEDIA_ROOT, getattr(settings, "PLATES_EXPORT_DIR_NAME", "plate_exports"))


def delete_after(finished_on):
    """The first nightly cleanup (05:00 IST) at or after finished_on + 24 h."""
    earliest = timezone.localtime(finished_on + datetime.timedelta(hours=24))
    cleanup = earliest.replace(hour=CLEANUP_HOUR, minute=0, second=0, microsecond=0)
    if cleanup < earliest:
        cleanup += datetime.timedelta(days=1)
    return cleanup


def available_until(batch):
    """"28 Nov 2026, 05:00" or ""."""
    if not batch.delete_after:
        return ""
    local = timezone.localtime(batch.delete_after)
    return "{} {}".format(local.day, local.strftime("%b %Y, %H:%M"))


def file_exists(batch):
    return bool(batch.file_path) and os.path.isfile(batch.file_path)


def expire_if_gone(batch):
    """Mark a done batch expired when its zip is no longer on disk. True when it is (now) expired."""
    if batch.status == "expired":
        return True
    if batch.status != "done" or file_exists(batch):
        return False
    from plates.models import PlateBatch

    PlateBatch.objects.filter(pk=batch.pk, status="done").update(status="expired")
    batch.status = "expired"
    return True
