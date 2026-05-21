from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.utils import make_msgid

def send_email(to_emails, subject, template_name=None, context=None, plain_message="", thread_message_id=None, cc=None, bcc=None):
    context = context or {}
    cc = cc or []
    bcc = bcc or []
    html_content = render_to_string(template_name, context) if template_name else plain_message
    msg = EmailMultiAlternatives(subject, plain_message, settings.DEFAULT_FROM_EMAIL, to_emails, cc=cc, bcc=bcc)
    message_id = make_msgid()
    msg.extra_headers = {"Message-ID": message_id}
    if thread_message_id: msg.extra_headers.update({"In-Reply-To": thread_message_id, "References": thread_message_id})
    msg.attach_alternative(html_content, "text/html")
    msg.send(); return message_id