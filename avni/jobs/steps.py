"""One guarded step of a job: a crash inside it fails the step, not the run."""

import logging

from avni.jobs import resume as resuming
from notification.services import reporting

logger = logging.getLogger(__name__)

SYNC_LOGGERS = [
    "avni.sync.households", "avni.sync.encounters", "avni.sync.program_encounters",
    "avni.sync.mobilization", "avni.sync.rim", "avni.sync.file_imports", "avni.sync.members",
    "avni.sync.structures", "avni.sync.locations", "avni.provider",
    "survey.connector", "survey.store", "survey.concepts", "survey.switches",
]


def run_step(recorder, name, sync, resume=None, **kwargs):
    """Run `sync(**kwargs)` as a recorded step; returns its result or None when it failed.

    With `resume` (avni.jobs.resume.Resume) a step that succeeded in the earlier
    run is skipped, and one that stopped starts from its checkpoint when the
    sync takes a from_date.
    """
    with recorder.step(name, loggers=SYNC_LOGGERS) as step:
        if step.disabled:
            return None
        if resume is not None:
            if resuming.already_done(resume, name):
                resuming.note_skipped(resume)
                return None
            checkpoint = resuming.checkpoint(resume, name)
            if checkpoint and "from_date" in kwargs:
                kwargs["from_date"] = checkpoint
                reporting.note(resumed_from=checkpoint)
        try:
            return sync(**kwargs)
        except Exception as exc:
            logger.exception("Step %s stopped: %s", name, exc)
            step.note_error("{}: {}".format(type(exc).__name__, exc))
            return None
