"""Records a completed run for a job that is not Python (e.g. a bash script).

    manage.py report_external_job cleanup_generated_files --exit-code 0 \\
        --started-on 2026-09-11T05:00:00 --metric dirs_removed=3 --log-tail-file x.log
"""

import os
import socket

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from notification.models import JobDefinition, JobRun, JobStep
from notification.services import email as job_email

TAIL_BYTES = 4000


class Command(BaseCommand):
    help = "Record a finished run for an external (non-Python) job."

    def add_arguments(self, parser):
        parser.add_argument("key")
        parser.add_argument("--exit-code", type=int, default=0)
        parser.add_argument("--started-on", default=None, help="ISO datetime")
        parser.add_argument("--metric", action="append", default=[], help="name=value")
        parser.add_argument("--log-tail-file", default=None)
        parser.add_argument("--trigger", default="cron", choices=("cron", "manual", "chained"))
        parser.add_argument("--no-email", action="store_true")

    def handle(self, *args, **options):
        key = options["key"]
        definition = JobDefinition.objects.filter(key=key).first()
        if definition is None:
            definition = JobDefinition.objects.create(
                key=key, display_name=key.replace("_", " ").title(),
                runner="external", is_active=False,
            )

        started = _parse(options["started_on"]) or timezone.now()
        failed = options["exit_code"] != 0
        tail = _tail(options["log_tail_file"])
        metrics = dict(m.split("=", 1) for m in options["metric"] if "=" in m)

        run = JobRun.objects.create(
            job=definition, job_key=key, trigger=options["trigger"],
            hostname=socket.gethostname()[:200], pid=os.getppid(),
            started_on=started, finished_on=timezone.now(),
            status="failed" if failed else "success",
            error=("exit code {}\n\n{}".format(options["exit_code"], tail)) if failed else None,
        )
        JobStep.objects.create(
            run=run, name=key, order=0, started_on=started,
            finished_on=run.finished_on, status=run.status,
            extras=metrics or None, error=run.error,
        )
        self.stdout.write("RUN_ID={} {}".format(run.pk, run.status))
        if failed and not options["no_email"]:
            job_email.send_failure_alert(run)


def _parse(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is not None and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def _tail(path):
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as handle:
        handle.seek(max(os.path.getsize(path) - TAIL_BYTES, 0))
        return handle.read().decode("utf-8", "replace")
