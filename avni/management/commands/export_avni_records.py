"""Fetch AVNI records listed in a CSV into a JSON-lines bundle (avni.bundle.export). Needs AVNI."""

from django.core.management.base import BaseCommand

from avni import bundle


class Command(BaseCommand):
    help = "Fetch each (kind, uuid) row of IDS into BUNDLE, one JSON line per record; resumes if stopped."

    def add_arguments(self, parser):
        parser.add_argument("ids", help="CSV with columns kind (subject|enrolment|program_encounter) and uuid.")
        parser.add_argument("bundle", help="JSON-lines file to append to.")

    def handle(self, *args, **options):
        bundle.export(options["ids"], options["bundle"], out=self.stdout.write)
