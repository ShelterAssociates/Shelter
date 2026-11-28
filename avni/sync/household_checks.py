"""Possible duplicate households, checked when a household is saved and re-checked nightly.

- family: one family registered under two numbers - the same 10-digit mobile and
  head of household (or interviewee, on the Detailed Socio Economic Survey) in one slum.
- number_again: the household number typed a second time is another household's number.

Reads only HouseholdData of the household's slum, so the sync makes no extra AVNI call.
"""

import logging
import re

from graphs.models import HouseholdData
from survey import duplicates
from survey.identity import household_number_from
from survey.models import SyncDuplicate

logger = logging.getLogger(__name__)

PROVIDER = "avni"
MOBILE = "group_el9cl08/Enter_the_10_digit_mobile_number"
HEADS = ("group_og5bx85/Full_name_of_the_head_of_the_household", "Name of Interviewee ?")
AGAIN = "Enter_household_number_again"
PLACEHOLDER_MOBILES = {"0000000000", "1111111111", "9999999999", "1234567890"}
SHORTEST_NAME = 6


def mobile_of(data):
    digits = re.sub(r"\D", "", str(data.get(MOBILE) or ""))[-10:]
    return digits if len(digits) == 10 and digits not in PLACEHOLDER_MOBILES else ""


def head_of(data):
    """(name as written, comparison key) of the head of household; key is '' when too short to trust."""
    for key in HEADS:
        name = str(data.get(key) or "").strip()
        if name:
            compared = re.sub(r"[^a-z]", "", name.lower())
            return name, compared if len(compared) >= SHORTEST_NAME else ""
    return "", ""


def masked(mobile):
    return "XXXXXX" + mobile[-4:]


def uuid_of(row):
    return (row.rhs_data or {}).get("rhs_uuid")


def family_rows(slum_id, mobile, head_key):
    rows = HouseholdData.objects.filter(slum_id=slum_id, rhs_data__contains=mobile[-4:]).only(
        "id", "slum_id", "city_id", "household_number", "rhs_data")
    return [row for row in rows if uuid_of(row) and mobile_of(row.rhs_data or {}) == mobile
            and head_of(row.rhs_data or {})[1] == head_key]


def flag_family(row):
    data = row.rhs_data or {}
    mobile, (head, head_key) = mobile_of(data), head_of(data)
    if not mobile or not head_key:
        return None
    rows = family_rows(row.slum_id, mobile, head_key)
    if len({uuid_of(item) for item in rows}) < 2:
        return None
    return duplicates.remember(
        PROVIDER, SyncDuplicate.FAMILY, "{}:{}:{}".format(row.slum_id, mobile, head_key),
        [uuid_of(item) for item in rows], slum_id=row.slum_id, city_id=row.city_id,
        details={"numbers": sorted({item.household_number for item in rows}, key=lambda n: (len(n), n)),
                 "head": head, "mobile": masked(mobile)})


def clashing_row(row):
    again = household_number_from((row.rhs_data or {}).get(AGAIN))
    if not again or again == household_number_from(row.household_number):
        return None
    other = HouseholdData.objects.filter(slum_id=row.slum_id, household_number=again).exclude(id=row.id).first()
    return other if other is not None and uuid_of(other) else None


def flag_number_again(row):
    other = clashing_row(row)
    if other is None:
        return None
    number = household_number_from(row.household_number)
    return duplicates.remember(
        PROVIDER, SyncDuplicate.NUMBER_AGAIN, "{}:{}:again".format(row.slum_id, number),
        [uuid_of(row), uuid_of(other)], slum_id=row.slum_id, city_id=row.city_id, household_number=number,
        details={"numbers": [number, other.household_number], "entered_again": other.household_number})


def in_open_group(subject_uuid):
    """True when this household is in an open same-family or number-again group: an answer cleared in AVNI
    must then clear here too, or the group could never close."""
    return SyncDuplicate.objects.filter(
        provider=PROVIDER, status=SyncDuplicate.OPEN, kind__in=(SyncDuplicate.FAMILY, SyncDuplicate.NUMBER_AGAIN),
        external_ids__contains=subject_uuid).exists()


def flag(row):
    """Both checks for one saved household; never breaks the sync."""
    if row is None or not uuid_of(row):
        return
    try:
        flag_family(row)
        flag_number_again(row)
    except Exception as exc:
        logger.warning("Duplicate checks for household %s in slum %s skipped: %s", row.household_number, row.slum_id, exc)


def still_holds(group):
    rows = [row for uuid in group.external_ids
            for row in HouseholdData.objects.filter(slum_id=group.slum_id, rhs_data__contains=uuid) if uuid_of(row) == uuid]
    if group.kind == SyncDuplicate.FAMILY:
        _, mobile, head_key = group.key.split(":", 2)
        return len({uuid_of(row) for row in rows if mobile_of(row.rhs_data or {}) == mobile
                    and head_of(row.rhs_data or {})[1] == head_key}) > 1
    first = next((row for row in rows if uuid_of(row) == group.external_ids[0]), None)
    return first is not None and clashing_row(first) is not None


def recheck():
    """Close family / number-again groups that no longer hold. Returns how many closed."""
    closed = 0
    for group in SyncDuplicate.objects.filter(provider=PROVIDER, status=SyncDuplicate.OPEN,
                                              kind__in=(SyncDuplicate.FAMILY, SyncDuplicate.NUMBER_AGAIN)):
        if not still_holds(group):
            duplicates.resolve(group, "corrected in AVNI")
            closed += 1
    return closed
