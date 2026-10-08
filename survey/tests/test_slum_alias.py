"""SlumAlias: constraints, the generic lookups, and the load_slum_locations command."""

import json
import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from survey import locations
from survey.models import SlumAlias
from survey.tests.support import make_city, make_slum

UUID = "105ecc66-688b-42c5-82fa-adc65b4a2616"


class SlumAliasTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.alias = SlumAlias.objects.create(slum=self.slum, provider="avni", external_id=UUID)

    def test_one_alias_per_slum_per_provider(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="other")

    def test_one_slum_per_external_id_per_provider(self):
        other = make_slum(self.city, name="Other", code="OT1")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            SlumAlias.objects.create(slum=other, provider="avni", external_id=UUID)
        SlumAlias.objects.create(slum=other, provider="kobo", external_id=UUID)

    def test_lookups(self):
        self.assertEqual(locations.slum_external_id("avni", self.slum.id), UUID)
        self.assertIsNone(locations.slum_external_id("kobo", self.slum.id))
        self.assertEqual(locations.slum_ids_for("avni"), [self.slum.id])
        self.assertEqual(locations.slum_ids_for("kobo"), [])
        self.assertEqual(locations.slum_id_for_external_id("avni", UUID), self.slum.id)
        self.assertIsNone(locations.slum_id_for_external_id("kobo", UUID))
        self.assertIsNone(locations.slum_id_for_external_id("avni", ""))
        self.assertIsNone(locations.slum_id_for_external_id("avni", None))


class LoadSlumLocationsTests(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city())
        self.path = os.path.join(tempfile.mkdtemp(), "uuids.json")

    def load(self, uuids):
        with open(self.path, "w") as handle:
            json.dump(uuids, handle)
        out = StringIO()
        call_command("load_slum_locations", "--file", self.path, stdout=out)
        return out.getvalue()

    def test_creates_known_and_skips_unknown_slums(self):
        out = self.load({str(self.slum.id): UUID, str(self.slum.id + 1000): "orphan"})
        self.assertIn("1 created, 0 already mapped, 0 locked, 1 unknown", out)
        self.assertIn("slum {} does not exist".format(self.slum.id + 1000), out)
        self.assertEqual(locations.slum_external_id("avni", self.slum.id), UUID)
        self.assertTrue(SlumAlias.objects.get(slum=self.slum).is_primary)

    def test_a_rerun_never_repoints_an_existing_mapping(self):
        """A slum may have several locations, and a hand-made mapping must stand."""
        self.load({str(self.slum.id): UUID})
        out = self.load({str(self.slum.id): "new-uuid"})
        self.assertIn("1 created", out)
        self.assertEqual(
            sorted(SlumAlias.objects.filter(slum=self.slum).values_list("external_id", flat=True)),
            sorted([UUID, "new-uuid"]),
        )
        self.assertEqual(locations.slum_external_id("avni", self.slum.id), UUID, "the primary is untouched")

    def test_the_same_uuid_twice_is_left_alone(self):
        self.load({str(self.slum.id): UUID})
        out = self.load({str(self.slum.id): UUID})
        self.assertIn("0 created, 1 already mapped", out)
        self.assertEqual(SlumAlias.objects.count(), 1)

    def test_a_locked_slum_is_left_alone(self):
        from survey import slum_sync

        slum_sync.update(self.slum.id, alias_locked=True)
        out = self.load({str(self.slum.id): UUID})
        self.assertIn("0 created, 0 already mapped, 1 locked", out)
        self.assertIn("locations are locked", out)
        self.assertFalse(SlumAlias.objects.exists())

    def test_a_uuid_held_by_another_slum_is_reported_not_moved(self):
        other = make_slum(make_city("Pune"), name="Other", code="OT9")
        SlumAlias.objects.create(slum=other, provider="avni", external_id=UUID)
        out = self.load({str(self.slum.id): UUID})
        self.assertIn("uuid {} is mapped to slum {}".format(UUID, other.id), out)
        self.assertEqual(SlumAlias.objects.get(external_id=UUID).slum_id, other.id)
