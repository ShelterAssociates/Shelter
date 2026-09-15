"""Syncs started from the AVNI console or the shell, one registry job each.

Every job takes (recorder, params); params is the JSON the console or
`run_job --params` supplied.
"""

from avni import watermark
from avni.jobs.steps import run_step
from avni.locations import mapped_slum_ids
from avni.sync import encounters, file_imports, households, members, mobilization, program_encounters, rim

HOUSEHOLD_SUBJECT_TYPES = ("Household", "Structure")

FILE_IMPORTS = {
    "sanitation": file_imports.import_sanitation,
    "water": file_imports.import_water,
    "waste": file_imports.import_waste,
    "electricity": file_imports.import_electricity,
    "households": file_imports.import_households,
    "members": members.import_members,
    "member_programs": members.import_member_programs,
    "member_encounters": members.import_member_encounters,
}


def setting(params, key, default=None):
    return (params or {}).get(key, default)


def set_since_window(recorder, from_date):
    recorder.set_window("modified since {}".format(watermark.window_start(from_date=from_date)))


def rhs_sync(recorder, params=None):
    from_date = setting(params, "from_date")
    subject_types = setting(params, "subject_types") or list(HOUSEHOLD_SUBJECT_TYPES)
    unknown = [kind for kind in subject_types if kind not in HOUSEHOLD_SUBJECT_TYPES]
    if unknown:
        raise ValueError("Unknown subject type(s): {}".format(", ".join(unknown)))
    set_since_window(recorder, from_date)
    for subject_type in subject_types:
        run_step(recorder, "households:{}".format(subject_type), households.sync_households,
                 subject_type=subject_type, from_date=from_date)


def sync_slums(slum_ids, sync_one):
    for slum_id in slum_ids:
        sync_one(slum_id)


def rim_sync(recorder, params=None):
    slum_ids = setting(params, "slum_ids") or mapped_slum_ids()
    recorder.set_window("{} slum(s), all dates".format(len(slum_ids)))
    run_step(recorder, "rim", sync_slums, slum_ids=slum_ids, sync_one=rim.sync_slum_rim)
    if setting(params, "include_toilets", True):
        run_step(recorder, "toilets", sync_slums, slum_ids=slum_ids, sync_one=rim.sync_slum_toilets)


def mobilization_sync(recorder, params=None):
    from_date = watermark.EPOCH if setting(params, "all_dates") else setting(params, "from_date")
    set_since_window(recorder, from_date)
    run_step(recorder, "mobilization", mobilization.sync_mobilization, from_date=from_date)


def family_factsheet_sync(recorder, params=None):
    from_date = setting(params, "from_date")
    set_since_window(recorder, from_date)
    run_step(recorder, "family_factsheets", program_encounters.sync_family_factsheets, from_date=from_date)


def daily_reporting_sync(recorder, params=None):
    from_date = setting(params, "from_date")
    set_since_window(recorder, from_date)
    run_step(recorder, "daily_reporting", program_encounters.sync_daily_reporting, from_date=from_date)


def encounter_sync(recorder, params=None):
    from_date = setting(params, "from_date")
    types = setting(params, "encounter_types") or encounters.DIRECT_ENCOUNTER_TYPES
    set_since_window(recorder, from_date)
    for encounter_type in types:
        run_step(recorder, "encounters:{}".format(encounter_type), encounters.sync_encounters,
                 encounter_type=encounter_type, from_date=from_date)


def file_import(recorder, params=None):
    kind = setting(params, "kind")
    path = setting(params, "path")
    if kind not in FILE_IMPORTS or not path:
        raise ValueError("file_import needs params kind (one of {}) and path".format(", ".join(sorted(FILE_IMPORTS))))
    recorder.set_window("{} from {}".format(kind, path))
    run_step(recorder, "import:{}".format(kind), FILE_IMPORTS[kind], file_path=path)
