"""Program encounters: Family factsheet -> ff_data, Daily Reporting -> ToiletConstruction."""

import logging

import dateparser

from avni import mappings, paths, watermark
from avni.client import AvniError, client
from avni.locations import slum_and_city_ids
from avni.sync import households
from graphs.models import HouseholdData
from mastersheet.models import ToiletConstruction
from notification.services import reporting

logger = logging.getLogger(__name__)

FAMILY_FACTSHEET = "Family factsheet"
DAILY_REPORTING = "Daily Reporting"
DAILY_REPORTING_TYPES = (DAILY_REPORTING, "Household Level Daily Reporting")

PHASE_ONE_MATERIALS = [
    "Date on which bricks are given",
    "Date on which sand is given",
    "Date on which crush sand is given",
    "Date on which river sand is given",
    "Date on which cement is given",
    "Date on which Pre mix plaster are given ?",
    "Date on which Sanala are given ?",
]
PHASE_TWO_MATERIALS = [
    "Date on which other hardware items are given",
    "Date on which pan is given",
    "Date on which Tiles are given",
]
SHIFTED_TO = {
    "p1_material_shifted_to": "House numbers of houses where PHASE 1 material bricks, sand and cement is given",
    "p2_material_shifted_to": "House numbers of houses where PHASE 2 material Hardware is given",
    "p3_material_shifted_to": "House numbers where material is shifted - 3rd Phase",
    "st_material_shifted_to": "House numbers of houses where Septic Tank is given",
}

STATUS_AGREEMENT_CANCELLED = 2
STATUS_MATERIAL_NOT_GIVEN = 3
STATUS_UNDER_CONSTRUCTION = 5
STATUS_COMPLETED = 6


def has_answers(record):
    return not record.get("Voided") and bool(record.get("observations"))


def parse_date(value):
    return dateparser.parse(value).date() if value else None


# -- family factsheet ------------------------------------------------------

def sync_family_factsheets(from_date=None, api=None):
    return sync_program_encounters(FAMILY_FACTSHEET, from_date, api)


def save_family_factsheet(record, household):
    """Write ff_data and the factsheet dates on ToiletConstruction."""
    slum_id, city_id = slum_and_city_ids(household.slum)
    rows = HouseholdData.objects.filter(household_number=household.number, city_id=city_id, slum_id=slum_id)
    if not rows.exists():
        households.save_household(household.record)
        rows = HouseholdData.objects.filter(household_number=household.number, city_id=city_id, slum_id=slum_id)
    ff_data = mappings.map_factsheet_keys(record["observations"])
    ff_data["ff_uuid"] = record["ID"]
    rows.update(ff_data=ff_data)

    done_on = parse_date(record["audit"]["Last modified at"])
    ToiletConstruction.objects.filter(household_number=household.number, slum_id=slum_id).update(
        factsheet_done=done_on, **factsheet_toilet_dates(record["observations"], done_on)
    )


def factsheet_toilet_dates(observations, done_on):
    connected = observations.get("Where the individual toilet is connected ?")
    in_use = observations.get("Use of toilet")
    return {
        "toilet_connected_to": done_on if connected not in (None, "Not connected") else None,
        "use_of_toilet": done_on if in_use is not None else None,
    }


# -- daily reporting -------------------------------------------------------

def sync_daily_reporting(from_date=None, api=None):
    return sync_program_encounters(DAILY_REPORTING, from_date, api)


def save_daily_reporting(observations, slum_name, household_number, source_uuid=None):
    """Upsert the ToiletConstruction row from one Daily Reporting encounter.

    `source_uuid` is the AVNI program encounter id; the Kobo path passes None.
    """
    slum_id, city_id = slum_and_city_ids(slum_name)
    fields = toilet_construction_fields(observations)
    if fields is None or len(observations) <= 1:
        return False
    rows = ToiletConstruction.objects.filter(household_number=household_number, slum_id=slum_id)
    if rows.exists():
        if source_uuid:
            fields["source_uuid"] = source_uuid
        rows.update(**fields)
    else:
        ToiletConstruction.objects.create(
            household_number=household_number, slum_id=slum_id, source_uuid=source_uuid, **fields
        )
    return True


