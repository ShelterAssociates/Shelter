"""Load the Slum id -> AVNI location uuid map into survey.SlumAlias."""

import json

from django.core.management.base import BaseCommand

from avni.locations import PROVIDER, data_file
from master.models import Slum
from survey.models import SlumAlias


class Command(BaseCommand):
    help = "Upsert survey.SlumAlias rows (provider avni) from slum_location_uuids.json. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=data_file("slum_location_uuids.json"), help="JSON of {slum id: uuid}.")

    def handle(self, *args, **options):
        with open(options["file"]) as handle:
            uuids = json.load(handle)
        known = set(Slum.objects.filter(id__in=[int(k) for k in uuids]).values_list("id", flat=True))
        created = updated = unknown = 0
        for slum_id, uuid in uuids.items():
            if int(slum_id) not in known:
                unknown += 1
                self.stdout.write("slum {} does not exist, skipped {}".format(slum_id, uuid))
                continue
            _, was_created = SlumAlias.objects.update_or_create(
                provider=PROVIDER, slum_id=int(slum_id), defaults={"external_id": uuid}
            )
            created += was_created
            updated += not was_created
        self.stdout.write("{} created, {} updated, {} unknown".format(created, updated, unknown))
