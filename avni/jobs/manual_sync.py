"""Syncs started from the AVNI console or the shell, one registry job each.

Every job takes (recorder, params); params is the JSON the console or
`run_job --params` supplied. A subject type or encounter type whose switch is
off (Admin -> Survey -> Sync switches) is refused with a ValueError.
"""

from avni import window
from avni.jobs import resume as resuming
from avni.jobs.steps import run_step
from avni.locations import mapped_slum_ids
from avni.sync import encounters, file_imports, households, members, mobilization, program_encounters, rim, structures
from notification.services import reporting
from survey import connector, switches

HOUSEHOLD_SUBJECT_TYPES = ("Household", structures.STRUCTURE, structures.DSES)
MEMBER_SUBJECT_TYPE = "Family Member"
MEMBER_KINDS = ("subject", "enrolment", "program_encounter")
SWITCHED_OFF = "{} is switched off (Admin -> Survey -> Sync switches)"

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
    recorder.set_window(window.window_label(from_date))


def ensure_enabled(label, subject_type, kind, program="", encounter_type=""):
    if not switches.is_enabled(subject_type, kind, program, encounter_type):
        raise ValueError(SWITCHED_OFF.format(label))


def rhs_sync(recorder, params=None):
    from_date = setting(params, "from_date")
    subject_types = setting(params, "subject_types") or list(HOUSEHOLD_SUBJECT_TYPES)
    unknown = [kind for kind in subject_types if kind not in HOUSEHOLD_SUBJECT_TYPES]
    if unknown:
        raise ValueError("Unknown subject type(s): {}".format(", ".join(unknown)))
    for subject_type in subject_types:
        ensure_enabled(subject_type, subject_type, "subject")
    resume = resuming.from_params(params)
    set_since_window(recorder, from_date)
    for subject_type in subject_types:
        run_step(recorder, "households:{}".format(subject_type), households.sync_households,
                 resume=resume, subject_type=subject_type, from_date=from_date)


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
    ensure_enabled("Community mobilization", mobilization.SUBJECT_TYPE, "subject")
    from_date = window.EPOCH if setting(params, "all_dates") else setting(params, "from_date")
    set_since_window(recorder, from_date)
    run_step(recorder, "mobilization", mobilization.sync_mobilization,
             resume=resuming.from_params(params), from_date=from_date)


def family_factsheet_sync(recorder, params=None):
    ensure_enabled("Family factsheet", "Household", "program_encounter", "", program_encounters.FAMILY_FACTSHEET)
    from_date = setting(params, "from_date")
    set_since_window(recorder, from_date)
    run_step(recorder, "family_factsheets", program_encounters.sync_family_factsheets,
             resume=resuming.from_params(params), from_date=from_date)


def daily_reporting_sync(recorder, params=None):
    ensure_enabled("Daily Reporting", "Household", "program_encounter", "", program_encounters.DAILY_REPORTING)
    from_date = setting(params, "from_date")
    set_since_window(recorder, from_date)
    run_step(recorder, "daily_reporting", program_encounters.sync_daily_reporting,
             resume=resuming.from_params(params), from_date=from_date)


def encounter_sync(recorder, params=None):
    from_date = setting(params, "from_date")
    types = setting(params, "encounter_types") or encounters.DIRECT_ENCOUNTER_TYPES
    for encounter_type in types:
        ensure_enabled(encounter_type, "Household", "encounter", "", encounter_type)
    resume = resuming.from_params(params)
    set_since_window(recorder, from_date)
    for encounter_type in types:
        run_step(recorder, "encounters:{}".format(encounter_type), encounters.sync_encounters,
                 resume=resume, encounter_type=encounter_type, from_date=from_date)


