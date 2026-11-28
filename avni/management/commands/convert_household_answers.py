"""Convert stored household answers to the map filters' answers (avni.mappings.convert_answers). Offline."""

from collections import Counter

from django.core.management.base import BaseCommand

from avni import mappings
from graphs.models import HouseholdData


class Command(BaseCommand):
    help = "Apply avni.mappings.convert_answers to every stored household; dry run unless --apply."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the changes (default is a dry run).")

    def handle(self, *args, **options):
        changed, keys = 0, Counter()
        for row in HouseholdData.objects.exclude(rhs_data__isnull=True).only("id", "rhs_data").iterator():
            before = row.rhs_data or {}
            after = mappings.convert_answers(dict(before))
            moved = [key for key in after if after.get(key) != before.get(key)]
            if not moved:
                continue
            changed += 1
            keys.update(moved)
            if options["apply"]:
                HouseholdData.objects.filter(id=row.id).update(rhs_data=after)
        self.stdout.write("{} household(s) {}.".format(changed, "converted" if options["apply"] else "to convert (dry run)"))
        for key, count in keys.most_common():
            self.stdout.write("  {}: {}".format(key, count))
