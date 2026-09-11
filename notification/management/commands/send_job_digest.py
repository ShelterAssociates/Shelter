"""Sends the daily job digest: what ran, what failed, what never started."""

import traceback
from datetime import datetime, time as dt_time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from notification.models import DAY_KEYS, JobDefinition, JobRun
from notification.services import email as job_email

SLOT_EARLY_TOLERANCE = timedelta(minutes=5)


class Command(BaseCommand):
    help = "Email the scheduled-job digest for the last window."

    def add_arguments(self, parser):
        parser.add_argument("--since", default=None, help="ISO datetime, for backfill")
        parser.add_argument("--until", default=None, help="ISO datetime, for backfill")
        parser.add_argument("--no-email", action="store_true")

    def handle(self, *args, **options):
        until = _parse(options["until"]) or timezone.now()
        explicit_since = _parse(options["since"])

        swept = self.sweep_stuck(until)
        if swept:
            self.stdout.write("Marked {} stuck run(s) crashed".format(swept))

        definitions = JobDefinition.objects.filter(
            is_active=True, include_in_digest=True
        )
        missed = []
        for definition in definitions:
            since = explicit_since or definition.last_digest_checked_at or (
                until - timedelta(hours=24)
            )
            missed.extend(self.missed_slots(definition, since, until))

        if explicit_since:
            runs = JobRun.objects.filter(
                started_on__gte=explicit_since, started_on__lte=until
            )
        else:
            runs = JobRun.objects.filter(
                included_in_digest_at__isnull=True, started_on__lte=until
            )
        runs = list(runs.select_related("job").prefetch_related("steps").order_by("started_on"))

        self.stdout.write(
            "{} run(s), {} missed slot(s)".format(len(runs), len(missed))
        )
        if options["no_email"]:
            for item in missed:
                self.stdout.write("  MISSED {} at {}".format(item["name"], item["expected_at"]))
            for run in runs:
                self.stdout.write("  {} {}".format(run.job_key, run.status))
            return

        since = explicit_since or (until - timedelta(hours=24))
        try:
            message_id = job_email.send_digest(runs, missed, since, until)
        except Exception:
            self.stderr.write("Digest failed to send:\n" + traceback.format_exc())
            return

        if not message_id:
            self.stderr.write("Digest was not sent; recipients or SMTP unavailable.")
            return

        if not explicit_since:
            stamp = timezone.now()
            JobRun.objects.filter(pk__in=[r.pk for r in runs]).update(
                included_in_digest_at=stamp
            )
            definitions.update(last_digest_checked_at=until)
            self.record_own_run(until, stamp)
        self.stdout.write(self.style.SUCCESS("Digest sent."))

    def record_own_run(self, started, finished):
        """So the next digest can tell this one ran. Pre-marked as digested."""
        definition = JobDefinition.objects.filter(key="job_digest").first()
        JobRun.objects.create(
            job=definition, job_key="job_digest", status="success",
            started_on=started, finished_on=finished,
            included_in_digest_at=finished,
        )

    def sweep_stuck(self, until):
        """Close runs that are still 'running' past their job's max runtime."""
        count = 0
        for run in JobRun.objects.filter(status="running").select_related("job"):
            limit = run.job.max_runtime_minutes if run.job else 360
            if run.started_on < until - timedelta(minutes=limit):
                run.status = "crashed"
                run.finished_on = timezone.now()
                run.error = (run.error or "") + "\nStill running after {} minutes.".format(limit)
                run.save(update_fields=["status", "finished_on", "error"])
                count += 1
        return count

    def missed_slots(self, definition, since, until):
        """Expected start times in the window with no run anywhere near them."""
        times = definition.expected_time_list()
        if not times:
            return []
        days = definition.expected_day_set()
        month_days = definition.expected_month_day_set()
        grace = timedelta(minutes=definition.grace_minutes)
        now = timezone.now()

        results = []
        cursor = timezone.localtime(since).date()
        last = timezone.localtime(until).date()
        while cursor <= last:
            on_month_day = not month_days or cursor.day in month_days
            if on_month_day and DAY_KEYS[cursor.weekday()] in days:
                for hour, minute in times:
                    slot = timezone.make_aware(
                        datetime.combine(cursor, dt_time(hour, minute))
                    )
                    if slot < since or slot > until or slot + grace > now:
                        continue
                    seen = JobRun.objects.filter(
                        job_key=definition.key,
                        started_on__gte=slot - SLOT_EARLY_TOLERANCE,
                        started_on__lte=slot + grace,
                    ).exists()
                    if not seen:
                        results.append(
                            {"name": definition.display_name, "expected_at": slot}
                        )
            cursor += timedelta(days=1)
        return results


def _parse(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed
