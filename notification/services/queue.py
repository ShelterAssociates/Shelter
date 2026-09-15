"""The JobRequest queue: how console / admin / shell requests become JobRuns.

Cron runs `manage.py run_job_queue` every two minutes; it claims the oldest due
request, executes it, links the JobRun, and emails an activity report. Cron
rather than request threads because a deploy's gunicorn restart would kill a
thread silently; a row survives and the orphan sweep reports it.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from notification.models import JobRequest
from notification.services import email as job_email
from notification.services import execute, registry

logger = logging.getLogger(__name__)

ORPHAN_MESSAGE = (
    "Stopped unexpectedly (most likely a server restart or deploy while it was "
    "running). Queue it again if needed."
)


def enqueue(job_key, params, user, scheduled_for=None, dedupe_key=""):
    """Create a queued request, or merge into the pending one with the same dedupe_key."""
    registry.resolve(job_key)
    if dedupe_key:
        pending = JobRequest.objects.filter(dedupe_key=dedupe_key, status="queued").order_by("created_on").first()
        if pending is not None:
            pending.params = merge_params(pending.params or {}, params or {})
            pending.save(update_fields=["params"])
            return pending
    return JobRequest.objects.create(
        job_key=job_key,
        params=params or {},
        requested_by=user,
        scheduled_for=scheduled_for or timezone.now(),
        dedupe_key=dedupe_key or "",
    )


def merge_params(existing, incoming):
    """Lists union (order kept), other values: the newer request wins."""
    merged = dict(existing)
    for key, value in incoming.items():
        if isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = merged[key] + [item for item in value if item not in merged[key]]
        else:
            merged[key] = value
    return merged


def pending(job_key, user=None):
    rows = JobRequest.objects.filter(job_key=job_key, status__in=("queued", "running"))
    if user is not None:
        rows = rows.filter(requested_by=user)
    return rows


def claim_next():
    """Mark the oldest due queued request running and return it, or None."""
    with transaction.atomic():
        request = (
            JobRequest.objects.select_for_update()
            .filter(status="queued", scheduled_for__lte=timezone.now())
            .order_by("created_on")
            .first()
        )
        if request is None:
            return None
        request.status = "running"
        request.started_on = timezone.now()
        request.save(update_fields=["status", "started_on"])
        return request


def sweep_orphans():
    """Fail requests left running longer than JOB_RUN_STUCK_HOURS and report them."""
    hours = getattr(settings, "JOB_RUN_STUCK_HOURS", 6)
    cutoff = timezone.now() - timezone.timedelta(hours=hours)
    orphans = list(JobRequest.objects.filter(status="running", started_on__lt=cutoff))
    for request in orphans:
        finish(request, "failed", error=ORPHAN_MESSAGE)
        logger.error("Job request %s marked failed: orphaned", request.pk)
        report(request)
    return len(orphans)


def run(request):
    """Execute one claimed request as a manual JobRun and record the outcome."""
    try:
        definition = execute.definition_for(request.job_key)
        if not definition.is_active:
            finish(request, "cancelled", error="{} is switched off in admin (Job definitions).".format(request.job_key))
            return request
        job_run = execute.execute(
            request.job_key, trigger="manual", params=request.params or {},
            definition=definition, handle_sigterm=False,
        )
        request.job_run = job_run
        status = "done" if job_run.status in ("success", "partial") else "failed"
        finish(request, status, summary=summarize(job_run), error=job_run.error if status == "failed" else None)
    except Exception as exc:  # noqa: BLE001 - a request must always be closed
        logger.exception("Job request %s failed outside the job", request.pk)
        finish(request, "failed", error="{}: {}".format(type(exc).__name__, exc))
    report(request)
    return request


def summarize(job_run):
    return "{}: {} ok, {} failed, {} seen".format(
        job_run.status, job_run.records_ok, job_run.records_failed, job_run.records_total
    )


def finish(request, status, summary=None, error=None):
    request.status = status
    request.finished_on = timezone.now()
    if summary is not None:
        request.summary = summary
    if error is not None:
        request.error = error
    request.save()


def report(request):
    try:
        job_email.send_activity_report(request, request.job_run)
    except Exception:  # noqa: BLE001 - email must never break the queue
        logger.exception("Activity report for job request %s could not be sent", request.pk)
