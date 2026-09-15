"""The nightly AVNI sync (deploy/AVNI_DAILY_SYNC.sh)."""

import time

from avni import watermark
from avni.jobs.steps import run_step
from avni.sync import households, mobilization, program_encounters

# (step name, function, kwargs)
STEPS = (
    ("households:Household", households.sync_households, {"subject_type": "Household"}),
    ("daily_reporting", program_encounters.sync_daily_reporting, {}),
    ("family_factsheets", program_encounters.sync_family_factsheets, {}),
    ("mobilization", mobilization.sync_mobilization, {}),
)


def run(recorder, params=None):
    from_date = (params or {}).get("from_date")
    recorder.set_window("modified since {}".format(watermark.window_start(from_date=from_date)))
    for index, (name, sync, kwargs) in enumerate(STEPS):
        if index:
            time.sleep(1)
        run_step(recorder, name, sync, from_date=from_date, **kwargs)
