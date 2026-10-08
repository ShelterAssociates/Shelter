"""Per-slum sync control: turn a slum's sync off, and lock its locations.

Absent setting = today's behaviour, so every slum stays synced until someone
turns it off. Lookups are not cached: the web process would otherwise hold a
stale answer after the page changes a setting.
"""

import logging

from django.utils import timezone

from notification.services import reporting
from survey.models import SlumSyncSetting

logger = logging.getLogger(__name__)

SYNC_OFF_REASON = "sync switched off for this slum"
SYNC_OFF_EXTRA = "sync_off_slums"


def setting_for(slum_id):
    if not slum_id:
        return None
    return SlumSyncSetting.objects.filter(slum_id=slum_id).first()


def is_enabled(slum_id):
    """False only when a setting says so, so an unconfigured slum syncs as today."""
    setting = setting_for(slum_id)
    return True if setting is None else setting.sync_enabled


def is_alias_locked(slum_id):
    setting = setting_for(slum_id)
    return False if setting is None else setting.alias_locked


def locked_slum_ids():
    return set(SlumSyncSetting.objects.filter(alias_locked=True).values_list("slum_id", flat=True))


def disabled_slum_ids():
    return set(SlumSyncSetting.objects.filter(sync_enabled=False).values_list("slum_id", flat=True))


def report_skipped(slum_name):
    """Count the record as skipped and name the slum in the job digest."""
    reporting.skip(slum=slum_name or None, reason=SYNC_OFF_REASON)
    reporting.note_slum(SYNC_OFF_EXTRA, slum_name)


def refuses(slum_id, slum_name=None):
    """True when this slum's sync is off; reports the skip as a side effect."""
    if slum_id is None or is_enabled(slum_id):
        return False
    report_skipped(slum_name)
    return True


def update(slum_id, user=None, sync_enabled=None, alias_locked=None, note=None):
    """Create or change one slum's setting, leaving unnamed flags alone."""
    setting, _ = SlumSyncSetting.objects.get_or_create(slum_id=slum_id)
    if sync_enabled is not None:
        setting.sync_enabled = bool(sync_enabled)
    if alias_locked is not None:
        setting.alias_locked = bool(alias_locked)
    if note is not None:
        setting.note = note
    setting.updated_by = user if getattr(user, "pk", None) else None
    setting.updated_on = timezone.now()
    setting.save()
    logger.info("Slum %s sync setting: enabled=%s locked=%s", slum_id, setting.sync_enabled, setting.alias_locked)
    return setting
