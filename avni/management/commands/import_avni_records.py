"""Load a JSON-lines bundle through the normal sync with no AVNI calls (avni.bundle.load)."""

import datetime

from django.core.management.base import BaseCommand

from avni import bundle


class Command(BaseCommand):
    help = "Load an AVNI bundle offline: prints the result per record; --apply writes it."

    def add_arguments(self, parser):
        parser.add_argument("bundle", help="JSON-lines file made by export_avni_records.")
        parser.add_argument("--apply", action="store_true", help="Write the changes (default is a dry run).")
        parser.add_argument("--report", help="Where to write the CSV report (default: a dated file here).")

    def handle(self, *args, **options):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle.load(options["bundle"], apply=options["apply"], out=self.stdout.write,
                    report=options["report"] or "avni_bundle_load_{}.csv".format(stamp))
