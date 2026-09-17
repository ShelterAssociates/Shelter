"""Per-slum data versions. Older versions are frozen: a record belongs to the
version that was current at its last-modified moment, so re-surveying a slum
starts a clean version without touching what was already collected.
"""

from django.utils import timezone

from survey.models import SlumDataVersion


def starts_for_slum(slum_id, cache=None):
    """[(started_on, version), ...] oldest first, memoised per run."""
    if cache is not None and slum_id in cache:
        return cache[slum_id]
    rows = list(
        SlumDataVersion.objects.filter(slum_id=slum_id)
        .order_by("started_on")
        .values_list("started_on", "version")
    )
    if cache is not None:
        cache[slum_id] = rows
    return rows


def version_for(slum_id, moment=None, cache=None):
    """The version current in this slum at `moment`. Version 1 is implicit."""
    if not slum_id:
        return 1
    moment = moment or timezone.now()
    version = 1
    for started_on, number in starts_for_slum(slum_id, cache):
        if started_on <= moment and number > version:
            version = number
    return version


def current_version(slum_id, cache=None):
    return version_for(slum_id, timezone.now(), cache)