def household_encounter_sync(recorder, params=None):
    """Every enabled enrolment / encounter / program encounter of the household subject types."""
    from_date = setting(params, "from_date")
    subject_types = setting(params, "subject_types") or list(HOUSEHOLD_SUBJECT_TYPES)
    unknown = [kind for kind in subject_types if kind not in HOUSEHOLD_SUBJECT_TYPES]
    if unknown:
        raise ValueError("Unknown subject type(s): {}".format(", ".join(unknown)))
    rows = connector.enabled_rows(subject_types, exclude=())
    wanted = setting(params, "encounter_types")
    if wanted:
        known = {row.encounter_type for row in rows if row.encounter_type}
        unknown = [name for name in wanted if name not in known]
        if unknown:
            raise ValueError("Unknown or switched-off encounter type(s): {}".format(", ".join(unknown)))
        rows = [row for row in rows if row.encounter_type in wanted]
    if not rows:
        raise ValueError("No enabled encounter kinds for {}. Refresh the AVNI form cache first.".format(", ".join(subject_types)))
    resume = resuming.from_params(params)
    set_since_window(recorder, from_date)
    context = connector.context_for()
    for row in rows:
        run_step(recorder, connector.step_name(row), sync_one_kind, resume=resume,
                 row=row, from_date=from_date, context=context)


def sync_one_kind(row, from_date, context):
    return connector.sync_kind(row.kind, row.subject_type, row.program, row.encounter_type, from_date, context)


def member_sync(recorder, params=None):
    """Family Member subjects, enrolments and program encounters."""
    ensure_enabled(MEMBER_SUBJECT_TYPE, MEMBER_SUBJECT_TYPE, "subject")
    from_date = setting(params, "from_date")
    set_since_window(recorder, from_date)
    run_step(recorder, "members", connector.sync_kinds, resume=resuming.from_params(params),
             subject_types=(MEMBER_SUBJECT_TYPE,), from_date=from_date, exclude=(), kinds=MEMBER_KINDS)


def subject_sync(recorder, params=None):
    """The explorer's button: registration plus everything under each listed subject."""
    subject_ids = unique_ids(setting(params, "subject_ids") or [])
    if not subject_ids:
        raise ValueError("subject_sync needs params subject_ids (a list of subject uuids)")
    resume = resuming.from_params(params)
    if resume is not None:
        subject_ids = remaining_subjects(subject_ids, resume)
        recorder.set_window("{} subject(s), resuming run #{}".format(len(subject_ids), resume.run.pk))
    else:
        recorder.set_window("{} subject(s)".format(len(subject_ids)))
    run_step(recorder, "subjects", sync_subjects, subject_ids=subject_ids)


def remaining_subjects(subject_ids, resume):
    """The ones the earlier run failed on, then the ones it never reached."""
    done = resuming.processed(resume, "subjects")
    return unique_ids(resuming.failed_keys(resume, "subjects") + subject_ids[done:])


def sync_subjects(subject_ids):
    reporting.expect(len(subject_ids))
    context = connector.context_for()
    totals = {}
    for index, subject_id in enumerate(subject_ids, 1):
        for kind, counts in connector.sync_subject(subject_id, context).items():
            bucket = totals.setdefault(kind, {})
            for name, count in counts.items():
                bucket[name] = bucket.get(name, 0) + count
        reporting.note(processed=index)
    reporting.note(**{kind: summarize(counts) for kind, counts in totals.items()})
    context.note()
    return sum(counts.get("legacy_saved", 0) for counts in totals.values())


def summarize(counts):
    return ", ".join("{} {}".format(name, count) for name, count in sorted(counts.items()))


def unique_ids(values):
    seen, ordered = set(), []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            ordered.append(text)
    return ordered


def file_import(recorder, params=None):
    kind = setting(params, "kind")
    path = setting(params, "path")
    if kind not in FILE_IMPORTS or not path:
        raise ValueError("file_import needs params kind (one of {}) and path".format(", ".join(sorted(FILE_IMPORTS))))
    recorder.set_window("{} from {}".format(kind, path))
    run_step(recorder, "import:{}".format(kind), FILE_IMPORTS[kind], file_path=path)
