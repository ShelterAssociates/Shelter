"""The nightly AVNI sync (deploy/AVNI_DAILY_SYNC.sh).

Each step names its survey.switches switch (subject type, kind, program,
encounter type); a step whose switch is off is recorded as disabled, exactly
like a step disabled in the job's admin.
"""

import time

from avni import window
from avni.jobs import resume as resuming
from avni.jobs.steps import run_step
from avni.sync import households, mobilization, program_encounters, structures
from survey import connector, switches

MEMBER_SUBJECT_TYPE = "Family Member"
MEMBER_KINDS = ("subject", "enrolment", "program_encounter")


def sync_members(from_date=None):
    return connector.sync_kinds((MEMBER_SUBJECT_TYPE,), from_date=from_date, exclude=(), kinds=MEMBER_KINDS)


def sync_household_encounters(from_date=None):
    return connector.sync_kinds(connector.HOUSEHOLD_SUBJECT_TYPES, from_date=from_date)


# (step name, function, kwargs, switch spec or None)
STEPS = (
    ("households:Household", households.sync_households, {"subject_type": "Household"},
     ("Household", "subject", "", "")),
    ("households:Structure", households.sync_households, {"subject_type": structures.STRUCTURE},
     (structures.STRUCTURE, "subject", "", "")),
    ("households:Detailed Socio Economic Survey", households.sync_households, {"subject_type": structures.DSES},
     (structures.DSES, "subject", "", "")),
    ("daily_reporting", program_encounters.sync_daily_reporting, {},
     ("Household", "program_encounter", "", program_encounters.DAILY_REPORTING)),
    ("family_factsheets", program_encounters.sync_family_factsheets, {},
     ("Household", "program_encounter", "", program_encounters.FAMILY_FACTSHEET)),
    ("mobilization", mobilization.sync_mobilization, {},
     (mobilization.SUBJECT_TYPE, "subject", "", "")),
    ("household_encounters", sync_household_encounters, {}, None),
    ("members", sync_members, {}, (MEMBER_SUBJECT_TYPE, "subject", "", "")),
)


def switch_specs():
    return [(name, spec) for name, _, _, spec in STEPS]


def run(recorder, params=None):
    from_date = (params or {}).get("from_date")
    resume = resuming.from_params(params)
    recorder.set_window(window.window_label(from_date))
    recorder.disabled_steps |= switches.disabled_step_names(switch_specs())
    for index, (name, sync, kwargs, _) in enumerate(STEPS):
        if index:
            time.sleep(1)
        run_step(recorder, name, sync, resume=resume, from_date=from_date, **kwargs)
