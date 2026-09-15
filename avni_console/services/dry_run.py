"""Synchronous 'how much would this pull?' counts for the console."""

from datetime import date

from avni import paths, watermark
from avni.client import AvniError, client
from avni.jobs.manual_sync import HOUSEHOLD_SUBJECT_TYPES

COUNT_TIMEOUT_SECONDS = 150
WIDE_WINDOW_DAYS = 60


def count_households(subject_types, from_date, api=None):
    """Exact record counts (voided included) per subject type since from_date."""
    unknown = [kind for kind in subject_types if kind not in HOUSEHOLD_SUBJECT_TYPES]
    if unknown:
        raise ValueError("Unknown subject type(s): {}".format(", ".join(unknown)))
    api = api or client()
    since = watermark.format_from_date(from_date)
    result = {"window_start": since, "counts": {}, "errors": {}, "warning": ""}
    for subject_type in subject_types:
        try:
            result["counts"][subject_type] = api.count(paths.subjects(subject_type, since), timeout=COUNT_TIMEOUT_SECONDS)
        except AvniError as exc:
            result["errors"][subject_type] = str(exc)
    if window_days(from_date) > WIDE_WINDOW_DAYS:
        result["warning"] = (
            "This window is over {} days; AVNI answers slowly for wide windows and the "
            "queued sync will take a while.".format(WIDE_WINDOW_DAYS)
        )
    return result


def window_days(from_date):
    start = date(*[int(part) for part in str(from_date)[:10].split("-")])
    return (date.today() - start).days
