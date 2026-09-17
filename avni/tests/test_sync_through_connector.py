"""The legacy listing loops now run through survey.connector: same legacy
results, plus core Record rows, plus no repeated work on a second pass."""

from django.test import TestCase

from avni import paths, window
from avni.sync import encounters, households
from avni.tests.support import FakeApi, encounter_record, make_city, make_slum, page, subject_record
from graphs.models import FollowupData, HouseholdData
from notification.services import reporting
from survey.models import Record

SINCE = "2026-01-01T00:00:00.000Z"


class HouseholdsThroughConnectorTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_saved_voided_and_unlinked_subjects_all_get_core_rows(self):
        path = paths.subjects("Household", SINCE)
        api = FakeApi({path: page([
            subject_record("a", number="1"),
            subject_record("v", number="2", voided=True),
            subject_record("u", number="3", slum="Nowhere"),
        ])})
        saved = households.sync_households("Household", from_date=SINCE, api=api)
        self.assertEqual(saved, 1)
        self.assertEqual(HouseholdData.objects.count(), 1, "legacy behaviour unchanged")
        rows = {row.external_id: row for row in Record.objects.all()}
        self.assertEqual(sorted(rows), ["a", "u", "v"])
        self.assertTrue(rows["v"].is_voided)
        self.assertEqual(rows["a"].household, HouseholdData.objects.get())
        self.assertIsNone(rows["u"].slum)

    def test_a_second_run_changes_nothing_and_fetches_nothing_extra(self):
        path = paths.subjects("Household", SINCE)
        api = FakeApi({path: page([subject_record("a", number="1")])})
        households.sync_households("Household", from_date=SINCE, api=api)
        first_calls = list(api.calls)
        recorder = reporting.start("rhs_sync", trigger="manual")
        with recorder.step("households:Household") as step:
            households.sync_households("Household", from_date=SINCE, api=api)
        recorder.finish()
        self.assertEqual(api.calls, first_calls + [path])
        self.assertEqual((step.extras["created"], step.extras["updated"], step.extras["unchanged"]), ("0", "0", "1"))
        self.assertEqual(Record.objects.count(), 1)


class EncountersThroughConnectorTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def api(self, records):
        return FakeApi({
            paths.encounters("Sanitation", SINCE): page(records),
            paths.subject("sub-1"): subject_record(),
        })

    def test_legacy_merge_and_core_rows_from_one_pass(self):
        api = self.api([
            encounter_record("e1", observations={"Status of toilet under SBM ?": "Built"}),
            encounter_record("e2", observations={"Status of toilet under SBM ?": "Planned"}),
        ])
        saved = encounters.sync_encounters("Sanitation", from_date=SINCE, api=api)
        self.assertEqual(saved, 2)
        self.assertEqual(HouseholdData.objects.get().rhs_data["group_oi8ts04/Status_of_toilet_under_SBM"], "Planned")
        self.assertTrue(FollowupData.objects.filter(household_number="42").exists())
        self.assertEqual(Record.objects.filter(kind="encounter").count(), 2)
        self.assertEqual(api.calls.count(paths.subject("sub-1")), 1, "one subject fetch for two encounters")
        row = Record.objects.get(external_id="e1")
        self.assertEqual(row.household, HouseholdData.objects.get())
        self.assertEqual(row.answers_by_key()["status_of_toilet_under_sbm"], "Built")

    def test_a_second_run_makes_no_subject_call_at_all(self):
        api = self.api([encounter_record("e1")])
        encounters.sync_encounters("Sanitation", from_date=SINCE, api=api)
        api.calls = []
        encounters.sync_encounters("Sanitation", from_date=SINCE, api=api)
        self.assertEqual(api.calls, [paths.encounters("Sanitation", SINCE)])

    def test_an_edited_encounter_is_merged_again(self):
        api = self.api([encounter_record("e1", observations={"Status of toilet under SBM ?": "Built"})])
        encounters.sync_encounters("Sanitation", from_date=SINCE, api=api)
        api.routes[paths.encounters("Sanitation", SINCE)] = page([
            encounter_record("e1", observations={"Status of toilet under SBM ?": "Demolished"},
                             modified="2026-09-03T00:00:00.000Z"),
        ])
        encounters.sync_encounters("Sanitation", from_date=SINCE, api=api)
        self.assertEqual(HouseholdData.objects.get().rhs_data["group_oi8ts04/Status_of_toilet_under_SBM"], "Demolished")
        self.assertEqual(Record.objects.get(external_id="e1").answers_by_key()["status_of_toilet_under_sbm"], "Demolished")

    def test_the_window_start_is_still_noted_on_the_step(self):
        api = self.api([])
        recorder = reporting.start("encounter_sync", trigger="manual")
        with recorder.step("encounters:Sanitation") as step:
            encounters.sync_encounters("Sanitation", from_date=SINCE, api=api)
        recorder.finish()
        self.assertEqual(step.extras["window_start"], window.format_from_date(SINCE))
