"""Nightly refresh of the cached AVNI form definitions (deploy/AVNI_FORM_CACHE_REFRESH.sh)."""

from avni import metadata
from notification.services import reporting


def run(recorder, params=None):
    recorder.set_window("all forms")
    with recorder.step("form_cache_refresh", loggers=["avni.metadata"]) as step:
        if step.disabled:
            return
        counts = metadata.refresh_form_cache()
        reporting.note(**counts)
        step.expect(counts["forms"])
        for _ in range(counts["forms"] - counts["export_errors"]):
            with reporting.record():
                pass
