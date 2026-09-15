"""Direct encounter sync: rhs_data merge, sanitation follow-up, failure handling."""

from django.test import TestCase

from avni import paths
from avni.client import AvniError
from avni.sync import encounters
from avni.tests.support import FakeApi, encounter_record, make_city, make_slum, page, subject_record
from graphs.models import FollowupData, HouseholdData
from notification.services import reporting

SINCE = "2026-01-01T00:00:00.000Z"


class EncounterPayloadTests(TestCase):
    def test_sanitation_keys_are_renamed_and_stamped(self):
        record = encounter_record(observations={"Status of toilet under SBM ?": "Done", "Other": "x"})
        data = encounters.encounter_payload(record)
        self.assertEqual(data["group_oi8ts04/Status_of_toilet_under_SBM"], "Done")
        self.assertEqual(data["submission_date"], record["audit"]["Last modified at"])
        self.assertEqual(data["Other"], "x")

    def test_water_and_waste_single_renames(self):
        water = encounters.encounter_payload(encounter_record(encounter_type="Water", observations={"Type of water connection ?": "Own"}))
        self.assertEqual(water["group_el9cl08/Type_of_water_connection"], "Own")
        self.assertIn("Last_modified_date", water)
        waste = encounters.encounter_payload(encounter_record(encounter_type="Waste", observations={"How do you dispose your solid waste ?": "Bin"}))
        self.assertEqual(waste["group_el9cl08/Facility_of_solid_waste_collection"], "Bin")

    def test_property_tax_and_electricity_pass_through(self):
        for kind in ("Property tax", "Electricity"):
            data = encounters.encounter_payload(encounter_record(encounter_type=kind, observations={"Q": 1}))
            self.assertEqual(data["Q"], 1)
            self.assertIn("Last_modified_date", data)


class EncounterSaveTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.api = FakeApi({paths.subject("sub-1"): subject_record()})

    def household(self):
        return HouseholdData.objects.get(household_number="42")

    def test_sanitation_creates_followup_and_merges_rhs(self):
        record = encounter_record(observations={"Do you have a toilet at home?": "Yes"})
        self.assertTrue(encounters.save_encounter(record, self.api))
        self.assertEqual(self.household().rhs_data["Do you have a toilet at home?"], "Yes")
        followup = FollowupData.objects.get(household_number="42")
        self.assertEqual(followup.followup_data["Do you have a toilet at home?"], "Yes")
        self.assertFalse(followup.flag_followup_in_rhs)

    def test_second_sanitation_updates_followup(self):
        encounters.save_encounter(encounter_record(observations={"A": 1}), self.api)
        encounters.save_encounter(encounter_record(uuid="enc-2", observations={"B": 2}), self.api)
        followup = FollowupData.objects.get(household_number="42")
        self.assertEqual(followup.followup_data["A"], 1)
        self.assertEqual(followup.followup_data["B"], 2)
        self.assertEqual(FollowupData.objects.count(), 1)

    def test_water_merges_into_existing_household_without_followup(self):
        HouseholdData.objects.create(household_number="42", slum=self.slum, city=self.city,
                                     submission_date="2020-01-01T00:00:00Z", rhs_data={"old": 1})
        encounters.save_encounter(encounter_record(encounter_type="Water", observations={"Type of water connection ?": "Own"}), self.api)
        row = self.household()
        self.assertEqual(row.rhs_data["old"], 1)
        self.assertEqual(row.rhs_data["group_el9cl08/Type_of_water_connection"], "Own")
        self.assertEqual(FollowupData.objects.count(), 0)

    def test_voided_or_empty_is_not_saved(self):
        self.assertFalse(encounters.save_encounter(encounter_record(voided=True), self.api))
        self.assertFalse(encounters.save_encounter(encounter_record(observations={}), self.api))
        self.assertEqual(HouseholdData.objects.count(), 0)

    def test_unknown_subject_raises_avni_error(self):
        with self.assertRaises(AvniError):
            encounters.save_encounter(encounter_record(subject_uuid="ghost"), self.api)


class EncounterSyncTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_sync_counts_ok_failed_skipped(self):
        records = [
            encounter_record("e1", subject_uuid="sub-1"),
            encounter_record("e2", subject_uuid="ghost"),
            encounter_record("e3", voided=True),
            encounter_record("e4", subject_uuid="sub-bad"),
        ]
        api = FakeApi({
            paths.encounters("Sanitation", SINCE): page(records),
            paths.subject("sub-1"): subject_record(),
            paths.subject("sub-bad"): subject_record("sub-bad", slum="Nowhere", number="7"),
        })
        recorder = reporting.start("encounter_sync", trigger="manual")
        with recorder.step("encounters:Sanitation"):
            saved = encounters.sync_encounters("Sanitation", from_date="2026-01-01", api=api)
        run = recorder.finish()
        step = run.steps.get()
        self.assertEqual(saved, 1)
        self.assertEqual((step.records_ok, step.records_failed, step.records_skipped), (1, 2, 1))
        self.assertIn("Nowhere", [f["slum"] for f in step.sample_failures])

    def test_sync_all_encounters_reports_each_type(self):
        api = FakeApi({paths.encounters(kind, SINCE): page([]) for kind in encounters.DIRECT_ENCOUNTER_TYPES})
        result = encounters.sync_all_encounters(from_date="2026-01-01", api=api)
        self.assertEqual(result, {kind: 0 for kind in encounters.DIRECT_ENCOUNTER_TYPES})
