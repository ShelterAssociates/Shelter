"""Builds and sends the job digest and failure alerts."""

import csv
import logging
import os
from datetime import timedelta

from django.utils import timezone

from helpers.services.send_email import send_email
from notification.services import contacts

logger = logging.getLogger(__name__)

DIGEST_PURPOSE = "job_digest"
FAILURE_PURPOSE = "job_failure"
ACTIVITY_PURPOSE = "avni_console_activity"
BULK_PURPOSE = "avni_bulk_update"
BULK_JOB_KEY = "avni_bulk_update"
INLINE_CHANGE_ROWS = 200

STATUS_COLOURS = {
    "success": "#1e8e3e",
    "partial": "#f29900",
    "failed": "#d93025",
    "crashed": "#d93025",
    "running": "#1a73e8",
}


def _run_payload(run):
    steps = []
    for step in run.steps.all().prefetch_related("city_stats"):
        steps.append(
            {
                "step": step,
                "cities": list(step.city_stats.all()),
                "failures": (step.sample_failures or [])[:20],
            }
        )
    request = run.requests.select_related("requested_by").first()
    return {
        "run": run,
        "steps": steps,
        "request": request,
        "requester": requester_label(request) if request else "",
        "params_text": describe_params(request.job_key, request.params or {}) if request else "",
    }


def queue_health(since, until):
    """Requests the runner should have picked up but did not, and requests that died outside a run."""
    from notification.models import JobRequest

    stuck_after = timezone.now() - timedelta(hours=2)
    stuck = list(JobRequest.objects.filter(status="queued", scheduled_for__lt=stuck_after).select_related("requested_by"))
    died = list(
        JobRequest.objects.filter(status__in=("failed", "cancelled"), job_run__isnull=True,
                                  finished_on__gte=since, finished_on__lte=until).select_related("requested_by")
    )
    return {"stuck": stuck, "died": died}


def send_digest(runs, missed, since, until):
    """One digest covering every run in the window. Returns the Message-ID or None."""
    to, cc, bcc = contacts.recipients_for(DIGEST_PURPOSE)
    if not to:
        logger.error("Digest not sent: no recipients for %s", DIGEST_PURPOSE)
        return None

    runs = list(runs)
    bad = [r for r in runs if r.status in ("failed", "crashed", "partial")]
    health = queue_health(since, until)
    if missed:
        headline = "{} job(s) did not run".format(len(missed))
        colour = STATUS_COLOURS["failed"]
    elif health["stuck"]:
        headline = "{} queued request(s) were never picked up".format(len(health["stuck"]))
        colour = STATUS_COLOURS["failed"]
    elif bad:
        headline = "{} job(s) had problems".format(len(bad))
        colour = STATUS_COLOURS["partial"]
    else:
        headline = "All jobs healthy"
        colour = STATUS_COLOURS["success"]

    subject = "Shelter daily job report - {} - {}".format(
        timezone.localtime(until).strftime("%d %b %Y"), headline
    )
    context = {
        "headline": headline,
        "header_colour": colour,
        "since": timezone.localtime(since),
        "until": timezone.localtime(until),
        "missed": missed,
        "queue": health,
        "jobs": [_run_payload(r) for r in runs],
        "totals": {
            "records": sum(r.records_total for r in runs),
            "ok": sum(r.records_ok for r in runs),
            "failed": sum(r.records_failed for r in runs),
        },
    }
    attachments = [r.detail_file_path for r in runs if r.detail_file_path]
    return _send(
        to, cc, bcc, subject, "notification/digest_email.html", context, attachments
    )


def send_failure_alert(run):
    """Immediate alert for one failed run. Returns the Message-ID or None."""
    definition = run.job
    if definition and not definition.alert_on_failure:
        return None
    if definition and definition.failure_alert_cooldown_minutes:
        from notification.models import JobRun

        cutoff = timezone.now() - timedelta(
            minutes=definition.failure_alert_cooldown_minutes
        )
        recent = (
            JobRun.objects.filter(job_key=run.job_key, alert_sent_at__gte=cutoff)
            .exclude(pk=run.pk)
            .exists()
        )
        if recent:
            logger.info("Alert for %s suppressed by cooldown", run.job_key)
            return None

    to, cc, bcc = contacts.recipients_for(FAILURE_PURPOSE)
    if not to:
        logger.error("Failure alert not sent: no recipients for %s", FAILURE_PURPOSE)
        return None

    name = definition.display_name if definition else run.job_key
    subject = "Shelter job FAILED: {} ({} records failed)".format(
        name, run.records_failed
    )
    context = {
        "run": run,
        "job_name": name,
        "header_colour": STATUS_COLOURS.get(run.status, STATUS_COLOURS["failed"]),
        "steps": _run_payload(run)["steps"],
    }
    attachments = [run.detail_file_path] if run.detail_file_path else []
    thread = definition.thread_message_id if definition else None
    message_id = _send(
        to,
        cc,
        bcc,
        subject,
        "notification/failure_alert_email.html",
        context,
        attachments,
        thread_message_id=thread,
    )
    if message_id:
        run.alert_sent_at = timezone.now()
        run.save(update_fields=["alert_sent_at"])
        if definition and not definition.thread_message_id:
            definition.thread_message_id = message_id
            definition.save(update_fields=["thread_message_id"])
    return message_id


