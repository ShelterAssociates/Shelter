"""Retry a stopped run from where it stopped.

Every listing step notes `checkpoint` (the last-modified stamp of the last
record it processed) and `processed`; subject_sync notes `processed` and keeps
the failed keys in the step's failure sample. A job queued with
params["resume_run"] = <JobRun id> skips the steps that finished successfully
in that run and starts every other step from its checkpoint.
"""

from collections import namedtuple

from notification.models import JobRun
from notification.services import reporting

PARAM = "resume_run"
RESUMABLE_STATUSES = ("failed", "partial", "crashed")

Resume = namedtuple("Resume", "run steps")


def from_params(params):
    """Resume for params[PARAM], or None. An unknown run id is a ValueError."""
    run_id = (params or {}).get(PARAM)
    if not run_id:
        return None
    run = JobRun.objects.filter(pk=run_id).first()
    if run is None:
        raise ValueError("resume_run {} is not a known run".format(run_id))
    return Resume(run, {step.name: step for step in run.steps.all()})


def previous_step(resume, name):
    return resume.steps.get(name) if resume else None


def already_done(resume, name):
    step = previous_step(resume, name)
    return step is not None and step.status == "success"


def checkpoint(resume, name):
    step = previous_step(resume, name)
    return (step.extras or {}).get("checkpoint") if step else None


def processed(resume, name):
    step = previous_step(resume, name)
    try:
        return int((step.extras or {}).get("processed", 0)) if step else 0
    except (TypeError, ValueError):
        return 0


def failed_keys(resume, name):
    step = previous_step(resume, name)
    if step is None:
        return []
    return [entry.get("key") for entry in step.sample_failures or [] if entry.get("key")]


def note_skipped(resume):
    reporting.note(resumed="already done in run #{}".format(resume.run.pk))


def can_resume(run, job_key=None):
    return run is not None and run.status in RESUMABLE_STATUSES and (job_key or run.job_key) in RESUMABLE_JOBS


# Jobs whose steps understand a checkpoint (the listing syncs) or a processed
# count (subject_sync). rim_sync re-reads whole slums, file_import whole files.
RESUMABLE_JOBS = (
    "avni_daily_sync", "rhs_sync", "mobilization_sync", "family_factsheet_sync", "daily_reporting_sync",
    "encounter_sync", "household_encounter_sync", "member_sync", "subject_sync",
)
