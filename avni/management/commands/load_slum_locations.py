"""Load the Slum id -> AVNI location uuid map into survey.SlumAlias."""

import json

from django.core.management.base import BaseCommand

from avni.locations import PROVIDER, data_file
from master.models import Slum
from survey import slum_sync
from survey.models import SlumAlias


class Command(BaseCommand):
    """Keyed on the uuid, never on the slum: a slum may have several locations.

    A slum whose locations are locked is left alone, and an existing alias is
    never re-pointed, so a hand-made mapping survives a re-run.
    """

    help = "Add survey.SlumAlias rows (provider avni) from slum_location_uuids.json. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=data_file("slum_location_uuids.json"), help="JSON of {slum id: uuid}.")

    def handle(self, *args, **options):
        with open(options["file"]) as handle:
            uuids = json.load(handle)
        known = set(Slum.objects.filter(id__in=[int(k) for k in uuids]).values_list("id", flat=True))
        locked = slum_sync.locked_slum_ids()
        taken = dict(SlumAlias.objects.filter(provider=PROVIDER).values_list("external_id", "slum_id"))
        aliased = set(taken.values())
        created = held = skipped_locked = unknown = 0
        for slum_id, uuid in uuids.items():
            slum_id = int(slum_id)
            if slum_id not in known:
                unknown += 1
                self.stdout.write("slum {} does not exist, skipped {}".format(slum_id, uuid))
                continue
            if slum_id in locked:
                skipped_locked += 1
                self.stdout.write("slum {} locations are locked, left alone".format(slum_id))
                continue
            if uuid in taken:
                held += 1
                if taken[uuid] != slum_id:
                    self.stdout.write("uuid {} is mapped to slum {}, not {}".format(uuid, taken[uuid], slum_id))
                continue
            SlumAlias.objects.create(
                provider=PROVIDER, slum_id=slum_id, external_id=uuid, is_primary=slum_id not in aliased,
            )
            aliased.add(slum_id)
            taken[uuid] = slum_id
            created += 1
        self.stdout.write("{} created, {} already mapped, {} locked, {} unknown".format(
            created, held, skipped_locked, unknown,
        ))
