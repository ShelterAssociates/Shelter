"""Remove/rename HouseholdData ghosts left by renumbers, moves and voids in AVNI."""

from django.core.management.base import BaseCommand

from avni.sync import reconcile


class Command(BaseCommand):
    help = "Reconcile HouseholdData with AVNI: prints the plan, --apply runs it."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the changes (default is a dry run).")

    def handle(self, *args, **options):
        reconcile.run(apply=options["apply"], out=self.stdout.write)
