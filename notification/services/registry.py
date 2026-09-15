"""Maps a job key to the callable that runs it.

Resolved lazily so a module missing on this host fails the run with a clear
message instead of breaking startup.
"""

import importlib

JOBS = {
    "avni_daily_sync": "avni.jobs.daily_sync:run",
    "rhs_sync": "avni.jobs.manual_sync:rhs_sync",
    "rim_sync": "avni.jobs.manual_sync:rim_sync",
    "mobilization_sync": "avni.jobs.manual_sync:mobilization_sync",
    "family_factsheet_sync": "avni.jobs.manual_sync:family_factsheet_sync",
    "daily_reporting_sync": "avni.jobs.manual_sync:daily_reporting_sync",
    "encounter_sync": "avni.jobs.manual_sync:encounter_sync",
    "file_import": "avni.jobs.manual_sync:file_import",
    "avni_form_cache_refresh": "avni.jobs.form_cache_refresh:run",
    "avni_bulk_update": "avni_console.services.bulk_update:run",
    "dashboard_update": "graphs.jobs.dashboard_update:run",
    "selftest": "notification.services.selftest:run",
}


class JobUnavailable(Exception):
    pass


def known_keys():
    return sorted(JOBS)


def resolve(key):
    target = JOBS.get(key)
    if target is None:
        raise JobUnavailable(
            "Unknown job '{}'. Known jobs: {}".format(key, ", ".join(known_keys()))
        )
    module_path, _, attribute = target.partition(":")
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise JobUnavailable("{} is not available on this host: {}".format(key, exc))
    try:
        return getattr(module, attribute)
    except AttributeError:
        raise JobUnavailable("{} has no {}()".format(module_path, attribute))
