"""A record's slum comes from its AVNI Location ID (SlumAlias) before its slum name, since a few slum names
exist in two cities; and a household the survey store holds but the household table lacks is saved again."""

from django.test import TestCase

from avni.provider import AvniProvider
from avni.sync import households, members, structures
from avni.tests.support import FakeApi, make_city, make_slum, subject_record
from avni.tests.test_member_sync import member_record
from graphs.models import HouseholdData, MemberData
from survey import connector, locations
from survey.models import Record, SlumAlias
from survey.store import SyncContext


class LocationCase(TestCase):
    def setUp(self):
        self.panvel = make_slum(make_city("Panvel"), name="Ganesh Nagar", code="GN1")
        self.ichalkaranji = make_slum(make_city("Ichalkaranji"), name="Ganesh Nagar", code="GN2")
        SlumAlias.objects.create(slum=self.ichalkaranji, provider="avni", external_id="loc-ichal", external_name="")

    def record(self, uuid="hh-1", number="0042", subject_type="Household", **extra):
        record = subject_record(uuid=uuid, number=number, slum="Ganesh Nagar", city="Ichalkaranji",
                                subject_type=subject_type, **extra)
        record["Location ID"] = "loc-ichal"
        return record


class LookupTests(LocationCase):
    def test_location_id_wins_over_a_shared_name(self):
        self.assertEqual(locations.slum_and_city_ids("Ganesh Nagar", location_id="loc-ichal")[0], self.ichalkaranji.id)
        self.assertEqual(locations.slum_id_for_name("Ganesh Nagar", location_id="loc-ichal"), self.ichalkaranji.id)

    def test_unknown_location_id_falls_back_to_the_name(self):
        self.assertIsNotNone(locations.slum_and_city_ids("Ganesh Nagar", location_id="loc-unknown")[0])


class WritersTests(LocationCase):
    def test_household_lands_in_the_slum_of_its_location(self):
        households.save_household(self.record())
        self.assertEqual(HouseholdData.objects.get().slum_id, self.ichalkaranji.id)

    def test_detailed_survey_lands_in_the_slum_of_its_location(self):
        structures.save_structure_record(self.record(subject_type="Detailed Socio Economic Survey"))
        self.assertEqual(HouseholdData.objects.get().slum_id, self.ichalkaranji.id)

    def test_member_lands_in_the_slum_of_her_location(self):
        member = dict(member_record(groups=()), location={"Slum": "Ganesh Nagar", "City": "Ichalkaranji"})
        member["Location ID"] = "loc-ichal"
        members.save_member_from_record(member)
        self.assertEqual(MemberData.objects.get().slum_id, self.ichalkaranji.id)

    def test_misfiled_household_moves_to_its_location_slum(self):
        HouseholdData.objects.create(household_number="42", slum=self.panvel,
                                     city=self.panvel.electoral_ward.administrative_ward.city,
                                     submission_date="2026-01-01T00:00:00Z", rhs_data={"rhs_uuid": "hh-1"})
        households.save_household(self.record())
        self.assertEqual(list(HouseholdData.objects.values_list("slum_id", flat=True)), [self.ichalkaranji.id])


class StoreTests(LocationCase):
    def setUp(self):
        super().setUp()
        self.api = FakeApi()
        self.context = SyncContext(AvniProvider(api=self.api))

    def test_stored_record_takes_the_slum_of_its_location(self):
        connector.sync_record("subject", self.record(), self.context)
        self.assertEqual(Record.objects.get().slum_id, self.ichalkaranji.id)

    def test_household_missing_from_the_table_is_saved_again(self):
        connector.sync_record("subject", self.record(), self.context)
        HouseholdData.objects.all().delete()
        self.assertTrue(connector.sync_record("subject", self.record(), SyncContext(AvniProvider(api=self.api))))
        self.assertEqual(HouseholdData.objects.get().slum_id, self.ichalkaranji.id)
