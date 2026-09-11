"""Builds and sends the job digest and failure alerts."""

import logging
from datetime import timedelta

from django.utils import timezone

from helpers.services.send_email import send_email
from notification.services import contacts

logger = logging.getLogger(__name__)

DIGEST_PURPOSE = "job_digest"
FAILURE_PURPOSE = "job_failure"

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
    return {"run": run, "steps": steps}


def send_digest(runs, missed, since, until):
    """One digest covering every run in the window. Returns the Message-ID or None."""
    to, cc, bcc = contacts.recipients_for(DIGEST_PURPOSE)
    if not to:
        logger.error("Digest not sent: no recipients for %s", DIGEST_PURPOSE)
        return None

    runs = list(runs)
    bad = [r for r in runs if r.status in ("failed", "crashed", "partial")]
    if missed:
        headline = "{} job(s) did not run".format(len(missed))
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
