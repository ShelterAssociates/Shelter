"""Run queued photo exports. Invoked by cron via deploy/PHOTO_EXPORT_RUNNER.sh.

Processes one job per invocation so a long export can never block the next
cron tick from sweeping orphans, and so a crash affects exactly one job.
"""

import logging

from django.core.management.base import BaseCommand

from photos.services import runner

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Build any queued photo exports and email the result."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-jobs",
            type=int,
            default=1,
            help="How many queued jobs to run in this invocation (default 1).",
        )
        parser.add_argument(
            "--skip-orphan-sweep",
            action="store_true",
            help="Don't fail jobs left running by a restart.",
        )

    def handle(self, *args, **options):
        if not options["skip_orphan_sweep"]:
            swept = runner.sweep_orphans()
            if swept:
                self.stdout.write("Marked {} orphaned export(s) failed".format(swept))

        ran = 0
        for _ in range(max(1, options["max_jobs"])):
            job = runner.claim_next_job()
            if job is None:
                break
            self.stdout.write("Running export #{} ({})".format(job.pk, job.scope))
            runner.run_job(job)
            job.refresh_from_db()
            self.stdout.write("  -> {}".format(job.status))
            ran += 1

        if not ran:
            self.stdout.write("No queued photo exports.")
