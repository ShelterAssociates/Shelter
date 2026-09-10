"""Running queued photo exports.

Deliberately a cron-driven management command rather than the background thread
the RIM and GIS exports use. Deploying restarts gunicorn (`service shelter
restart`), which SIGKILLs in-flight threads; a slum export takes tens of minutes,
and because those exports record nothing, a killed one vanishes with no error and
nobody can be told. A job row survives the restart and an orphan sweep turns
"killed mid-run" into an actual notification.
"""

import logging
import os
import shutil
import tempfile
import uuid
import zipfile

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from helpers.models import ExportRequest
from photos.services import collect, email as export_email, export

logger = logging.getLogger(__name__)

EXPORT_DIR_NAME = "photo_exports"


def export_root():
    return os.path.join(settings.MEDIA_ROOT, EXPORT_DIR_NAME)


def claim_next_job():
    """Claim the oldest queued photo export, or None.

    select_for_update(skip_locked=True) is the single-job lock: two overlapping
    cron ticks cannot claim the same row, and a second runner simply finds
    nothing to do rather than blocking.
    """
    with transaction.atomic():
        job = (
            ExportRequest.objects.select_for_update(skip_locked=True)
            .filter(export_type="photo", status="queued")
            .order_by("created_on")
            .first()
        )
        if job is None:
            return None
        job.status = "running"
        job.started_on = timezone.now()
        job.save(update_fields=["status", "started_on"])
        return job


def sweep_orphans():
    """Fail jobs left 'running' by a restart, and report them.

    This is the payoff of having a job table: a thread killed by a deploy could
    never tell anyone it died.
    """
    hours = getattr(settings, "PHOTO_EXPORT_STUCK_HOURS", 3)
    cutoff = timezone.now() - timezone.timedelta(hours=hours)
    orphans = list(
        ExportRequest.objects.filter(
            export_type="photo", status="running", started_on__lt=cutoff
        )
    )
    for job in orphans:
        job.status = "failed"
        job.error = (
            "Export stopped unexpectedly (most likely a server restart or "
            "deploy while it was running). Re-run it from the admin."
        )
        job.finished_on = timezone.now()
        job.save(update_fields=["status", "error", "finished_on"])
        logger.error("Photo export %s marked failed: orphaned", job.pk)
        export_email.send_failure_email(job)
    return len(orphans)


def run_job(job):
    """Build one export's zip and email the outcome."""
    close_old_connections()
    failures = []
    try:
        params = job.params or {}
        photo_types = params.get("photo_types") or None
        slum = job.slum
        records = collect.slum_household_records(
            slum.id,
            household_numbers=params.get("household_numbers"),
            date_field=params.get("date_field"),
            fy_start_year=params.get("financial_year"),
        )
        if not records:
            _finish_failed(job, "No households matched this request.")
            return job

        estimated = collect.estimate_slum_photo_count(records, photo_types)
        ok, message = check_disk_or_fail(job, estimated)
        if not ok:
            return job

        entries = _gather_entries(records, slum, photo_types, failures)
        if not entries:
            _finish_failed(
                job,
                "No photos matched this request. The selected photo types may "
                "not exist for these households.",
            )
            return job

        # Re-check disk now that the real count is known.
        ok, message = check_disk_or_fail(job, len(entries))
        if not ok:
            return job

        file_path, written, total_bytes = _write_zip(job, slum, entries, failures)

        job.status = "done"
        job.file_path = file_path
        job.item_count = written
        job.bytes_total = total_bytes
        job.failures = failures
        job.finished_on = timezone.now()
        job.save()
        export_email.send_success_email(job)
        logger.info(
            "Photo export %s done: %s photos, %s bytes, %s failures",
            job.pk, written, total_bytes, len(failures),
        )
    except Exception as exc:  # noqa: BLE001 - must always record and report
        logger.exception("Photo export %s failed", job.pk)
        job.failures = failures
        _finish_failed(job, str(exc))
    finally:
        # The RIM export omits this and leaks a PG connection per run.
        close_old_connections()
    return job


def check_disk_or_fail(job, photo_count):
    ok, message = check_disk(photo_count)
    if not ok:
        _finish_failed(job, message)
    return ok, message


def check_disk(photo_count):
    return export.check_disk_space(photo_count, export_root())


def _gather_entries(records, slum, photo_types, failures):
    """Kobo households first: they are local file copies needing no Avni call,
    so a legacy-heavy slum finishes fast and an Avni outage still yields a
    useful zip."""
    from photos.services import sources

    kobo_entries, avni_entries = [], []
    for record in records:
        groups, error = collect.household_groups(record)
        if error:
            failures.append(
                {
                    "household": record.household_number,
                    "label": "-",
                    "error": error,
                }
            )
            continue
        entries = collect.entries_from_groups(
            groups, slum.name, record.household_number, photo_types
        )
        for entry in entries:
            if entry["photo"].get("source") == sources.SOURCE_KOBO:
                kobo_entries.append(entry)
            else:
                avni_entries.append(entry)
    return kobo_entries + avni_entries


def _write_zip(job, slum, entries, failures):
    """Write to a temp file, then rename into place so a half-written zip is
    never downloadable."""
    export_id = uuid.uuid4().hex
    directory = os.path.join(export_root(), export_id)
    os.makedirs(directory, exist_ok=True)
    filename = "{}-photos.zip".format(
        export.safe_path_component(slum.name, "slum").replace(" ", "-").lower()
    )
    final_path = os.path.join(directory, filename)

    temp_fd, temp_path = tempfile.mkstemp(suffix=".zip", dir=directory)
    os.close(temp_fd)
    try:
        def progress(written, total_bytes):
            ok, _message = check_disk(0)
            if not ok:
                raise RuntimeError(
                    "Ran out of disk space partway through the export."
                )
            ExportRequest.objects.filter(pk=job.pk).update(
                item_count=written, bytes_total=total_bytes
            )

        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_STORED, allowZip64=True) as zf:
            written, total_bytes = export.write_photos_to_zip(
                zf, entries, failures, progress=progress
            )
        os.rename(temp_path, final_path)
        return final_path, written, os.path.getsize(final_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        shutil.rmtree(directory, ignore_errors=True)
        raise


def _finish_failed(job, message):
    job.status = "failed"
    job.error = message
    job.finished_on = timezone.now()
    job.save()
    logger.error("Photo export %s failed: %s", job.pk, message)
    export_email.send_failure_email(job)
