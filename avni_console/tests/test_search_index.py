"""The slum and location search indexes behind the console's pickers."""

from django.test import TestCase
from django.urls import reverse

from avni.tests.support import make_city, make_slum
from avni_console import catalog
from avni_console.tests.test_views import ConsoleTestCase
from survey.models import SlumAlias


class LocationSearchIndexTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_row_carries_the_uuid_and_the_full_path(self):
        SlumAlias.objects.create(
            slum=self.slum, provider="avni", external_id="loc-1", is_primary=True
        )
        row = catalog.location_search_index()[0]

        self.assertEqual(row["id"], "loc-1")
        self.assertEqual(row["name"], self.slum.name)
        self.assertEqual(row["city"], "Thane")
        self.assertEqual(row["aw"], self.slum.electoral_ward.administrative_ward.name)
        self.assertEqual(row["ew"], self.slum.electoral_ward.name)

    def test_ids_are_exactly_what_the_validator_accepts(self):
        # The picker must not offer a location build_params would reject.
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="loc-1", is_primary=True)
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="loc-2", is_primary=False)

        self.assertEqual(
            {row["id"] for row in catalog.location_search_index()},
            {uuid for uuid, _ in catalog.location_choices()},
        )

    def test_only_the_second_location_is_tagged(self):
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="loc-1", is_primary=True)
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="loc-2", is_primary=False)
        rows = {row["id"]: row for row in catalog.location_search_index()}

        self.assertNotIn("tag", rows["loc-1"])
        self.assertEqual(rows["loc-2"]["tag"], "second location")

    def test_other_providers_are_left_out(self):
        SlumAlias.objects.create(slum=self.slum, provider="kobo", external_id="k-1", is_primary=True)
        self.assertEqual(catalog.location_search_index(), [])


class SlumSearchIndexTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_mapped_slum_is_listed_with_its_path(self):
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="loc-1", is_primary=True)
        rows = catalog.slum_search_index()

        self.assertEqual([row["id"] for row in rows], [self.slum.id])
        self.assertEqual(rows[0]["name"], self.slum.name)
        self.assertEqual(rows[0]["city"], "Thane")

    def test_unmapped_slum_is_left_out(self):
        self.assertEqual(catalog.slum_search_index(), [])

    def test_a_slum_with_no_ward_chain_is_still_listed(self):
        # It is mapped, so it is syncable; the old multi-select listed it and
        # the picker must too. Its path parts come back empty, not missing.
        orphan = make_slum(self.city, name="No Ward", code="NW1")
        orphan.electoral_ward = None
        orphan.save()
        SlumAlias.objects.create(slum=orphan, provider="avni", external_id="loc-9", is_primary=True)

        row = {r["id"]: r for r in catalog.slum_search_index()}[orphan.id]
        self.assertEqual(row["name"], "No Ward")
        self.assertEqual((row["city"], row["aw"], row["ew"]), ("", "", ""))


class ConsolePickerPageTests(ConsoleTestCase):
    """The page ships the indexes and the pickers, not thousands of options."""

    def setUp(self):
        super().setUp()
        SlumAlias.objects.create(
            slum=self.slum, provider="avni", external_id="loc-1", is_primary=True
        )
        self.client.force_login(self.sync_user)

    def test_page_carries_both_indexes_and_no_option_tags(self):
        response = self.client.get(reverse("avni_console:index"))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="ac-locations-index"', html)
        self.assertIn('id="ac-slums-index"', html)
        self.assertIn('<select name="locations" multiple hidden>', html)
        self.assertIn('<select name="slum_ids" multiple hidden>', html)
        # The long lists are searched client-side now; nothing is pre-rendered.
        self.assertNotIn("<option", html)

    def test_counts_are_in_the_context(self):
        response = self.client.get(reverse("avni_console:index"))

        self.assertEqual(response.context["location_count"], 1)
        self.assertEqual(response.context["slum_count"], 1)
        self.assertEqual(
            [row["id"] for row in response.context["location_search_index"]], ["loc-1"]
        )
