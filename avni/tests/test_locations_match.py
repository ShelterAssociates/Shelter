"""match_avni_locations: AVNI slum locations -> survey.SlumAlias by name + city."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from avni import paths
from avni.sync import locations
from avni.tests.support import FakeApi, make_city, make_slum
from survey.models import SlumAlias

LIST_PATH = paths.locations(locations.LOCATIONS_SINCE)


def location(uuid, title, type_name="Slum", parent=None, voided=False):
    row = {"ID": uuid, "Title": title, "Type": type_name, "Voided": voided}
    if parent:
        row["Parent"] = parent
    return row


def slum_location(uuid, title, city="Thane", voided=False):
    city_row = location("city-" + city, city, "City")
    ward = location("ward-1", "Ward 1", "Ward", parent=city_row)
    return location(uuid, title, parent=ward, voided=voided)


class MatchLocationsTests(TestCase):
    def setUp(self):
        self.thane = make_city("Thane")
        self.slum = make_slum(self.thane, "Lokmanya Nagar", "LN1")
        self.lines = []

    def api(self, *rows):
        return FakeApi({LIST_PATH: {"content": list(rows), "totalPages": 1}})

    def match(self, api, apply=False):
        return locations.run(apply=apply, api=api, out=self.lines.append)

    def test_exact_name_and_city_match_creates_alias_only_with_apply(self):
        api = self.api(slum_location("u-1", " lokmanya nagar "))
        counts = self.match(api)
        self.assertEqual(counts["to_create"], 1)
        self.assertEqual(SlumAlias.objects.count(), 0)
        self.match(api, apply=True)
        alias = SlumAlias.objects.get(slum=self.slum, provider="avni")
        self.assertEqual((alias.external_id, alias.external_name), ("u-1", " lokmanya nagar "))

    def test_same_name_in_another_city_is_not_matched(self):
        api = self.api(slum_location("u-1", "Lokmanya Nagar", city="Pune"))
        counts = self.match(api, apply=True)
        self.assertEqual((counts["to_create"], counts["unmatched_avni"], counts["unmatched_db"]), (0, 1, 1))
        self.assertIn("same name in DB under Thane", self.lines[0])
        self.assertEqual(SlumAlias.objects.count(), 0)

    def test_voided_cities_wards_and_already_aliased_are_skipped(self):
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="u-1")
        api = self.api(
            slum_location("u-1", "Lokmanya Nagar"),
            slum_location("u-2", "Gone", voided=True),
            location("city-Thane", "Thane", "City"),
        )
        counts = self.match(api, apply=True)
        self.assertEqual(sum(counts.values()), 0)
        self.assertEqual(SlumAlias.objects.count(), 1)

    def test_conflict_and_ambiguous_are_reported_not_written(self):
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="old-uuid")
        make_slum(self.thane, "Twin", "T1")
        make_slum(self.thane, "Twin", "T2")
        api = self.api(slum_location("new-uuid", "Lokmanya Nagar"), slum_location("u-3", "Twin"))
        counts = self.match(api, apply=True)
        self.assertEqual((counts["conflict"], counts["ambiguous"], counts["created"]), (1, 1, 0))
        self.assertEqual(SlumAlias.objects.count(), 1)

    def test_command_dry_run_by_default(self):
        out = StringIO()
        with self.settings(SURVEY_PROVIDER="avni.provider.AvniProvider"):
            from avni.client import reset_client, use_client
            use_client(self.api(slum_location("u-1", "Lokmanya Nagar")))
            try:
                call_command("match_avni_locations", stdout=out)
            finally:
                reset_client()
        self.assertIn("CREATE slum {} <- u-1".format(self.slum.id), out.getvalue())
        self.assertEqual(SlumAlias.objects.count(), 0)
