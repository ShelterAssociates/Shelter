"""The jobs the console offers and how their form fields become job params."""

import json
from collections import namedtuple

from avni.jobs.manual_sync import HOUSEHOLD_SUBJECT_TYPES
from avni.sync.encounters import DIRECT_ENCOUNTER_TYPES  # noqa: F401 (re-exported for views)

Job = namedtuple("Job", "key title description fields dry_run scheduled")

JOBS = [
    Job("rhs_sync", "RHS registration (Household / Structure)",
        "Pull household and structure registrations modified since a date into the mastersheet. "
        "Dry run tells you how many records AVNI would send.",
        ["from_date", "subject_types"], True, False),
    Job("daily_reporting_sync", "Daily Reporting (toilet construction)",
        "Program encounters that drive ToiletConstruction dates and status.", ["from_date"], False, False),
    Job("family_factsheet_sync", "Family factsheet", "Factsheet program encounters into ff_data.", ["from_date"], False, False),
    Job("mobilization_sync", "Community mobilization",
        "Mobilization activity subjects into the mastersheet. 'All dates' re-reads every record AVNI has.",
        ["from_date", "all_dates"], False, False),
    Job("encounter_sync", "Direct encounters (Sanitation, Water, Waste, Property tax, Electricity)",
        "Household-level follow-up encounters merged into rhs_data.", ["from_date", "encounter_types"], False, False),
    Job("rim_sync", "RIM and community toilet blocks (slum level)",
        "Slum-RIM registration and Toilet subjects for the chosen slums (all dates).", ["slum_ids", "include_toilets"], False, False),
    Job("dashboard_update", "Dashboard refresh",
        "Rebuilds the dashboard aggregates for the chosen cities. Heavy: it runs only in the night slot.",
        ["city_ids"], False, True),
    Job("avni_form_cache_refresh", "Refresh AVNI form cache",
        "Re-reads every AVNI form so bulk uploads validate against today's questions. Also runs nightly.", [], False, False),
]
BY_KEY = {job.key: job for job in JOBS}


class ParamError(ValueError):
    pass


def build_params(job_key, data):
    """Validated job params from a request payload; raises ParamError with a user-facing message."""
    job = BY_KEY.get(job_key)
    if job is None:
        raise ParamError("Unknown job.")
    params = {}
    for field in job.fields:
        BUILDERS[field](params, data)
    return params


def from_date(params, data):
    value = (data.get("from_date") or "").strip()
    if value:
        parse_iso_date(value)
        params["from_date"] = value


def parse_iso_date(value):
    from datetime import datetime

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ParamError("From date must be YYYY-MM-DD.")


def subject_types(params, data):
    chosen = as_list(data.get("subject_types"))
    unknown = [kind for kind in chosen if kind not in HOUSEHOLD_SUBJECT_TYPES]
    if unknown:
        raise ParamError("Unknown subject type(s): {}".format(", ".join(unknown)))
    if not chosen:
        raise ParamError("Pick at least one subject type.")
    params["subject_types"] = chosen


def all_dates(params, data):
    if truthy(data.get("all_dates")):
        params["all_dates"] = True
        params.pop("from_date", None)


def encounter_types(params, data):
    chosen = as_list(data.get("encounter_types"))
    unknown = [kind for kind in chosen if kind not in DIRECT_ENCOUNTER_TYPES]
    if unknown:
        raise ParamError("Unknown encounter type(s): {}".format(", ".join(unknown)))
    if chosen:
        params["encounter_types"] = chosen


def slum_ids(params, data):
    chosen = as_int_list(data.get("slum_ids"), "Slum")
    if chosen:
        params["slum_ids"] = chosen


def include_toilets(params, data):
    params["include_toilets"] = truthy(data.get("include_toilets", True))


def city_ids(params, data):
    chosen = as_int_list(data.get("city_ids"), "City")
    if not chosen:
        raise ParamError("Pick at least one city.")
    params["city_ids"] = chosen


BUILDERS = {
    "from_date": from_date, "subject_types": subject_types, "all_dates": all_dates,
    "encounter_types": encounter_types, "slum_ids": slum_ids, "include_toilets": include_toilets,
    "city_ids": city_ids,
}


def as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.startswith("["):
        return as_list(json.loads(value))
    return [part.strip() for part in str(value).split(",") if part.strip()]


def as_int_list(value, label):
    try:
        return [int(item) for item in as_list(value)]
    except ValueError:
        raise ParamError("{} ids must be numbers.".format(label))


def truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in ("1", "true", "yes", "on")


def describe(job_key, params):
    """Human-readable params for emails and the runs page."""
    params = params or {}
    parts = []
    labels = {
        "from_date": "from {}", "subject_types": "types: {}", "all_dates": "all dates", "encounter_types": "types: {}",
        "slum_ids": "{} slum(s)", "include_toilets": "with toilets", "city_ids": "{} city/cities",
        "dry_run": "DRY RUN", "bulk_update_id": "upload #{}", "kind": "{}", "path": "{}",
    }
    for key, value in params.items():
        label = labels.get(key)
        if label is None or value in (False, None, ""):
            continue
        if isinstance(value, list):
            value = len(value) if key in ("slum_ids", "city_ids") else ", ".join(str(v) for v in value)
        parts.append(label.format(value) if "{}" in label else label)
    return "; ".join(parts)
