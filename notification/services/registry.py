"""Maps a job key to the callable that runs it.

Resolved lazily so a module missing on this host fails the run with a clear
message instead of breaking startup.
"""

import importlib

JOBS = {
    "avni_daily_sync": "graphs.jobs.avni_daily_sync:run",
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
