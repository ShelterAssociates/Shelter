"""Put household numbers back on members from an AVNI member export (avni.sync.member_backfill)."""

import datetime

from django.core.management.base import BaseCommand

from avni.sync import member_backfill


class Command(BaseCommand):
    help = ("Fill blank member household numbers from an AVNI member export (.xlsx or .csv). "
            "Prints the plan and writes a report; --apply writes the numbers; --restore REPORT undoes a run.")

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", help="The export file. Not needed with --restore.")
        parser.add_argument("--apply", action="store_true", help="Write the changes (default is a dry run).")
        parser.add_argument("--report", help="Where to write the CSV report (default: a dated file here).")
        parser.add_argument("--skip-city", action="append", dest="skip_cities",
                            help="A City value to leave out; repeat for more. Default: Test_city.")
        parser.add_argument("--restore", metavar="REPORT", help="Undo an applied run from its report.")

    def handle(self, *args, **options):
        if options["restore"]:
            member_backfill.restore(options["restore"], apply=options["apply"], out=self.stdout.write)
            return
        if not options["path"]:
            self.stderr.write("Give the export file, or --restore REPORT.")
            return
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        member_backfill.run(
            options["path"], apply=options["apply"], out=self.stdout.write,
            report=options["report"] or "member_household_backfill_{}.csv".format(stamp),
            skip_cities=options["skip_cities"] or member_backfill.SKIP_CITIES,
        )
