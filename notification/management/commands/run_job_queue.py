"""Cron entry point for the JobRequest queue (deploy/JOB_QUEUE_RUNNER.sh, every 2 minutes)."""

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from notification.services import queue


class Command(BaseCommand):
    help = "Run due job requests, oldest first."

    def add_arguments(self, parser):
        parser.add_argument("--max-jobs", type=int, default=1, help="Requests to run this tick (default 1).")
        parser.add_argument("--skip-orphan-sweep", action="store_true")

    def handle(self, *args, **options):
        if not options["skip_orphan_sweep"]:
            swept = queue.sweep_orphans()
            if swept:
                self.stdout.write("Marked {} orphaned request(s) failed".format(swept))

        for _ in range(max(options["max_jobs"], 0)):
            close_old_connections()
            request = queue.claim_next()
            if request is None:
                self.stdout.write("No due job requests.")
                return
            self.stdout.write("Running job request {} ({})".format(request.pk, request.job_key))
            queue.run(request)
            close_old_connections()
            self.stdout.write("Job request {}: {} - {}".format(request.pk, request.status, request.summary or request.error or ""))