def _send(to, cc, bcc, subject, template, context, attachments, thread_message_id=None):
    try:
        return send_email(
            to,
            subject,
            template,
            context,
            subject,
            thread_message_id,
            cc,
            bcc,
            attachments=attachments,
        )
    except Exception:
        logger.exception("Failed to send %s", subject)
        return None



def send_activity_report(request, run):
    """Who ran what from the console / shell, and everything it changed. Returns the Message-ID or None.

    Syncs go to the activity purpose with the requester in CC; bulk updates into
    AVNI go to the bulk purpose only (developer + data team).
    """
    is_bulk = request.job_key == BULK_JOB_KEY
    to, cc, bcc = contacts.recipients_for(BULK_PURPOSE if is_bulk else ACTIVITY_PURPOSE)
    if not to:
        logger.error("Activity report not sent: no recipients for job request %s", request.pk)
        return None
    requester_email = getattr(request.requested_by, "email", "") or ""
    if not is_bulk and requester_email and requester_email not in to and requester_email not in cc:
        cc = list(cc) + [requester_email]

    params = request.params or {}
    dry_run = bool(params.get("dry_run")) if is_bulk else False
    status = run.status if run else request.status
    title = job_title(request.job_key)
    subject = "[Shelter] {}{} by {} - {}".format("DRY RUN " if dry_run else "", title, requester_name(request), status)

    changes_total = len(change_rows(changes_file_for(request))) if is_bulk else 0
    context = {
        "title": title,
        "request": request,
        "run": run,
        "status": status,
        "header_colour": STATUS_COLOURS.get(status, STATUS_COLOURS["failed"]),
        "requester": requester_label(request),
        "params_text": describe_params(request.job_key, params),
        "dry_run": dry_run,
        "steps": _run_payload(run)["steps"] if run else [],
        "changes_total": changes_total,
        "detail_lines": detail_lines(run) if run and not is_bulk else [],
        "run_url": run_url(request),
    }
    attachments = []
    if run and run.detail_file_path and os.path.exists(run.detail_file_path):
        attachments.append(run.detail_file_path)
    changes_path = changes_file_for(request) if is_bulk else None
    if changes_path and os.path.exists(changes_path):
        with open(changes_path, "rb") as handle:
            attachments.append(("changes.csv", handle.read(), "text/csv"))
    return _send(to, cc, bcc, subject, "notification/activity_email.html", context, attachments)


def job_title(job_key):
    try:
        from avni_console import catalog

        job = catalog.BY_KEY.get(job_key)
        if job:
            return job.title
    except ImportError:
        pass
    return "Bulk update into AVNI" if job_key == BULK_JOB_KEY else job_key.replace("_", " ")


def describe_params(job_key, params):
    try:
        from avni_console import catalog

        return catalog.describe(job_key, params)
    except ImportError:
        return ", ".join("{}={}".format(k, v) for k, v in sorted(params.items()))


def requester_name(request):
    user = request.requested_by
    return user.get_username() if user else "system"


def requester_label(request):
    user = request.requested_by
    if user is None:
        return "system (shell or cron)"
    return "{} (user id {}{})".format(user.get_username(), user.pk, ", " + user.email if user.email else "")


def run_url(request):
    from django.conf import settings

    base = (getattr(settings, "BASE_APP_URL", "") or "").rstrip("/")
    return "{}/avni-console/runs/{}/".format(base, request.pk)


def changes_file_for(request):
    """Path of the bulk update's changes.csv, or None."""
    try:
        from avni_console.models import BulkUpdate
    except ImportError:
        return None
    bulk = BulkUpdate.objects.filter(job_request=request).first()
    return bulk.result_file_path if bulk and bulk.result_file_path else None


def change_rows(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def detail_lines(run, limit=INLINE_CHANGE_ROWS):
    """Per-record lines of a sync's detail file (the 'what got synced' list)."""
    if not run.detail_file_path or not os.path.exists(run.detail_file_path):
        return []
    lines = []
    with open(run.detail_file_path) as handle:
        for line in handle:
            if line[:4].isdigit() and ("  OK  " in line or "  FAIL" in line or "  SKIP" in line):
                lines.append(line.rstrip())
                if len(lines) >= limit:
                    break
    return lines
