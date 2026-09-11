"""Notifications for photo exports.

Two deliberately different audiences:

* **Success** goes to whoever asked for the export, with the developer in CC.
* **Any failure** -- disk space, Avni, a job killed by a deploy -- goes to the
  developer ONLY. The requester is not told, because every failure here needs a
  developer to do something (free disk, fix Avni access) before a re-run can
  succeed; telling the requester would just invite them to retry into the same
  wall.
"""

import logging

from django.conf import settings

from helpers.services.send_email import send_email

logger = logging.getLogger(__name__)


def developer_emails():
    """Address-book contacts for photo_export_failure, falling back to
    PHOTO_EXPORT_NOTIFY_EMAILS while the table is empty."""
    from notification.services import contacts

    to, cc, bcc = contacts.recipients_for("photo_export_failure")
    return to + cc + bcc


def _download_url(job):
    base = (getattr(settings, "BASE_APP_URL", "") or "").rstrip("/")
    return "{}/photos/exports/{}/download/".format(base, job.pk)


def send_success_email(job):
    if not job.email:
        return
    context = {
        "scope": job.scope,
        "photo_count": job.item_count,
        "size": job.size_display,
        "download_url": _download_url(job),
        "failures": job.failures or [],
        "failure_count": len(job.failures or []),
        "expiry_note": (
            "This link stays available for 24 hours, after which the file is "
            "removed by the nightly cleanup job. Request the export again if "
            "you need it later."
        ),
    }
    try:
        send_email(
            [job.email],
            "Your Shelter photo export is ready",
            "helpers/photo_export_ready_email.html",
            context,
            "Your photo export is ready: {}".format(context["download_url"]),
            cc=developer_emails() or None,
        )
    except Exception:
        logger.exception("Could not send photo export success email for %s", job.pk)


def send_failure_email(job):
    recipients = developer_emails()
    if not recipients:
        logger.error(
            "Photo export %s failed but no photo_export_failure contacts exist, "
            "so nobody was told. Add one in admin under Email purposes.",
            job.pk,
        )
        return
    context = {
        "job_id": job.pk,
        "scope": job.scope,
        "requested_by": (
            job.requested_by.get_username() if job.requested_by else "unknown"
        ),
        "requester_email": job.email,
        "error": job.error or "Unknown error",
        "failures": job.failures or [],
        "failure_count": len(job.failures or []),
    }
    try:
        send_email(
            recipients,
            "Shelter photo export FAILED (#{})".format(job.pk),
            "helpers/photo_export_failed_email.html",
            context,
            "Photo export #{} failed: {}".format(job.pk, context["error"]),
        )
    except Exception:
        logger.exception("Could not send photo export failure email for %s", job.pk)
