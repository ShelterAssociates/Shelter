"""Flag visits entered twice across the whole survey store (offline; survey.duplicates)."""

from django.core.management.base import BaseCommand

from survey import duplicates


class Command(BaseCommand):
    help = "Scan stored AVNI encounters for one subject, type and day entered twice and flag them."

    def handle(self, *args, **options):
        self.stdout.write("{} duplicate visit group(s) flagged.".format(duplicates.flag_stored_encounters("avni")))
