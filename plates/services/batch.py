"""The plate_batch job (run by the cron queue runner) and the batch life cycle: confirm, cancel, generate again,
and catching batches whose run was stopped by the orphan sweep."""

import io
import logging
import os
import shutil
import tempfile
import uuid
import zipfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.db import transaction
from django.utils import timezone

from notification.models import JobRequest
from notification.services import queue
from plates.models import PlateBatch
from plates.services import check, email, excel, naming, retention
from plates.services.render import PlateRenderer, save_png, with_options
from plates.services.resources import Resources

logger = logging.getLogger(__name__)

JOB_KEY = "plate_batch"
PROGRESS_EVERY = 100
REPORT_LIMIT = 200
LOW_DISK = "The server is low on space, so this batch was not started. Nothing was made. Please contact the tech team."
DISK_RAN_OUT = "The server ran out of space during the run, so the batch was stopped. Please contact the tech team."
RESTARTED = "The batch stopped because the server restarted. Nothing was lost; press Generate again."
UNEXPECTED = "The batch stopped because of an unexpected error. Please contact the tech team."


class BatchError(ValueError):
    pass


class Stopped(Exception):
    pass


def enough_disk():
    root = retention.export_root()
    os.makedirs(root, exist_ok=True)
    return shutil.disk_usage(root).free >= float(getattr(settings, "PLATES_MIN_FREE_DISK_GB", 5)) * 1024 ** 3


def batch_spec(batch):
    """The batch's template version with its drill-hole and side-panel choices applied."""
    return with_options(batch.template.spec(), holes=batch.holes, side_panel=batch.side_panel)


def checked_batch(batch, resources=None):
    """(renderer, CheckResult) for the batch's stored Excel and template version."""
    sheet = excel.read_sheet(batch.upload.path, batch.sheet_name)
    renderer = PlateRenderer(batch_spec(batch), resources or Resources.from_database())
    return renderer, check.check_sheet(sheet, batch.plate_type, renderer)


def run(recorder, params):
    """Job entry point (registry key plate_batch); params = {"batch": "<public_id>"}."""
    batch = PlateBatch.objects.select_related("template").filter(public_id=(params or {}).get("batch")).first()
    if batch is None:
        raise ValueError("Plate batch {} does not exist".format((params or {}).get("batch")))
    claimed = PlateBatch.objects.filter(pk=batch.pk, status="queued").update(status="running", started_on=timezone.now())
    batch.refresh_from_db()
    if not claimed:
        recorder.set_window("Plate batch {} is {}; nothing to do".format(batch.pk, batch.status))
        return
    recorder.set_window("{} plate batch {} ({} rows)".format(batch.get_plate_type_display(), batch.pk, batch.row_count))
    with recorder.step("plates") as step:
        try:
            make(batch, step)
        except Stopped as exc:
            step.note_error(str(exc))
            fail(batch, str(exc))
        except Exception as exc:  # noqa: BLE001 - the batch must always be closed and reported
            logger.exception("Plate batch %s failed", batch.pk)
            step.note_error("{}: {}".format(type(exc).__name__, exc))
            fail(batch, UNEXPECTED)


def make(batch, step):
    if not enough_disk():
        raise Stopped(LOW_DISK)
    renderer, checked = checked_batch(batch)
    step.expect(checked.total)
    directory = os.path.join(retention.export_root(), uuid.uuid4().hex)
    os.makedirs(directory, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(suffix=".zip", dir=directory)
    os.close(handle)
    try:
        with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_STORED, allowZip64=True) as archive:
            write_plates(batch, renderer, checked, archive, step)
            archive.writestr("plates.xlsx", report_bytes(batch, checked))
        final_path = os.path.join(directory, zip_file_name(batch, checked))
        os.rename(temp_path, final_path)
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    finish(batch, checked, final_path)


def write_plates(batch, renderer, checked, archive, step):
    for index, result in enumerate(checked.made, start=1):
        with step.record(key="row {}".format(result.number)):
            buffer = io.BytesIO()
            save_png(renderer.render(result.row), buffer, batch.template.dpi)
            archive.writestr("images/" + result.file_name, buffer.getvalue())
        if index % PROGRESS_EVERY == 0:
            PlateBatch.objects.filter(pk=batch.pk).update(made_count=index)
            if not enough_disk():
                raise Stopped(DISK_RAN_OUT)


def zip_file_name(batch, checked):
    label = checked.first_value("city") or checked.first_value("slum") or os.path.splitext(batch.original_name)[0]
    return naming.zip_name(label, batch.plate_type, timezone.localdate(), batch.pk)


def report_facts(batch, checked):
    template = batch.template
    who = lambda user: user.get_username() if user else ""  # noqa: E731
    return [
        ("Batch", str(batch.public_id)), ("Batch number", batch.pk), ("Plate type", batch.get_plate_type_display()),
        ("Template", template.name), ("Template version", template.version),
        ("Plate size", "{} x {} mm".format(template.width_mm, template.height_mm)), ("DPI", template.dpi),
        ("Drill holes", "yes" if batch.holes and (template.holes or {}).get("on", True) else "no"),
        ("Side panel", "yes" if batch.side_panel or (template.side_panel or {}).get("on") else "no"),
        ("Source file", batch.original_name), ("Sheet", checked.sheet.title),
        ("Rows", checked.total), ("Made", len(checked.made)), ("Skipped", len(checked.skipped)), ("Warnings", len(checked.warned)),
        ("Requested by", who(batch.requested_by)), ("Requested on", email.when(batch.created_on)),
        ("Confirmed by", who(batch.confirmed_by)), ("Confirmed on", email.when(batch.confirmed_on)),
        ("Started", email.when(batch.started_on)), ("Finished", email.when(timezone.now())),
    ]


