"""Re-sync individual AVNI records by uuid (the old SaveDataFromIds)."""

import logging

from avni import paths
from avni.client import AvniError, client
from avni.sync import encounters, households, mobilization, program_encounters
from notification.services import reporting

logger = logging.getLogger(__name__)

SUBJECT, ENCOUNTER, PROGRAM_ENCOUNTER = "subject", "encounter", "program_encounter"
KINDS = (SUBJECT, ENCOUNTER, PROGRAM_ENCOUNTER)

SUBJECT_HANDLERS = {
    "Household": households.save_household,
    "Structure": households.save_household,
    "New_Mobilization_Form": mobilization.save_mobilization,
}

ACTIVITY_ENCOUNTER = "Daily Mobilization Activity"


def fetch(kind, uuid, api):
    path = {SUBJECT: paths.subject, ENCOUNTER: paths.encounter, PROGRAM_ENCOUNTER: paths.program_encounter}[kind]
    return api.get_json(path(uuid))


def save_subject(record, api, subject_type="Household"):
    """api/subject/{id} does not say its subject type, so the caller names it."""
    handler = SUBJECT_HANDLERS.get(subject_type)
    if handler is None:
        raise LookupError("No handler for subject type {}".format(subject_type))
    return handler(record)


def save_encounter(record, api):
    if record.get("Encounter type") != ACTIVITY_ENCOUNTER:
        return encounters.save_encounter(record, api)
    household = households.fetch_household(record["Subject ID"], api)
    mobilization.save_activity_attendance(record["observations"], household.slum, household.number)
    return True


def save_program_encounter(record, api):
    household = households.fetch_household(record["Subject ID"], api)
    return program_encounters.save_program_encounter(record, household)


SAVERS = {ENCOUNTER: save_encounter, PROGRAM_ENCOUNTER: save_program_encounter}


def sync_by_uuid(kind, uuids, api=None, subject_type="Household"):
    """Fetch and save each uuid of one kind; returns {saved, skipped, failed}.

    `subject_type` matters only for kind "subject" (Household, Structure, New_Mobilization_Form).
    """
    if kind not in KINDS:
        raise ValueError("kind must be one of {}".format(", ".join(KINDS)))
    if kind == SUBJECT and subject_type not in SUBJECT_HANDLERS:
        raise ValueError("subject_type must be one of {}".format(", ".join(sorted(SUBJECT_HANDLERS))))
    api = api or client()
    counts = {"saved": 0, "skipped": 0, "failed": 0}
    for uuid in uuids:
        outcome = sync_one(kind, uuid, api, subject_type)
        counts[outcome] += 1
    return counts


def sync_one(kind, uuid, api, subject_type="Household"):
    with reporting.record(key=uuid):
        try:
            record = fetch(kind, uuid, api)
        except AvniError as exc:
            reporting.fail(exc)
            return "failed"
        if record.get("Voided") or not record.get("observations"):
            reporting.skip(reason="voided or empty observations")
            return "skipped"
        try:
            if kind == SUBJECT:
                saved = save_subject(record, api, subject_type)
            else:
                saved = SAVERS[kind](record, api)
            return "saved" if saved else "skipped"
        except Exception as exc:
            logger.error("%s %s not saved: %s", kind, uuid, exc)
            reporting.fail(exc)
            return "failed"
