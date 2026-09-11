"""Runs a registered job, records what it did, and emails on failure."""

import signal
import traceback

from django.core.management.base import BaseCommand, CommandError

from notification.models import JobDefinition, JobRun
from notification.services import registry, reporting
from notification.services import email as job_email


class _Terminated(Exception):
    pass


class Command(BaseCommand):
    help = "Run a scheduled job and record the result."

    def add_arguments(self, parser):
        parser.add_argument("key", help="Job key, e.g. avni_daily_sync")
        parser.add_argument(
            "--trigger", default="cron", choices=("cron", "manual", "chained")
        )
        parser.add_argument("--parent-run", type=int, default=None)
        parser.add_argument(
            "--no-email", action="store_true", help="Record the run but send nothing."
        )

    def handle(self, *args, **options):
        key = options["key"]
        definition = JobDefinition.objects.filter(key=key).first()
        if definition is None:
            definition = JobDefinition.objects.create(
                key=key, display_name=key.replace("_", " ").title()
            )
            self.stderr.write(
                "No JobDefinition for '{}'; created one. "
                "Set its schedule in admin to get missed-run alerts.".format(key)
            )
        if not definition.is_active:
            self.stdout.write(
                "{} is switched off in admin (Job definitions); nothing run.".format(key)
            )
            return

        parent = None
        if options["parent_run"]:
            parent = JobRun.objects.filter(pk=options["parent_run"]).first()

        recorder = reporting.start(
            key, trigger=options["trigger"], definition=definition, parent_run=parent
        )
        self.stdout.write("RUN_ID={}".format(recorder.model.pk))

        previous = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, _raise_terminated)
        try:
            job = registry.resolve(key)
            job(recorder)
        except _Terminated:
            recorder.finish(status="crashed", error="Received SIGTERM")
            signal.signal(signal.SIGTERM, previous)
            raise CommandError("{} was terminated".format(key))
        except registry.JobUnavailable as exc:
            recorder.finish(status="failed", error=str(exc))
            signal.signal(signal.SIGTERM, previous)
            self._notify(recorder.model, options["no_email"])
            raise CommandError(str(exc))
        except BaseException:
            recorder.finish(status="crashed", error=traceback.format_exc())
            signal.signal(signal.SIGTERM, previous)
            self._notify(recorder.model, options["no_email"])
            raise
        else:
            run = recorder.finish()
            signal.signal(signal.SIGTERM, previous)
            self.stdout.write(
                "{}: {} - {} ok, {} failed, {} seen".format(
                    key, run.status, run.records_ok, run.records_failed,
                    run.records_total,
                )
            )
            if run.status in ("failed", "partial", "crashed"):
                self._notify(run, options["no_email"])

    def _notify(self, run, suppressed):
        if suppressed:
            self.stdout.write("Email suppressed by --no-email")
            return
        try:
            job_email.send_failure_alert(run)
        except Exception:
            self.stderr.write("Failure alert could not be sent:\n" + traceback.format_exc())


def _raise_terminated(signum, frame):
    raise _Terminated()