def report_bytes(batch, checked):
    buffer = io.BytesIO()
    excel.write_report(buffer, checked.sheet, checked.results, report_facts(batch, checked))
    return buffer.getvalue()


def row_list(results, attribute):
    items = []
    for result in results:
        text = result.reason if attribute == "reason" else "; ".join(result.warnings)
        items.append({"row": result.number, "reason": text})
    return items[:REPORT_LIMIT]


def finish(batch, checked, path):
    batch.status = "done"
    batch.file_path = path
    batch.bytes_total = os.path.getsize(path)
    batch.made_count, batch.skipped_count, batch.warning_count = len(checked.made), len(checked.skipped), len(checked.warned)
    batch.failures = row_list(checked.skipped, "reason")
    batch.warnings = row_list(checked.warned, "warnings")
    batch.finished_on = timezone.now()
    batch.delete_after = retention.delete_after(batch.finished_on)
    batch.save()
    email.send_done(batch)
    logger.info("Plate batch %s done: %s made, %s skipped", batch.pk, batch.made_count, batch.skipped_count)


def fail(batch, message):
    PlateBatch.objects.filter(pk=batch.pk).update(status="failed", error=message, finished_on=timezone.now())
    batch.refresh_from_db()
    logger.error("Plate batch %s failed: %s", batch.pk, message)
    email.send_failed(batch)


def apply_check(batch, checked):
    batch.row_count, batch.skipped_count, batch.warning_count = checked.total, len(checked.skipped), len(checked.warned)
    batch.slum_name = checked.first_value("slum")[:120]
    batch.city_name = checked.first_value("city")[:120]
    batch.columns = list(checked.sheet.headers)
    batch.sheet_name = checked.sheet.title


def active_batch(user, exclude=None):
    return PlateBatch.objects.filter(requested_by=user, status__in=("queued", "running")).exclude(pk=exclude).first()


def confirm(batch, user, checked, address=None):
    """Queue a checked draft; notifications go to address (default: the user's email). Raises BatchError."""
    if not checked.made:
        raise BatchError("None of the rows can be made into plates. Check the reasons below; nothing has been queued.")
    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)
        locked = PlateBatch.objects.select_for_update().get(pk=batch.pk)
        if locked.status != "draft":
            raise BatchError("This batch has already been confirmed or cancelled.")
        running = active_batch(user, exclude=locked.pk)
        if running is not None:
            raise BatchError("You already have a batch queued ({}, {}). Wait for it to finish or cancel it first.".format(
                email.label(running), running.get_plate_type_display()))
        apply_check(locked, checked)
        locked.confirmed_by, locked.confirmed_on, locked.email = user, timezone.now(), address or user.email or ""
        locked.status = "queued"
        locked.job_request = queue.enqueue(JOB_KEY, {"batch": str(locked.public_id)}, user)
        locked.save()
    email.send_queued(locked)
    return locked


def delete_upload(batch):
    if batch.upload:
        batch.upload.delete(save=False)
        PlateBatch.objects.filter(pk=batch.pk).update(upload="")


def cancel(batch, user):
    """Cancel a draft or a queued batch. Raises BatchError once the run has started."""
    now = timezone.now()
    if batch.status == "draft":
        PlateBatch.objects.filter(pk=batch.pk, status="draft").update(status="cancelled", cancelled_by=user, cancelled_on=now)
        delete_upload(batch)
        batch.refresh_from_db()
        return batch
    with transaction.atomic():
        cancelled = PlateBatch.objects.filter(pk=batch.pk, status="queued").update(status="cancelled", cancelled_by=user, cancelled_on=now)
        if not cancelled:
            raise BatchError("This batch has already started, so it can no longer be cancelled.")
        if batch.job_request_id:
            JobRequest.objects.filter(pk=batch.job_request_id, status="queued").update(
                status="cancelled", finished_on=now, error="Cancelled from the plates page by {}".format(user.get_username()))
    batch.refresh_from_db()
    email.send_cancelled(batch)
    return batch


def can_generate_again(batch):
    return batch.status in ("failed", "cancelled", "expired") and bool(batch.upload) and batch.confirmed_on is not None


def generate_again(batch, user):
    """A new draft from the stored Excel with the same template version; it goes through demo and confirm again."""
    if not can_generate_again(batch) or not os.path.isfile(batch.upload.path):
        raise BatchError("The uploaded Excel of this batch is no longer kept. Upload it again to make these plates.")
    fresh = PlateBatch(template=batch.template, plate_type=batch.plate_type, source="excel", original_name=batch.original_name,
                       sheet_name=batch.sheet_name, requested_by=user, email=user.email or "", regenerated_from=batch, holes=batch.holes,
                       side_panel=batch.side_panel)
    with open(batch.upload.path, "rb") as handle:
        fresh.upload.save(os.path.basename(batch.upload.name), File(handle), save=True)
    return fresh


def reconcile(batch):
    """A queued/running batch whose queue request already ended (orphan sweep, switched off) is marked failed once."""
    if batch.status not in ("queued", "running") or not batch.job_request_id:
        return batch
    request = JobRequest.objects.filter(pk=batch.job_request_id).first()
    if request is None or request.status in ("queued", "running", "done"):
        return batch
    message = RESTARTED if request.status == "failed" else "The batch was stopped before it ran: {}".format(request.error or request.status)
    if PlateBatch.objects.filter(pk=batch.pk, status__in=("queued", "running")).update(status="failed", error=message, finished_on=timezone.now()):
        batch.refresh_from_db()
        email.send_failed(batch)
    return batch


def reconcile_all():
    for batch in PlateBatch.objects.filter(status__in=("queued", "running"), job_request__status__in=("failed", "cancelled")):
        reconcile(batch)
