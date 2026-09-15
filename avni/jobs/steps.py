"""One guarded step of a job: a crash inside it fails the step, not the run."""

import logging

logger = logging.getLogger(__name__)

SYNC_LOGGERS = [
    "avni.sync.households", "avni.sync.encounters", "avni.sync.program_encounters",
    "avni.sync.mobilization", "avni.sync.rim", "avni.sync.file_imports", "avni.sync.members",
]


def run_step(recorder, name, sync, **kwargs):
    """Run `sync(**kwargs)` as a recorded step; returns its result or None when it failed."""
    with recorder.step(name, loggers=SYNC_LOGGERS) as step:
        if step.disabled:
            return None
        try:
            return sync(**kwargs)
        except Exception as exc:
            logger.exception("Step %s stopped: %s", name, exc)
            step.note_error("{}: {}".format(type(exc).__name__, exc))
            return None
