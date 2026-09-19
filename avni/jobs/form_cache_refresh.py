"""Nightly refresh of the cached AVNI form definitions (deploy/AVNI_FORM_CACHE_REFRESH.sh).

After the forms are cached, the survey concept dictionary claims a key for
every question and answer and the sync switches are brought in line with the
catalog. Run this before the first backfill so the clean keys win. The last
step aliases slums newly present in both AVNI and master.Slum (exact name +
city only) so a slum is map-enabled the night after it is created in both.
"""

from avni import metadata
from avni.jobs.steps import run_step
from avni.sync import locations
from notification.services import reporting
from survey import concepts, connector, switches


def sync_slum_locations():
    counts = locations.run(apply=True, out=locations.logger.info)
    reporting.note(**counts)
    return counts


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
    with recorder.step("survey_catalog", loggers=["survey.concepts", "survey.switches"]) as step:
        if step.disabled:
            return
        provider = connector.provider()
        if hasattr(provider, "reset_forms"):
            provider.reset_forms()
        catalog = provider.catalog()
        concept_counts = concepts.upsert_catalog(catalog, provider.key)
        switch_counts = switches.sync_catalog(provider)
        reporting.note(
            forms=concept_counts["forms"], questions=concept_counts["questions"], answers=concept_counts["answers"],
            switches_created=switch_counts["created"], switches_seen=switch_counts["seen"],
            switches_deactivated=switch_counts["deactivated"],
        )
        step.expect(len(catalog))
        for _ in catalog:
            with reporting.record():
                pass
    run_step(recorder, "slum_locations", sync_slum_locations)
