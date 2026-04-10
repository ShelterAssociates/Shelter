from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


def send_otp_email(email, otp):
    print
    html_content = render_to_string(
        "helpers/otp_email.html",
        {
            "otp": otp
        }
    )

    msg = EmailMultiAlternatives(
        "Shelter Associates - OTP Verification",
        f"Your OTP is {otp}",
        settings.DEFAULT_FROM_EMAIL,
        [email]
    )

    msg.attach_alternative(html_content, "text/html")
    msg.send()