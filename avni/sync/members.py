"""Family member JSON exports -> graphs.MemberData / MemberProgramData / MemberEncounterData."""

import json
import logging
from datetime import datetime

from graphs.models import MemberData, MemberEncounterData, MemberProgramData
from master.models import Slum
from notification.services import reporting

logger = logging.getLogger(__name__)

GENDER_CODES = {"Male": "1", "Female": "2"}


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
    MemberData.objects.update_or_create(slum=slum, member_uuid=member_uuid, defaults=fields)
    return True


def save_member_program(row):
    member = MemberData.objects.filter(member_uuid=row["member_id"]).first()
    if member is None:
        raise LookupError("Member {} not available".format(row["member_id"]))
    fields = {
        key: value for key, value in row.items()
        if key not in ("family_member_menstrual_hygiene__uuid", "first_name", "member_id", "program_exit_date")
    }
    fields["created_date"] = iso_date(row["created_date"])
    fields["submission_date"] = iso_date(row["submission_date"])
    fields["program_uuid"] = row["family_member_menstrual_hygiene__uuid"]
    if row.get("program_exit_date"):
        fields["program_exit_date"] = iso_date(row["program_exit_date"])
    MemberProgramData.objects.update_or_create(member=member, slum=member.slum, defaults=fields)
    return True


def save_member_encounter(row):
    member = MemberData.objects.filter(member_uuid=row["member_id"]).first()
    if member is None:
        raise LookupError("Member {} not available".format(row["member_id"]))
    program = MemberProgramData.objects.filter(member=member).first()
    fields = {
        key: value for key, value in row.items()
        if key not in ("program_id", "member_id", "program__name", "first_name")
    }
    fields["created_date"] = iso_date(row["created_date"])
    fields["submission_date"] = iso_date(row["submission_date"])
    MemberEncounterData.objects.update_or_create(member=member, slum=member.slum, program=program, defaults=fields)
    return True


def import_members(file_path):
    return import_rows(file_path, save_member)


def import_member_programs(file_path):
    return import_rows(file_path, save_member_program)


def import_member_encounters(file_path):
    return import_rows(file_path, save_member_encounter)
