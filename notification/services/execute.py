"""Run one registered job as a recorded JobRun. Shared by run_job and the queue runner."""

import signal
import traceback

from notification.models import JobDefinition
from notification.services import registry, reporting


class Terminated(Exception):
    pass


def raise_terminated(signum, frame):
    raise Terminated()


def definition_for(key):
    """The JobDefinition for a key, created (active) on first sight."""
    definition = JobDefinition.objects.filter(key=key).first()
    if definition is None:
        definition = JobDefinition.objects.create(
            key=key, display_name=key.replace("_", " ").title()
        )
    return definition


def execute(key, trigger="cron", params=None, parent=None, definition=None, handle_sigterm=True):
    """Run the job and return its finished JobRun. Never raises for job failures;
    the run's status/error carry them. SIGTERM (a deploy) closes the run as crashed."""
    definition = definition or definition_for(key)
    recorder = reporting.start(key, trigger=trigger, definition=definition, parent_run=parent)
    previous = signal.getsignal(signal.SIGTERM) if handle_sigterm else None
    if handle_sigterm:
        signal.signal(signal.SIGTERM, raise_terminated)
    try:
        job = registry.resolve(key)
        job(recorder, params)
    except Terminated:
        return recorder.finish(status="crashed", error="Received SIGTERM")
    except registry.JobUnavailable as exc:
        return recorder.finish(status="failed", error=str(exc))
    except BaseException:
        return recorder.finish(status="crashed", error=traceback.format_exc())
    else:
        return recorder.finish()
    finally:
        if handle_sigterm:
            signal.signal(signal.SIGTERM, previous)
