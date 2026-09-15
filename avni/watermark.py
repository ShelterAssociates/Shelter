"""Which lastModifiedDateTime window a sync asks AVNI for.

Default: one day before the newest household we hold or the last successful run
of the same job, whichever is later, so a nightly run re-reads a little overlap
instead of risking a gap but does not keep re-reading the same records through
a quiet spell. Any job can pass an explicit from_date instead; EPOCH means
"everything".
"""

from datetime import date, datetime, timedelta

from django.utils import timezone

from notification.services import reporting

EPOCH = "2021-10-31T01:30:00.000Z"
DAY_START = "%Y-%m-%dT00:00:00.000Z"

# Structure registration is used in these cities; everything else is Household.
STRUCTURE_CITIES = ["Banthara Town", "Mohanlalganj City"]


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


def window_start(subject_type=None, from_date=None):
    """ISO start of the window; records the choice on the active job step."""
    if from_date:
        start = format_from_date(from_date)
    else:
        moments = [m for m in (latest_submission(subject_type), last_successful_run()) if m]
        start = day_before(max(moments) if moments else timezone.now())
    reporting.note(watermark=start)
    return start
