"""Resolves outbound email addresses from the EmailContact address book.

Every caller asks for a purpose key and gets back (to, cc, bcc). Nothing in the
app should hold a literal address.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Purpose key -> settings constant used only when the DB has no active rows yet.
# Lets the address book roll out without any mail silently stopping.
SETTINGS_FALLBACK = {
    "job_digest": "JOB_NOTIFY_FALLBACK_EMAILS",
    "job_failure": "JOB_NOTIFY_FALLBACK_EMAILS",
    "kml_change": "KML_CHANGE_NOTIFY_EMAILS",
    "photo_export_failure": "PHOTO_EXPORT_NOTIFY_EMAILS",
    "avni_console_activity": "JOB_NOTIFY_FALLBACK_EMAILS",
    "avni_bulk_update": "JOB_NOTIFY_FALLBACK_EMAILS",
    "dev_redirect": "EMAIL_DEV_REDIRECT_TO",
}


def recipients_for(purpose_key):
    """Return (to, cc, bcc) lists of addresses for a purpose key."""
    from notification.models import EmailRecipient

    buckets = {"to": [], "cc": [], "bcc": []}
    rows = (
        EmailRecipient.objects.filter(
            purpose__key=purpose_key,
            purpose__is_active=True,
            is_active=True,
            contact__is_active=True,
        )
        .select_related("contact")
        .order_by("contact__name")
    )
    for row in rows:
        bucket = buckets.get(row.kind)
        if bucket is not None and row.contact.email not in bucket:
            bucket.append(row.contact.email)

    if not buckets["to"]:
        fallback = _settings_fallback(purpose_key)
        if fallback:
            logger.warning(
                "No active TO contacts for purpose %s; using settings fallback",
                purpose_key,
            )
            buckets["to"] = fallback
        else:
            logger.error("No recipients configured for purpose %s", purpose_key)

    return buckets["to"], buckets["cc"], buckets["bcc"]


def _settings_fallback(purpose_key):
    name = SETTINGS_FALLBACK.get(purpose_key)
    if not name:
        return []
    return list(getattr(settings, name, []) or [])


def all_addresses(purpose_key):
    """Flat list of every address on a purpose, for logging and previews."""
    to, cc, bcc = recipients_for(purpose_key)
    return to + cc + bcc
