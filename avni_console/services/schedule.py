"""When a queued dashboard refresh runs: the next occurrence of the configured hour, local time."""

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone


def next_run_at(hour=None, now=None):
    hour = getattr(settings, "AVNI_DASHBOARD_QUEUE_HOUR", 1) if hour is None else hour
    now = timezone.localtime(now or timezone.now())
    slot = timezone.make_aware(datetime.combine(now.date(), datetime.min.time()).replace(hour=hour))
    if slot <= now:
        slot += timedelta(days=1)
    return slot


def slot_key(job_key, when):
    """dedupe key so every click before the same slot merges into one request."""
    return "{}:{}".format(job_key, timezone.localtime(when).strftime("%Y-%m-%dT%H:%M"))
