"""Batch and template emails. Only @shelter-associates.org addresses; links go to login-protected pages, never to a file.
A failed email is logged and never fails a batch."""

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from helpers.services.send_email import send_email
from helpers.validators import validate_shelter_email
from plates.services import retention

logger = logging.getLogger(__name__)
TEMPLATE = "plates/email/notice.html"
COLOURS = {"queued": "#4B42A8", "done": "#1e8e3e", "failed": "#d93025", "cancelled": "#b45309", "template": "#2A2468"}


def page_url(name, *args):
    return (getattr(settings, "BASE_APP_URL", "") or "").rstrip("/") + reverse(name, args=args)


def batch_url(batch):
    return page_url("plates:batch_detail", batch.public_id)


def label(batch):
    return batch.slum_name or batch.original_name or "plates"


def addresses(candidates):
    found = []
    for email in candidates:
        email = (email or "").strip()
        if validate_shelter_email(email) and email.lower() not in [item.lower() for item in found]:
            found.append(email)
    return found


def size_text(bytes_total):
    size = float(bytes_total or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return "{:.1f} {}".format(size, unit)
        size /= 1024


def when(moment):
    return timezone.localtime(moment).strftime("%d %b %Y, %H:%M") if moment else ""


def batch_facts(batch):
    template = batch.template
    return [
        ("Template", "{} (version {})".format(template.name, template.version)),
        ("Size", "{} x {} mm at {} DPI".format(template.width_mm, template.height_mm, template.dpi)),
        ("File", batch.original_name),
        ("Requested by", batch.requested_by.get_username() if batch.requested_by else ""),
    ]


def deliver(to, subject, context, text, attachments=None, cc=None):
    to = addresses(to)
    if not to:
        logger.warning("Plates email not sent (no @shelter-associates.org address): %s", subject)
        return None
    try:
        return send_email(to, subject, TEMPLATE, context, text, cc=addresses(cc or []) or None, attachments=attachments)
    except Exception:
        logger.exception("Plates email could not be sent: %s", subject)
        return None


def send_batch(batch, kind, subject, lines, facts=(), rows=(), button="Open the batch page", to=None):
    context = {
        "title": subject, "colour": COLOURS.get(kind, COLOURS["template"]), "lines": lines,
        "facts": list(batch_facts(batch)) + list(facts), "rows": list(rows), "link": batch_url(batch), "button": button,
    }
    text = "\n".join([subject, ""] + list(lines) + ["", batch_url(batch)])
    return deliver(to or [batch.email], subject, context, text)


def send_queued(batch):
    subject = "Plates queued: {}, {}, {} plates".format(label(batch), batch.get_plate_type_display(), batch.row_count - batch.skipped_count)
    lines = ["Your plates have been queued. They usually start within 2 minutes (longer if another job is running).",
             "You will get another email when the download is ready."]
    facts = [("Rows in the file", batch.row_count), ("Plates to make", batch.row_count - batch.skipped_count),
             ("Rows skipped", batch.skipped_count), ("Warnings", batch.warning_count)]
    return send_batch(batch, "queued", subject, lines, facts)


def send_done(batch):
    subject = "Plates ready: {}, {}, {} made, {} skipped".format(label(batch), batch.get_plate_type_display(), batch.made_count, batch.skipped_count)
    until = retention.available_until(batch)
    lines = ["Your plates are ready. Log in and download the zip from the batch page.",
             "Available until {}. After that the zip is deleted by the nightly cleanup; you can generate it again from the batch page.".format(until)]
    facts = [("Plates made", batch.made_count), ("Rows skipped", batch.skipped_count), ("Warnings", batch.warning_count),
             ("Zip size", size_text(batch.bytes_total)), ("Available until", until)]
    skipped = [("Row {}".format(item["row"]), item["reason"]) for item in (batch.failures or [])[:10]]
    return send_batch(batch, "done", subject, lines, facts, skipped, "Download (login needed)")


def send_failed(batch):
    from notification.services import contacts

    to, cc, bcc = contacts.recipients_for("job_failure")
    subject = "Plates failed: {}, {}".format(label(batch), batch.get_plate_type_display())
    made = "{} plates were drawn before it stopped, but no zip was kept.".format(batch.made_count) if batch.made_count else "Nothing was made."
    lines = [batch.error or "The batch stopped.", made, "Press Generate again on the batch page to start a new run."]
    return send_batch(batch, "failed", subject, lines, button="Generate again", to=[batch.email] + list(to) + list(cc) + list(bcc))


def send_cancelled(batch):
    subject = "Plates cancelled: {}".format(label(batch))
    who = batch.cancelled_by.get_username() if batch.cancelled_by else "someone"
    lines = ["{} cancelled this batch on {}. Nothing was made.".format(who, when(batch.cancelled_on))]
    return send_batch(batch, "cancelled", subject, lines)


def template_editors():
    groups = getattr(settings, "PLATES_TEMPLATE_GROUPS", []) or []
    users = User.objects.filter(is_active=True, is_superuser=True) | User.objects.filter(is_active=True, groups__name__in=groups)
    return [user.email for user in users.distinct()]


def send_template_changed(template, user, changes, preview_png):
    created = changes == ["New template"]
    subject = "Plate template {}: {}, version {}".format("created" if created else "changed", template.name, template.version)
    lines = ["{} {} this template.".format(user.get_username(), "created" if created else "changed")]
    context = {
        "title": subject, "colour": COLOURS["template"], "lines": lines, "facts": [], "rows": [(change, "") for change in changes],
        "link": page_url("plates:template_edit", template.pk), "button": "Open the template",
    }
    text = "\n".join([subject] + lines + list(changes))
    attachment = [("template-{}-v{}.png".format(template.pk, template.version), preview_png, "image/png")] if preview_png else None
    return deliver(template_editors(), subject, context, text, attachments=attachment)
