import os

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.utils import make_msgid
import logging

logger = logging.getLogger(__name__)


def send_email(
    to_emails,
    subject,
    template_name=None,
    context=None,
    plain_message="",
    thread_message_id=None,
    cc=None,
    bcc=None,
    attachments=None,
):
    context = context or {}
    cc = cc or []
    bcc = bcc or []
    to_emails, cc, bcc, subject, redirect_note = _dev_redirect(to_emails, cc, bcc, subject)
    logger.info(
        "Email render starting: subject=%s to=%s template=%s cc=%s bcc=%s",
        subject,
        to_emails,
        template_name,
        cc,
        bcc,
    )
    html_content = (
        render_to_string(template_name, context) if template_name else plain_message
    )
    if redirect_note:
        html_content = _dev_banner(redirect_note) + (html_content or "")
        plain_message = redirect_note + "\n\n" + (plain_message or "")
    logger.info(
        "Email render finished: subject=%s to=%s template=%s html_length=%s",
        subject,
        to_emails,
        template_name,
        len(html_content or ""),
    )
    msg = EmailMultiAlternatives(
        subject, plain_message, settings.DEFAULT_FROM_EMAIL, to_emails, cc=cc, bcc=bcc
    )
    message_id = make_msgid()
    msg.extra_headers = {"Message-ID": message_id}
    if thread_message_id:
        msg.extra_headers.update(
            {"In-Reply-To": thread_message_id, "References": thread_message_id}
        )
    msg.attach_alternative(html_content, "text/html")
    for item in attachments or []:
        _attach(msg, item)
    logger.info(
        "Email send starting: subject=%s to=%s cc=%s bcc=%s message_id=%s",
        subject,
        to_emails,
        cc,
        bcc,
        message_id,
    )
    sent_count = msg.send(fail_silently=False)
    logger.info(
        "Email sent: subject=%s to=%s cc=%s bcc=%s sent_count=%s",
        subject,
        to_emails,
        cc,
        bcc,
        sent_count,
    )
    return message_id


def _attach(msg, item):
    """Attach a (filename, content, mimetype) tuple or a path on disk.

    Files over settings.JOB_REPORT_MAX_ATTACH_BYTES are truncated to a head and
    tail rather than dropped, so a huge report still tells you something.
    """
    if isinstance(item, (tuple, list)):
        msg.attach(*item)
        return
    path = item
    if not path or not os.path.exists(path):
        logger.warning("Skipping missing attachment %s", path)
        return
    cap = getattr(settings, "JOB_REPORT_MAX_ATTACH_BYTES", 5 * 1024 * 1024)
    name = os.path.basename(path)
    size = os.path.getsize(path)
    if size <= cap:
        msg.attach_file(path)
        return
    half = cap // 2
    with open(path, "rb") as handle:
        head = handle.read(half)
        handle.seek(max(size - half, half))
        tail = handle.read()
    notice = (
        "\n\n... TRUNCATED: original was {} bytes, limit is {} ...\n\n"
    ).format(size, cap).encode("utf-8")
    msg.attach(name, head + notice + tail, "text/plain")
    logger.warning("Attachment %s truncated from %s bytes", name, size)


def _dev_redirect(to, cc, bcc, subject):
    """With DEBUG on, every mail goes only to the dev_redirect contacts.

    Returns (to, cc, bcc, subject, note); note is empty when nothing changed.
    Refuses to send at all if no dev recipient is configured, so a local run
    can never reach real people.
    """
    if not settings.DEBUG:
        return to, cc, bcc, subject, ""
    from notification.services import contacts

    dev_to, _, _ = contacts.recipients_for("dev_redirect")
    if not dev_to:
        raise RuntimeError(
            "DEBUG is on but no dev_redirect recipients exist. Add a contact to "
            "the dev_redirect purpose in admin or set EMAIL_DEV_REDIRECT_TO."
        )
    note = (
        "DEV REDIRECT: this mail was sent from a development environment and "
        "delivered only to {}. Original recipients - to: {}; cc: {}; bcc: {}."
    ).format(
        ", ".join(dev_to),
        ", ".join(to) or "-",
        ", ".join(cc) or "-",
        ", ".join(bcc) or "-",
    )
    logger.warning(note)
    return dev_to, [], [], "[DEV] " + subject, note


def _dev_banner(note):
    return (
        '<div style="background:#fff3cd;border:2px solid #f0ad4e;color:#664d03;'
        'padding:12px 16px;margin:0 0 16px;font:14px Arial,Helvetica,sans-serif;">'
        "<strong>Development environment</strong><br />{}</div>"
    ).format(note)
