"""Community mobilization subjects and Daily Mobilization Activity encounters -> mastersheet."""

import logging

import dateparser

from avni import paths, watermark
from avni.client import client
from avni.locations import slum_and_city_ids
from graphs.models import HouseholdData
from mastersheet.models import ActivityType, CommunityMobilization, CommunityMobilizationActivityAttendance
from notification.services import reporting

logger = logging.getLogger(__name__)

SUBJECT_TYPE = "New_Mobilization_Form"

ATTENDEE_QUESTIONS = [
    "Household numbers for which activity attended by girls",
    "Household numbers for which activity attended by boys",
    "Household numbers for which activity attended by female members",
    "Household numbers for which activity attended by male members",
]

# AVNI spelling -> ActivityType name
ACTIVITY_ALIASES = {
    "Samiti meeting{}".format(n): "Samitee meeting {}".format(n) for n in range(1, 6)
}

ATTENDANCE_COUNTS = {
    "males_attended_activity": "Number of Men present",
    "females_attended_activity": "Number of Women present",
    "other_gender_attended_activity": "Number of Other gender members present",
    "girls_attended_activity": "Number of Girls present",
    "boys_attended_activity": "Number of Boys present",
}


def activity_key(name):
    name = ACTIVITY_ALIASES.get(name, name)
    key = ActivityType.objects.filter(name=name).values_list("key", flat=True).first()
    if key is None:
        raise LookupError("No ActivityType named '{}'".format(name))
    return key


def attending_households(observations, slum_id):
    """Household numbers listed in the four attendee questions that exist for the slum."""
    listed = set()
    for question in ATTENDEE_QUESTIONS:
        value = observations.get(question)
        if value and value != "0":
            listed.update(part for part in str(value).split(",") if part)
    known = set(
        HouseholdData.objects.filter(slum_id=slum_id, rhs_data__isnull=False)
        .values_list("household_number", flat=True)
    )
    return sorted(listed & known)


def save_mobilization(record):
    """Upsert the CommunityMobilization row for one mobilization subject."""
    observations = record["observations"]
    slum_id, city_id = slum_and_city_ids(record["location"]["Slum"])
    activity = activity_key(observations["Type of Activity"])
    activity_date = dateparser.parse(observations["Date of Survey"]).date()
    attendees = attending_households(observations, slum_id)

    rows = CommunityMobilization.objects.filter(slum=slum_id, activity_date=activity_date, activity_type_id=activity)
    if not rows.exists():
        CommunityMobilization.objects.create(
            slum_id=slum_id, household_number=attendees, activity_type_id=activity, activity_date=activity_date
        )
        return True
    existing = [number for number in (rows.values_list("household_number", flat=True)[0] or []) if number]
    rows.update(household_number=sorted(set(existing) | set(attendees)))
    return True


def save_mobilization_record(record):
    slum = (record.get("location") or {}).get("Slum")
    if record.get("Voided"):
        reporting.skip(slum=slum, reason="voided")
        return False
    with reporting.record(slum=slum, key=record.get("ID")):
        try:
            save_mobilization(record)
            return True
        except Exception as exc:
            logger.error("Mobilization %s not saved: %s", record.get("ID"), exc)
            reporting.fail(exc)
            return False


def sync_mobilization(from_date=None, api=None):
    """Pull mobilization subjects modified since the window start (EPOCH = all dates)."""
    api = api or client()
    since = watermark.window_start(from_date=from_date)
    saved = 0
    for page in api.iter_pages(paths.subjects(SUBJECT_TYPE, since)):
        for record in page:
            saved += int(save_mobilization_record(record))
    return saved


def attendance_counts(observations):
    return {field: observations.get(question, 0) for field, question in ATTENDANCE_COUNTS.items()}


def save_activity_attendance(observations, slum_name, household_number):
    """Upsert one household's attendance from a Daily Mobilization Activity encounter."""
    slum_id, city_id = slum_and_city_ids(slum_name)
    activity = activity_key(observations["Type of Activity"])
    fields = dict(
        date_of_activity=dateparser.parse(observations["Date of the activity conducted"]).date(),
        activity_type_id=activity,
        household_number=household_number,
        **attendance_counts(observations)
    )
    rows = CommunityMobilizationActivityAttendance.objects.filter(
        slum=slum_id, city=city_id, household_number=household_number, activity_type_id=activity
    )
    if rows.exists():
        rows.update(**fields)
    else:
        CommunityMobilizationActivityAttendance.objects.create(slum_id=slum_id, city_id=city_id, **fields)
