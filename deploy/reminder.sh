#!/bin/bash

cd /srv/Shelter/
source ENV3/bin/activate || exit

python manage.py shell << 'EOF'

from datetime import datetime, timedelta
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from helpers.services.send_email import send_email
from helpers.models import ReminderTracker

# ── Test Config (adjust these before each manual run) ────────────────────────
REMINDER_TYPE  = "GIS_SERVER_DATA_SYNC"
TO_EMAILS      = ["developer@shelter-associates.org"]
CC_EMAILS      = ["sonjevrundavan2102@gmail.com" ]
BCC_EMAILS     = []
TEMPLATE       = "helpers/gis_reminder.html"
PRIMARY_EMAIL  = TO_EMAILS[0]

GAP_MINUTES    = 2800         
# ─────────────────────────────────────────────────────────────────────────────

current_date    = datetime.now() 
last_month_date = current_date.replace(day=1) - timedelta(days=1)

tracker, created = ReminderTracker.objects.get_or_create(
    reminder_type=REMINDER_TYPE,
    month=current_date.month,
    year=current_date.year,
    email=PRIMARY_EMAIL,
)

if tracker.status == "COMPLETED":
    print("Already confirmed for this month. Skipping.")
    exit()

if not created and tracker.last_reminder_sent_at:
    last_sent = tracker.last_reminder_sent_at
    if timezone.is_naive(last_sent):
        last_sent = timezone.make_aware(last_sent)
    minutes_since = (timezone.now() - last_sent).total_seconds() / 60
    if minutes_since < GAP_MINUTES:
        print(f"[TEST] Last reminder sent {minutes_since:.1f} min ago. Gap is {GAP_MINUTES} min. Skipping.")
        exit()

reminder_count = tracker.reminder_sent_count + 1

subject = (
    f"[TEST] GIS Server Data Sync Reminder - {last_month_date.strftime('%B')} "
    f"{last_month_date.year} - Reminder {reminder_count}"
)

confirm_path = reverse("confirm_reminder")
confirm_url  = f"{settings.BASE_APP_URL}{confirm_path}?uuid={tracker.uuid}"

context = {
    "DATE_TODAY":  current_date.strftime("%d %B %Y"),
    "MONTH_NAME":  last_month_date.strftime("%B"),
    "YEAR":        last_month_date.year,
    "confirm_url": confirm_url,
    "reminder_count": reminder_count,
}

message_id = send_email(
    TO_EMAILS,
    subject,
    TEMPLATE,
    context,
    subject,
    tracker.thread_message_id,
    CC_EMAILS,
    BCC_EMAILS,
)

if not tracker.thread_message_id:
    tracker.thread_message_id = message_id

if not tracker.subject:
    tracker.subject = subject

tracker.recipient_data = {
    "to":  TO_EMAILS,
    "cc":  CC_EMAILS,
    "bcc": BCC_EMAILS,
}

tracker.reminder_sent_count   = reminder_count
tracker.last_reminder_sent_at = timezone.now()
tracker.save()

print(f"[TEST] Reminder #{reminder_count} sent for {last_month_date.strftime('%B')} {last_month_date.year}")
print(f"[TEST] Run again after {GAP_MINUTES} min to simulate next reminder.")
print(f"[TEST] Confirm URL: {confirm_url}")

EOF