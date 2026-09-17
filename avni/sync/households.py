"""Household / Structure registration subjects -> graphs.HouseholdData.rhs_data."""

import logging
from collections import namedtuple

from django.utils import timezone

from avni import mappings, paths
from avni.client import AvniError, client
from avni.locations import slum_and_city_ids
from graphs.models import HouseholdData
from notification.services import reporting

logger = logging.getLogger(__name__)

Household = namedtuple("Household", "city slum number submitted_on record")


def fetch_subject(subject_uuid, api=None):
    return (api or client()).get_json(paths.subject(subject_uuid))


def household_from_record(record):
    """City, slum, household number and last-modified stamp of a subject record."""
    location = record.get("location") or {}
    number = mappings.household_number_from((record.get("observations") or {}).get("First name"))
    return Household(
        city=location.get("City"),
        slum=location.get("Slum"),
        number=number,
        submitted_on=(record.get("audit") or {}).get("Last modified at"),
        record=record,
    )


def fetch_household(subject_uuid, api=None):
    return household_from_record(fetch_subject(subject_uuid, api))


def save_household(record):
    """Create or update the HouseholdData row for one subject record."""
    observations = mappings.normalize_occupancy(dict(record.get("observations") or {}))
    household = household_from_record(record)
    try:
        if not household.number:
            raise ValueError("subject has no First name (household number)")
        slum_id, city_id = slum_and_city_ids(household.slum)
        retire_stale_rows(record["ID"], slum_id, city_id, household.number)
        existing = HouseholdData.objects.filter(
            household_number=household.number, city_id=city_id, slum_id=slum_id
        )
        if existing.exists():
            update_household(existing, record, observations)
        else:
            create_household(slum_id, city_id, record, observations)
        return True
    except Exception as exc:
        logger.error("Household %s in %s not saved: %s", household.number, household.slum, exc)
        reporting.fail(exc)
        return False


def rows_for_subject(subject_uuid):
    """Every HouseholdData row carrying this subject's uuid (rhs_data is text, so LIKE then confirm)."""
    rows = HouseholdData.objects.filter(rhs_data__contains=subject_uuid)
    return [row for row in rows if (row.rhs_data or {}).get("rhs_uuid") == subject_uuid]


def plan_stale_rows(subject_uuid, slum_id, number):
    """Rows this subject left behind after a renumber or slum move in AVNI.

    Returns (row to rename, rows to delete): the newest stale row is renamed
    when the new number has no row yet, every other one is a duplicate.
    """
    stale = [
        row for row in rows_for_subject(subject_uuid)
        if (row.household_number, row.slum_id) != (number, slum_id)
    ]
    stale.sort(key=lambda row: row.submission_date, reverse=True)
    if not stale or HouseholdData.objects.filter(household_number=number, slum_id=slum_id).exists():
        return None, stale
    return stale[0], stale[1:]


def retire_stale_rows(subject_uuid, slum_id, city_id, number):
    rename, delete = plan_stale_rows(subject_uuid, slum_id, number)
    if rename is not None:
        logger.info("Household %s in slum %s renamed to %s (subject %s)", rename.household_number, rename.slum_id, number, subject_uuid)
        rename.household_number, rename.slum_id, rename.city_id = number, slum_id, city_id
        rename.save(update_fields=["household_number", "slum", "city"])
    for row in delete:
        logger.info("Household %s in slum %s removed: subject %s is now %s in slum %s", row.household_number, row.slum_id, subject_uuid, number, slum_id)
        row.delete()
    return len(delete) + int(rename is not None)


def remove_voided_household(record):
    """A subject voided in AVNI takes its HouseholdData rows with it (matched by uuid, never by number)."""
    rows = rows_for_subject(record["ID"])
    for row in rows:
        logger.info("Household %s in slum %s removed: subject %s voided", row.household_number, row.slum_id, record["ID"])
        row.delete()
    return len(rows)


def registration_fields(record):
    return {
        "submission_date": record["audit"]["Last modified at"],
        "created_date": registration_datetime(record["Registration date"]),
    }


def registration_datetime(value):
    """AVNI gives a bare 'YYYY-MM-DD'; store it as local midnight, not a naive datetime."""
    parsed = timezone.datetime.strptime(value[:10], "%Y-%m-%d")
    return timezone.make_aware(parsed)


def create_household(slum_id, city_id, record, observations):
    rhs_data = mappings.merge_rhs_keys({}, observations)
    mappings.apply_household_overrides(rhs_data)
    rhs_data["rhs_uuid"] = record["ID"]
    rhs_data.setdefault("group_og5bx85/Type_of_survey", "RHS")
    HouseholdData.objects.create(
        household_number=mappings.household_number_from(observations.get("First name")),
        slum_id=slum_id,
        city_id=city_id,
        rhs_data=rhs_data,
        **registration_fields(record)
    )


def update_household(existing, record, observations):
    rhs_data = mappings.normalize_occupancy(existing.values_list("rhs_data", flat=True)[0] or {})
    mappings.apply_household_overrides(observations)
    rhs_data = mappings.merge_rhs_keys(rhs_data, observations)
    rhs_data["rhs_uuid"] = record["ID"]
    rhs_data["group_og5bx85/Type_of_survey"] = "RHS"
    existing.update(rhs_data=rhs_data, **registration_fields(record))


def sync_households(subject_type, from_date=None, api=None, context=None):
    """Pull every Household/Structure subject modified since the window start.

    Runs through survey.connector so the core store is fed in the same pass.
    """
    from avni.provider import sync_context
    from survey import connector

    return connector.sync_kind("subject", subject_type, from_date=from_date, context=context or sync_context(api))


def save_household_record(record):
    """Record one listed subject against the active job step; voided ones are skipped."""
    slum = (record.get("location") or {}).get("Slum")
    if record.get("Voided"):
        reporting.skip(slum=slum, reason="voided")
        remove_voided_household(record)
        return False
    number = (record.get("observations") or {}).get("First name")
    with reporting.record(slum=slum, household=number, key=record.get("ID")):
        return save_household(record)


def sync_household_by_uuid(subject_uuid, api=None):
    try:
        record = fetch_subject(subject_uuid, api)
    except AvniError as exc:
        logger.error("Subject %s not fetched: %s", subject_uuid, exc)
        return False
    return save_household_record(record)


def sync_households_by_uuid(subject_uuids, api=None):
    return sum(int(sync_household_by_uuid(uuid, api)) for uuid in subject_uuids)


def merge_into_rhs_data(household, data):
    """Merge encounter answers into the household's rhs_data, registering it first if unknown."""
    rows = HouseholdData.objects.filter(slum_id__name=household.slum, household_number=household.number)
    if not rows.exists():
        save_household(household.record)
        rows = HouseholdData.objects.filter(slum_id__name=household.slum, household_number=household.number)
    rhs_data = rows.values_list("rhs_data", flat=True)[0] or {}
    rhs_data.update(data)
    rows.update(rhs_data=rhs_data)
