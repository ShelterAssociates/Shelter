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
):
    context = context or {}
    cc = cc or []
    bcc = bcc or []
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
