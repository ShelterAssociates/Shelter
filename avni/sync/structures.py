"""Structure / Detailed Socio Economic Survey subjects -> rhs_data (newer mapping style).

Unlike households.py this maps every known question through KNOWN_QUESTION_MAP
and writes unknown questions through unchanged. Used from the shell for bulk
re-syncs by uuid or Excel.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.db import close_old_connections

from avni import excel, mappings, paths
from avni.client import AvniError, client
from avni.locations import slum_and_city_ids
from graphs.models import HouseholdData

logger = logging.getLogger(__name__)

STRUCTURE = "Structure"
DSES = "Detailed Socio Economic Survey"


def save_structure_record(record):
    observations = record.get("observations") or {}
    if not observations:
        return False
    rhs_data = mappings.apply_structure_overrides(mappings.map_known_questions(observations))
    rhs_data.setdefault("group_og5bx85/Type_of_survey", "RHS")
    rhs_data.setdefault("rhs_uuid", record.get("ID") or record.get("uuid"))
    number = mappings.household_number_from(observations.get("First name"))
    rhs_data["Household_number"] = number

    slum_name = (record.get("location") or {}).get("Slum") or record.get("Slum")
    if not slum_name:
        logger.error("Record %s has no slum", rhs_data.get("rhs_uuid"))
        return False
    slum_id, city_id = slum_and_city_ids(slum_name)
    fields = {
        "rhs_data": rhs_data,
        "submission_date": record.get("last_modified_date_time") or (record.get("audit") or {}).get("Last modified at"),
        "created_date": record.get("registration_date") or record.get("Registration date"),
    }
    rows = HouseholdData.objects.filter(household_number=number, slum_id=slum_id, city_id=city_id)
    if rows.exists():
        rows.update(**fields)
    else:
        HouseholdData.objects.create(household_number=number, slum_id=slum_id, city_id=city_id, **fields)
    return True


def sync_subject_type(subject_type, since, location_uuid=None, api=None):
    """Save every non-voided subject of a type modified since `since`; returns saved count."""
    api = api or client()
    saved = 0
    for page in api.iter_pages(paths.subjects(subject_type, since, location_uuid)):
        for record in page:
            if record.get("Voided"):
                continue
            try:
                saved += int(save_structure_record(record))
            except Exception as exc:
                logger.error("%s %s not saved: %s", subject_type, record.get("ID"), exc)
    return saved


def sync_one_uuid(subject_uuid, api):
    """saved / voided / fetch_failed / save_failed / errors for one subject."""
    try:
        record = api.get_json(paths.subject(subject_uuid))
    except AvniError:
        return "fetch_failed"
    if record.get("Voided"):
        return "voided"
    try:
        return "saved" if save_structure_record(record) else "save_failed"
    except Exception as exc:
        logger.error("Subject %s not saved: %s", subject_uuid, exc)
        return "errors"


def sync_one_uuid_in_thread(subject_uuid, api):
    try:
        return sync_one_uuid(subject_uuid, api)
    finally:
        close_old_connections()


def sync_subjects_by_uuid(subject_uuids, workers=5, api=None):
    """Fetch and save many subjects; `workers` > 1 runs them in threads."""
    api = api or client()
    uuids = [str(value).strip() for value in subject_uuids if str(value).strip()]
    counts = {"saved": 0, "voided": 0, "fetch_failed": 0, "save_failed": 0, "errors": 0}
    if workers <= 1:
        for uuid in uuids:
            counts[sync_one_uuid(uuid, api)] += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for future in as_completed([pool.submit(sync_one_uuid_in_thread, uuid, api) for uuid in uuids]):
                counts[future.result()] += 1
    logger.info("Subjects by uuid: %s", counts)
    return counts


def sync_subjects_from_excel(file_path, column="uuid", workers=5, api=None):
    uuids = excel.read_column(file_path, column)
    return sync_subjects_by_uuid(uuids, workers=workers, api=api)


def subject_summary(subject_type, location_uuid, since, api=None):
    """Counts and ward distribution for a subject type at a location; writes nothing."""
    api = api or client()
    summary = {"total": 0, "voided": 0, "not_voided": 0, "ward_distribution": {}}
    for page in api.iter_pages(paths.subjects(subject_type, since, location_uuid)):
        for record in page:
            summary["total"] += 1
            if record.get("Voided"):
                summary["voided"] += 1
                continue
            ward = (record.get("observations") or {}).get("Select Ward") or "Unknown"
            summary["ward_distribution"][ward] = summary["ward_distribution"].get(ward, 0) + 1
    summary["not_voided"] = summary["total"] - summary["voided"]
    return summary
