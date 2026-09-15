"""Direct (subject-level) encounters -> rhs_data, plus the sanitation follow-up table."""

import logging

import dateparser

from avni import mappings, paths, watermark
from avni.client import AvniError, client
from avni.locations import slum_and_city_ids
from avni.sync import households
from graphs.models import FollowupData
from notification.services import reporting

logger = logging.getLogger(__name__)

DIRECT_ENCOUNTER_TYPES = ["Sanitation", "Water", "Waste", "Property tax", "Electricity"]


def has_answers(record):
    return not record.get("Voided") and bool(record.get("observations"))


def encounter_payload(record):
    """Observations renamed to rhs keys, stamped with the AVNI modification time."""
    encounter_type = record.get("Encounter type")
    data = dict(record.get("observations") or {})
    modified_at = (record.get("audit") or {}).get("Last modified at")
    if encounter_type == "Sanitation":
        data = mappings.map_sanitation_keys(data)
        data["submission_date"] = modified_at
    else:
        mappings.rename_keys(data, mappings.ENCOUNTER_RENAMES.get(encounter_type, {}))
        data["Last_modified_date"] = modified_at
    return data


def save_encounter(record, api=None):
    """Merge one direct encounter into its household; sanitation also feeds FollowupData."""
    if not has_answers(record):
        return False
    household = households.fetch_household(record["Subject ID"], api)
    save_encounter_for(household, record)
    return True


def save_encounter_for(household, record):
    data = encounter_payload(record)
    households.merge_into_rhs_data(household, data)
    if record.get("Encounter type") == "Sanitation":
        save_sanitation_followup(household, data)


def save_sanitation_followup(household, data):
    rows = FollowupData.objects.filter(household_number=household.number, slum_id__name=household.slum)
    if not rows.exists():
        slum_id, city_id = slum_and_city_ids(household.slum)
        FollowupData.objects.create(
            household_number=household.number,
            slum_id=slum_id,
            city_id=city_id,
            submission_date=household.submitted_on,
            followup_data=data,
            created_date=household.record["audit"]["Created at"],
            flag_followup_in_rhs=False,
        )
        return
    for row in rows:
        followup = row.followup_data or {}
        followup.update(data)
        rows.update(followup_data=followup, submission_date=dateparser.parse(household.submitted_on))


def sync_encounters(encounter_type, from_date=None, api=None):
    """Pull every encounter of one type modified since the window start."""
    api = api or client()
    since = watermark.window_start(from_date=from_date)
    saved = 0
    for page in api.iter_pages(paths.encounters(encounter_type, since)):
        for record in page:
            saved += int(save_encounter_record(record, api))
    return saved


def save_encounter_record(record, api=None):
    """Save one listed encounter against the active job step."""
    if not has_answers(record):
        reporting.skip(reason="voided or empty observations")
        return False
    try:
        household = households.fetch_household(record["Subject ID"], api)
    except AvniError as exc:
        with reporting.record(key=record.get("ID")):
            reporting.fail(exc)
        return False
    with reporting.record(slum=household.slum, household=household.number, key=record.get("ID")):
        try:
            save_encounter_for(household, record)
            return True
        except Exception as exc:
            logger.error("Encounter %s not saved: %s", record.get("ID"), exc)
            reporting.fail(exc)
            return False


def sync_all_encounters(from_date=None, api=None):
    return {kind: sync_encounters(kind, from_date, api) for kind in DIRECT_ENCOUNTER_TYPES}
