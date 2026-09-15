"""Imports from JSON files exported out of AVNI (deploy/encounter_sync.sh).

Each file is a list of flat dicts: household identity columns plus the
encounter answers already keyed the rhs_data way.
"""

import json
import logging

from avni import mappings
from avni.locations import slum_and_city_ids
from avni.sync import households
from graphs.models import FollowupData, HouseholdData
from notification.services import reporting

logger = logging.getLogger(__name__)

IDENTITY_KEYS = [
    "household_number", "Slum", "Last_modified_date", "Household_uuid",
    "HH_last_modified_date", "HH_created_date",
]

ELECTRICITY_KEYS = [
    "uuid",
    "Photo for electricity bill",
    "Do you lend electricity to any house ?",
    "Do you have electricity in the house ?",
    "Comment if any ?",
    "If borrowed meter, from which house you borrowed?",
    "If yes for electricity ,  type of meter ?",
    "Name on the electricity bill",
    "If yes for lending electricity with other houses , write those ",
    "What is the average monthly billing amount ? (Electricity)",
    "If own meter, then meter/consumer number ?",
]


def load_rows(file_path):
    with open(file_path) as handle:
        return json.load(handle)


def household_rows(slum_name, household_number, household_uuid, api=None):
    """HouseholdData queryset for the row, registering the household from AVNI if missing."""
    rows = HouseholdData.objects.filter(slum_id__name=slum_name, household_number=household_number)
    if not rows.exists():
        households.save_household(households.fetch_subject(household_uuid, api))
        rows = HouseholdData.objects.filter(slum_id__name=slum_name, household_number=household_number)
    return rows


def merge_rhs(rows, data):
    rhs_data = rows.values_list("rhs_data", flat=True)[0] or {}
    rhs_data.update(data)
    rows.update(rhs_data=rhs_data)


def answers_only(row, extra_keys=()):
    """The row without identity columns, empty values and the given extra keys."""
    drop = set(IDENTITY_KEYS) | set(extra_keys) | {key for key, value in row.items() if not value}
    data = {key: value for key, value in row.items() if key not in drop}
    data["Last_modified_date"] = row["Last_modified_date"]
    return data


def import_encounter_rows(file_path, required_key=None, extra_keys=(), after_merge=None, api=None):
    saved = 0
    for row in load_rows(file_path):
        if required_key and not row.get(required_key):
            continue
        number = mappings.household_number_from(row.get("household_number"))
        with reporting.record(slum=row.get("Slum"), household=number, key=row.get("Household_uuid")):
            try:
                if not number:
                    raise ValueError("row has no household_number")
                data = answers_only(row, extra_keys)
                rows = household_rows(row["Slum"], number, row["Household_uuid"], api)
                merge_rhs(rows, data)
                if after_merge:
                    after_merge(row, number, data)
                saved += 1
            except Exception as exc:
                logger.error("Row for household %s not imported: %s", number, exc)
                reporting.fail(exc)
    return saved


def save_followup(row, number, data):
    rows = FollowupData.objects.filter(household_number=number, slum_id__name=row["Slum"])
    if not rows.exists():
        slum_id, city_id = slum_and_city_ids(row["Slum"])
        FollowupData.objects.create(
            household_number=number, slum_id=slum_id, city_id=city_id,
            submission_date=row["HH_created_date"], followup_data=data,
            created_date=row["HH_last_modified_date"], flag_followup_in_rhs=False,
        )
        return
    for followup in rows:
        merged = followup.followup_data or {}
        merged.update(data)
        rows.update(followup_data=merged, submission_date=row["Last_modified_date"])


def import_sanitation(file_path, api=None):
    return import_encounter_rows(
        file_path, extra_keys=["Sanitation_encounter_uuid"], after_merge=save_followup, api=api
    )


def import_water(file_path, api=None):
    return import_encounter_rows(file_path, required_key="group_el9cl08/Type_of_water_connection", api=api)


def import_waste(file_path, api=None):
    return import_encounter_rows(
        file_path, required_key="group_el9cl08/Facility_of_solid_waste_collection", api=api
    )


def electricity_answers(row):
    return {key: row[key] for key in ELECTRICITY_KEYS if key in row and row[key] != "None"}


def import_electricity(file_path, api=None):
    saved = 0
    for row in load_rows(file_path):
        number = mappings.household_number_from(row.get("household__first_name"))
        with reporting.record(slum=row.get("Slum"), household=number, key=row.get("household__uuid")):
            try:
                if not number:
                    raise ValueError("row has no household__first_name")
                slum_id, city_id = slum_and_city_ids(row["Slum"])
                rows = HouseholdData.objects.filter(slum_id=slum_id, household_number=number)
                if not rows.exists():
                    rows = household_rows(row["Slum"], number, row["household__uuid"], api)
                merge_rhs(rows, {"Electricity_data": electricity_answers(row)})
                saved += 1
            except Exception as exc:
                logger.error("Electricity row for household %s not imported: %s", number, exc)
                reporting.fail(exc)
    return saved


def import_households(file_path):
    """A file of raw AVNI subject records (the api/subject shape)."""
    return sum(int(households.save_household_record(record)) for record in load_rows(file_path))
