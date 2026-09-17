"""Family members -> graphs.MemberData / MemberProgramData / MemberEncounterData.

Two sources feed the same writers: the JSON exports (import_* below, unchanged)
and, through avni.provider, live Family Member subjects, enrolments and program
encounters (save_*_from_record). The record adapters read these AVNI fields:

  subject           ID, location.Slum, observations["First name" / "Last name"],
                    "Date of birth" and "Gender" (top level, falling back to
                    observations), household number from observations
                    (HOUSEHOLD_NUMBER_KEYS) or the first entry of "Groups"
  enrolment         ID, Subject ID, Program, Enrolment datetime, Exit datetime,
                    observations
  program encounter ID, Subject ID, Enrolment ID, Encounter type,
                    Encounter date time, observations

Verify these on one live Family Member before enabling the member switches in
Admin -> Survey -> Sync switches; they ship switched off.
"""

import json
import logging
from datetime import datetime

from graphs.models import MemberData, MemberEncounterData, MemberProgramData
from master.models import Slum
from notification.services import reporting

logger = logging.getLogger(__name__)

GENDER_CODES = {"Male": "1", "Female": "2"}
HOUSEHOLD_NUMBER_KEYS = ("Household number", "Househhold number", "House number", "Parent household number")


def load_rows(file_path):
    with open(file_path) as handle:
        return json.load(handle)


def iso_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def import_rows(file_path, save_row):
    saved = 0
    for row in load_rows(file_path):
        with reporting.record(slum=row.get("slum"), key=row.get("member_uuid") or row.get("member_id")):
            try:
                saved += int(save_row(row))
            except Exception as exc:
                logger.error("Member row %s not imported: %s", row.get("member_uuid") or row.get("member_id"), exc)
                reporting.fail(exc)
    return saved


# -- writers shared by both sources ------------------------------------------

def write_member(slum, member_uuid, fields):
    MemberData.objects.update_or_create(slum=slum, member_uuid=member_uuid, defaults=fields)
    return True


def write_member_program(member, fields):
    MemberProgramData.objects.update_or_create(member=member, slum=member.slum, defaults=fields)
    return True


def write_member_encounter(member, program, fields):
    MemberEncounterData.objects.update_or_create(member=member, slum=member.slum, program=program, defaults=fields)
    return True


def member_for(member_uuid):
    member = MemberData.objects.filter(member_uuid=member_uuid).first()
    if member is None:
        raise LookupError("Member {} not available".format(member_uuid))
    return member


# -- JSON export rows ---------------------------------------------------------

def save_member(row):
    slum = Slum.objects.filter(name=row["slum"]).first()
    if slum is None:
        return False
    fields = dict(row)
    member_uuid = fields.pop("member_uuid")
    fields.pop("slum")
    fields["created_date"] = iso_date(row["created_date"])
    fields["submission_date"] = iso_date(row["submission_date"])
    fields["date_of_birth"] = datetime.strptime(row["date_of_birth"], "%B %d, %Y").date()
    fields["household_number"] = str(row["household_number"]).strip() if row["household_number"] else None
    fields["gender"] = GENDER_CODES.get(row["gender"], "3")
    return write_member(slum, member_uuid, fields)


def save_member_program(row):
    member = member_for(row["member_id"])
    fields = {
        key: value for key, value in row.items()
        if key not in ("family_member_menstrual_hygiene__uuid", "first_name", "member_id", "program_exit_date")
    }
    fields["created_date"] = iso_date(row["created_date"])
    fields["submission_date"] = iso_date(row["submission_date"])
    fields["program_uuid"] = row["family_member_menstrual_hygiene__uuid"]
    if row.get("program_exit_date"):
        fields["program_exit_date"] = iso_date(row["program_exit_date"])
    return write_member_program(member, fields)


def save_member_encounter(row):
    member = member_for(row["member_id"])
    program = MemberProgramData.objects.filter(member=member).first()
    fields = {
        key: value for key, value in row.items()
        if key not in ("program_id", "member_id", "program__name", "first_name")
    }
    fields["created_date"] = iso_date(row["created_date"])
    fields["submission_date"] = iso_date(row["submission_date"])
    return write_member_encounter(member, program, fields)


def import_members(file_path):
    return import_rows(file_path, save_member)


def import_member_programs(file_path):
    return import_rows(file_path, save_member_program)


def import_member_encounters(file_path):
    return import_rows(file_path, save_member_encounter)


# -- live AVNI records --------------------------------------------------------

def record_day(value):
    """AVNI ISO stamp or 'YYYY-MM-DD' -> date, or None."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def audit_days(record):
    audit = record.get("audit") or {}
    return {
        "created_date": record_day(audit.get("Created at")),
        "submission_date": record_day(audit.get("Last modified at")),
    }


def member_household_number(record):
    observations = record.get("observations") or {}
    for key in HOUSEHOLD_NUMBER_KEYS:
        if observations.get(key) not in (None, ""):
            return str(observations[key]).strip()[:5]
    groups = record.get("Groups") or []
    if groups and isinstance(groups[0], dict):
        number = groups[0].get("Household number") or groups[0].get("First name")
        if number:
            return str(number).strip()[:5]
    return None


def save_member_from_record(record):
    """One Family Member subject -> MemberData."""
    slum = Slum.objects.filter(name=(record.get("location") or {}).get("Slum")).first()
    if slum is None:
        return False
    observations = record.get("observations") or {}
    fields = {
        "member_first_name": (observations.get("First name") or record.get("First name") or "")[:100],
        "member_last_name": (observations.get("Last name") or record.get("Last name") or "")[:100],
        "date_of_birth": record_day(record.get("Date of birth") or observations.get("Date of birth")),
        "gender": GENDER_CODES.get(record.get("Gender") or observations.get("Gender"), "3"),
        "household_number": member_household_number(record),
        "member_data": observations,
    }
    fields.update(audit_days(record))
    return write_member(slum, record["ID"], fields)


def save_member_program_from_record(record):
    """One program enrolment of a Family Member -> MemberProgramData."""
    member = member_for(record["Subject ID"])
    fields = {
        "program_uuid": record.get("ID") or "",
        "program_name": (record.get("Program") or "")[:100],
        "program_exit_date": record_day(record.get("Exit datetime") or record.get("Program exit date time")),
        "program_data": record.get("observations") or {},
    }
    fields.update(audit_days(record))
    if not fields["created_date"]:
        fields["created_date"] = record_day(record.get("Enrolment datetime"))
    return write_member_program(member, fields)


def save_member_encounter_from_record(record):
    """One program encounter of a Family Member -> MemberEncounterData."""
    member = member_for(record["Subject ID"])
    program = MemberProgramData.objects.filter(member=member, program_uuid=record.get("Enrolment ID") or "").first()
    if program is None:
        program = MemberProgramData.objects.filter(member=member).first()
    fields = {
        "encounter_uuid": record.get("ID") or "",
        "encounter_name": (record.get("Encounter type") or "")[:100],
        "encounter_data": record.get("observations") or {},
    }
    fields.update(audit_days(record))
    return write_member_encounter(member, program, fields)