def toilet_construction_fields(data):
    """All ToiletConstruction columns derived from the answers, or None when the
    material moved to another slum (nothing to record here)."""
    shifted = data.get("Is the material is shifted ?")
    if shifted == "Yes, Outside the Slum":
        return None
    cancelled = "Date on which agreement is cancelled" in data
    shifted_within_slum = shifted == "Yes, Within the Slum"

    def date_unless_shifted(value, shifted_key):
        blocked = cancelled or (shifted_within_slum and SHIFTED_TO[shifted_key] in data)
        return None if blocked or not value else value

    phase_one = latest_date(data, PHASE_ONE_MATERIALS)
    phase_two = latest_date(data, PHASE_TWO_MATERIALS)
    fields = {
        "agreement_date": parse_date(data.get("Date of agreement")),
        "agreement_cancelled": cancelled,
        "septic_tank_date": parse_date(date_unless_shifted(data.get("Date on which septic tank is given"), "st_material_shifted_to")),
        "phase_one_material_date": date_unless_shifted(phase_one, "p1_material_shifted_to"),
        "phase_two_material_date": date_unless_shifted(phase_two, "p2_material_shifted_to"),
        "phase_three_material_date": parse_date(date_unless_shifted(data.get("Date on which door is given"), "p3_material_shifted_to")),
        "completion_date": parse_date(data.get("Date on which toilet construction is complete")),
        "comment": data.get("Comment if any ?"),
    }
    fields.update(shifted_house_numbers(data, cancelled or shifted_within_slum))
    fields["status"] = construction_status(fields)
    return fields


def latest_date(data, keys):
    """Newest of the material dates present, as a naive datetime (legacy column type)."""
    values = sorted((data[key] for key in keys if key in data), reverse=True)
    return dateparser.parse(values[0]).replace(tzinfo=None) if values else None


def shifted_house_numbers(data, shifting_applies):
    numbers = {}
    for field, question in SHIFTED_TO.items():
        value = data.get(question) if shifting_applies else None
        numbers[field] = int(value) if value not in (None, "") else None
    return numbers


def construction_status(fields):
    materials_given = any(
        fields[key] for key in ("phase_one_material_date", "phase_two_material_date", "phase_three_material_date")
    )
    if fields["completion_date"] is not None:
        return STATUS_COMPLETED
    if materials_given and not fields["agreement_cancelled"]:
        return STATUS_UNDER_CONSTRUCTION
    if fields["agreement_date"] is not None and not materials_given and not fields["agreement_cancelled"]:
        return STATUS_MATERIAL_NOT_GIVEN
    if fields["agreement_cancelled"]:
        return STATUS_AGREEMENT_CANCELLED
    return None


# -- shared ----------------------------------------------------------------

def save_program_encounter(record, household):
    """Dispatch one program encounter to its handler. Returns True when something was written."""
    encounter_type = record.get("Encounter type")
    if encounter_type == FAMILY_FACTSHEET:
        save_family_factsheet(record, household)
        return True
    if encounter_type in DAILY_REPORTING_TYPES:
        return save_daily_reporting(record["observations"], household.slum, household.number, record.get("ID"))
    raise LookupError("Program encounter type {} has no handler".format(encounter_type))


def save_program_encounter_record(record, api=None):
    """Save one listed program encounter against the active job step."""
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
            return save_program_encounter(record, household)
        except Exception as exc:
            logger.error("Program encounter %s not saved: %s", record.get("ID"), exc)
            reporting.fail(exc)
            return False


def sync_program_encounters(encounter_type, from_date=None, api=None):
    api = api or client()
    since = watermark.window_start(from_date=from_date)
    saved = 0
    for page in api.iter_pages(paths.program_encounters(encounter_type, since)):
        for record in page:
            saved += int(save_program_encounter_record(record, api))
    return saved


def sync_program_encounter_by_uuid(encounter_uuid, api=None):
    api = api or client()
    record = api.get_json(paths.program_encounter(encounter_uuid))
    return save_program_encounter_record(record, api)
