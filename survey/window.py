"""Which lastModifiedDateTime window a sync asks the provider for.

Default: one day before the newest record of that kind we hold or the last
successful run of the same job, whichever is later, so a nightly run re-reads a
little overlap instead of risking a gap but does not keep re-reading the same
records through a quiet spell. Household registrations read the mastersheet;
every other kind reads the survey store. A kind with nothing held yet starts
from FIRST_SYNC_START. Any job can pass an explicit from_date instead; EPOCH
means "everything".
"""

from datetime import date, datetime, timedelta


from notification.services import reporting

EPOCH = "2021-10-31T01:30:00.000Z"
FIRST_SYNC_START = "2018-01-01T00:00:00.000Z"
DAY_START = "%Y-%m-%dT00:00:00.000Z"

# Structure registration is used in these cities; everything else is Household.
STRUCTURE_CITIES = ["Banthara Town", "Mohanlalganj City"]
# Registrations the mastersheet (HouseholdData) holds; other subject types live only in the survey store.
HOUSEHOLD_SUBJECT_TYPES = ("Household", "Structure", "Detailed Socio Economic Survey")


def format_from_date(value):
    """Date, datetime or 'YYYY-MM-DD' -> AVNI ISO string; full ISO strings pass through."""
    if isinstance(value, str):
        if "T" in value:
            return value
        value = datetime.strptime(value[:10], "%Y-%m-%d")
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime(value.year, value.month, value.day)
    return value.strftime(DAY_START)


def day_before(moment):
    return (moment - timedelta(days=1)).strftime(DAY_START)


def latest_submission(subject_type=None):
    from graphs.models import HouseholdData

    households = HouseholdData.objects.order_by("-submission_date")
    if subject_type == "Structure":
        households = households.filter(city__name__city_name__in=STRUCTURE_CITIES)
    elif subject_type == "Household":
        households = households.exclude(city__name__city_name__in=STRUCTURE_CITIES)
    return households.values_list("submission_date", flat=True).first()


def latest_record(kind, subject_type="", program="", encounter_type=""):
    """last_modified_at of the newest survey record of this exact kind, or None."""
    from survey.models import Record

    rows = Record.objects.filter(kind=kind, program=program or "", encounter_type=encounter_type or "")
    if subject_type:
        rows = rows.filter(subject_type=subject_type)
    return rows.exclude(last_modified_at__isnull=True).order_by("-last_modified_at").values_list(
        "last_modified_at", flat=True
    ).first()


def latest_held(kind, subject_type="", program="", encounter_type=""):
    if kind == "subject" and (not subject_type or subject_type in HOUSEHOLD_SUBJECT_TYPES):
        return latest_submission(subject_type)
    return latest_record(kind, subject_type, program, encounter_type)


def last_successful_run():
    """started_on of the newest successful run of the job currently running, or None."""
    from notification.models import JobRun

    run = reporting.active_run()
    if run is None:
        return None
    return (
        JobRun.objects.filter(job_key=run.job_key, status="success")
        .order_by("-started_on")
        .values_list("started_on", flat=True)
        .first()
    )


def window_label(from_date=None):
    """The run's window label; without a from_date each step notes its own start."""
    if from_date:
        return "modified since {}".format(format_from_date(from_date))
    return "per-step window (see steps)"


def window_start(subject_type=None, from_date=None, kind="subject", program="", encounter_type=""):
    """ISO start of the window; records the choice on the active job step."""
    if from_date:
        start = format_from_date(from_date)
    else:
        held = latest_held(kind, subject_type, program, encounter_type)
        if held is None:
            start = FIRST_SYNC_START
        else:
            start = day_before(max(m for m in (held, last_successful_run()) if m))
    reporting.note(window_start=start)
    return start
