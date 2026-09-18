"""Runs a registered job, records what it did, and reports it.

Cron runs mail only on failure (the nightly digest covers success). A manual
run from the shell is recorded as a JobRequest and mailed on every outcome, the
same activity report the console queue sends, so it is never silent.
"""

import json
import traceback

from django.core.management.base import BaseCommand, CommandError

from notification.models import JobRequest, JobRun
from notification.services import email as job_email
from notification.services import execute, queue


class Command(BaseCommand):
    help = "Run a scheduled job and record the result."

    def add_arguments(self, parser):
        parser.add_argument("key", help="Job key, e.g. avni_daily_sync")
        parser.add_argument("--trigger", default="cron", choices=("cron", "manual", "chained"))
        parser.add_argument("--parent-run", type=int, default=None)
        parser.add_argument("--no-email", action="store_true", help="Record the run but send nothing.")
        parser.add_argument(
            "--params", default=None,
            help='JSON object passed to the job, e.g. \'{"from_date": "2026-01-01"}\'',
        )

    def handle(self, *args, **options):
        key = options["key"]
        params = parse_params(options["params"])
        definition = execute.definition_for(key)
        if not definition.is_active:
            self.stdout.write("{} is switched off in admin (Job definitions); nothing run.".format(key))
            return

        parent = JobRun.objects.filter(pk=options["parent_run"]).first() if options["parent_run"] else None
        run = execute.execute(key, trigger=options["trigger"], params=params, parent=parent, definition=definition)

        self.stdout.write("RUN_ID={}".format(run.pk))
        self.stdout.write("{}: {} - {} ok, {} failed, {} seen".format(
            key, run.status, run.records_ok, run.records_failed, run.records_total
        ))
        if options["trigger"] == "manual":
            self.record_request(run, params, options["no_email"])
        elif run.status in ("failed", "partial", "crashed"):
            self.notify(run, options["no_email"])
        if run.status == "crashed":
            raise CommandError("{} crashed: {}".format(key, (run.error or "").strip().splitlines()[-1:] or ""))
        if run.status == "failed" and run.records_total == 0 and run.error:
            raise CommandError(run.error)

    def record_request(self, run, params, suppressed):
        """A shell run gets a JobRequest like a console run: listed in the console, mailed as it finishes."""
        request = JobRequest.objects.create(
            job_key=run.job_key, params=params or {}, requested_by=None, status="running",
            job_run=run, scheduled_for=run.started_on, created_on=run.started_on, started_on=run.started_on,
        )
        status = "done" if run.status in ("success", "partial") else "failed"
        queue.finish(request, status, summary=queue.summarize(run), error=run.error if status == "failed" else None)
        if suppressed:
            self.stdout.write("Email suppressed by --no-email")
            return
        queue.report(request)

    def notify(self, run, suppressed):
        if suppressed:
            self.stdout.write("Email suppressed by --no-email")
            return
        try:
            job_email.send_failure_alert(run)
        except Exception:
            self.stderr.write("Failure alert could not be sent:\n" + traceback.format_exc())


def parse_params(raw):
    if not raw:
        return None
    try:
        params = json.loads(raw)
    except ValueError as exc:
        raise CommandError("--params must be a JSON object: {}".format(exc))
    if not isinstance(params, dict):
        raise CommandError("--params must be a JSON object")
    return params
