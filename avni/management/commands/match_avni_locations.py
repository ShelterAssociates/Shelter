"""Create survey.SlumAlias rows by matching AVNI slum locations to master.Slum by name + city."""

from django.core.management.base import BaseCommand

from avni.sync import locations


class Command(BaseCommand):
    help = "Match AVNI slum locations to Slums by name + city: prints the plan, --apply writes the aliases."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the aliases (default is a dry run).")

    def handle(self, *args, **options):
        locations.run(apply=options["apply"], out=self.stdout.write)
