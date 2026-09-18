"""Builds and sends the nightly digest, failure alerts and activity reports."""

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
        "colour": STATUS_COLOURS.get(run.status, STATUS_COLOURS["failed"]),
        "steps": steps,
        "request": request,
        "requester": requester_label(request) if request else "",
        "params_text": describe_params(request.job_key, request.params or {}) if request else "",
    }


def stuck_requests():
    """Queued requests the runner should have picked up hours ago but did not."""
    from notification.models import JobRequest

    stuck_after = timezone.now() - timedelta(hours=2)
    return list(JobRequest.objects.filter(status="queued", scheduled_for__lt=stuck_after).order_by("pk"))


def send_digest(runs, missed, since, until):
    """Plain-text nightly summary of the scheduled runs. Returns the Message-ID or None.

    Short on purpose (management reads it): per-step counts and city tables, one
    cause line where something broke, no record-level lines, no attachments.
    Manual runs are not passed in; each is mailed as it finishes (send_activity_report).
    """
    to, cc, bcc = contacts.recipients_for(DIGEST_PURPOSE)
    if not to:
        logger.error("Digest not sent: no recipients for %s", DIGEST_PURPOSE)
        return None

    runs = list(runs)
    stuck = stuck_requests()
    status = digest_status(runs, missed, stuck)
    day = timezone.localtime(until).strftime("%d %b %Y")
    text = nightly_text(day, status, runs, missed, stuck, since, until)
    subject = "Shelter Nightly Sync - {} - {}".format(day, status.split(" (")[0])
    return _send(
        to, cc, bcc, subject, "notification/nightly_digest_email.html", {"text": text}, [], plain=text
    )


def digest_status(runs, missed, stuck):
    """OK, or the worst thing that happened and why, e.g. FAILED (members hung: ...)."""
    if missed:
        item = missed[0]
        return "MISSED ({} did not start at {})".format(item["name"], _when(item["expected_at"]))
    if stuck:
        return "FAILED ({} queued request(s) never picked up - is the queue runner cron running?)".format(len(stuck))
    order = ("crashed", "failed", "partial")
    bad = sorted((r for r in runs if r.status in order), key=lambda r: order.index(r.status))
    if not bad:
        return "OK"
    label = "PARTIAL" if bad[0].status == "partial" else "FAILED"
    return "{} ({})".format(label, run_cause(bad[0]))


def nightly_text(day, status, runs, missed, stuck, since, until):
    lines = [
        "Shelter Nightly Sync — {}".format(day),
        "Status: {}".format(status),
        "Window: {} → {}".format(_when(since), _when(until)),
        "",
    ]
    for item in missed:
        lines.append("Did not run: {} (expected {})".format(item["name"], _when(item["expected_at"])))
    if stuck:
        lines.append("Queued requests never picked up: " + ", ".join("#{} {}".format(r.pk, r.job_key) for r in stuck))
    if missed or stuck:
        lines.append("")
    if not runs:
        lines.append("No scheduled runs were recorded in this window.")
    for run in runs:
        lines.extend(run_lines(run))
        lines.append("")
    lines.append("Synced = source records written without error, not households changed.")
    return "\n".join(lines) + "\n"


def run_lines(run):
    name = run.job.display_name if run.job else run.job_key
    head = "{} — {}, started {}, took {}".format(
        name, run.get_status_display().upper(), _when(run.started_on), run.duration_display
    )
    if run.window_label:
        head += ", window: " + run.window_label
    lines = [head]
    steps = list(run.steps.all().prefetch_related("city_stats"))
    if not steps:
        lines.append("  {} synced, {} failed, {} skipped".format(run.records_ok, run.records_failed, run.records_skipped))
    for step in steps:
        if step.status == "disabled":
            lines.append("  {} — switched off in admin, not run".format(step.name))
            continue
        extras = step.extras or {}
        split = " ({} created, {} updated)".format(extras["created"], extras.get("updated", 0)) if "created" in extras else ""
        lines.append("  {} — {} synced{}, {} failed, {} skipped".format(
            step.name, step.records_ok, split, step.records_failed, step.records_skipped
        ))
        lines.extend(city_table(step.city_stats.all(), "    "))
        if step.error:
            lines.append("    Cause: " + last_line(step.error))
    if run.error:
        lines.append("  Cause: " + run_cause(run))
    return lines


def city_table(cities, indent):
    rows = [(c.city_name, str(c.records_ok), str(c.records_failed), str(c.records_skipped)) for c in cities]
    if not rows:
        return []
    rows.insert(0, ("City", "Synced", "Failed", "Skipped"))
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    return [indent + "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip() for row in rows]


def run_cause(run):
    """One line naming the step that broke and why; the run's own error otherwise."""
    steps = list(run.steps.all())
    for step in steps:
        if step.status == "failed" and step.error:
            return "{}: {}".format(step.name, last_line(step.error))
    hung = [s for s in steps if s.status == "running"]
    if run.status == "crashed" and hung:
        return "{} hung: {}".format(hung[-1].name, last_line(run.error) or "run was cut short")
    if run.error:
        return last_line(run.error)
    return "{} record(s) failed".format(run.records_failed)


def last_line(text, limit=160):
    """The last non-empty line of an error or traceback, i.e. the exception message."""
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return ""
    line = lines[-1]
    return line if len(line) <= limit else line[: limit - 3] + "..."


def _when(dt):
    return timezone.localtime(dt).strftime("%d %b %Y %H:%M")


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


def _send(to, cc, bcc, subject, template, context, attachments, thread_message_id=None, plain=None):
    try:
        return send_email(
            to,
            subject,
            template,
            context,
            plain or subject,
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
