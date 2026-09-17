"""Household registration sync against a fake AVNI and the real models."""

from django.test import TestCase
from django.utils import timezone

from avni import paths, window
from avni.sync import households
from avni.tests.support import FakeApi, make_city, make_slum, page, subject_record
from graphs.models import HouseholdData
from notification.services import reporting


class HouseholdSaveTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_creates_household_with_mapped_keys(self):
        record = subject_record(observations={"Aadhaar number": "1234", "Do you have a toilet at home?": "Yes"})
        self.assertTrue(households.save_household(record))
        row = HouseholdData.objects.get(slum=self.slum, household_number="42")
        self.assertEqual(row.city, self.city)
        self.assertEqual(row.rhs_data["rhs_uuid"], "sub-1")
        self.assertEqual(row.rhs_data["Household_number"], "0042")
        self.assertEqual(row.rhs_data["group_el9cl08/Aadhar_number"], "1234")
        self.assertEqual(row.rhs_data["Current place of defecation"], "Own toilet")
        self.assertEqual(row.rhs_data["group_og5bx85/Type_of_survey"], "RHS")
        self.assertEqual(str(timezone.localtime(row.created_date).date()), "2018-03-20")

    def test_update_merges_without_losing_existing_keys(self):
        HouseholdData.objects.create(
            household_number="42", slum=self.slum, city=self.city, submission_date="2020-01-01T00:00:00Z",
            rhs_data={"kept": "yes", "Type_of_structure_occupancy": "Shop", "Type of shop": "Kirana"},
        )
        households.save_household(subject_record(observations={"Ownership status of the house_1": "Own house/Shop"}))
        row = HouseholdData.objects.get(slum=self.slum, household_number="42")
        self.assertEqual(row.rhs_data["kept"], "yes")
        self.assertNotIn("Type of shop", row.rhs_data, "shop-only questions are dropped for shops")
        self.assertEqual(row.rhs_data["group_el9cl08/Ownership_status_of_the_house"], "Own house")
        self.assertEqual(HouseholdData.objects.count(), 1)

    def test_alphanumeric_household_number(self):
        households.save_household(subject_record(number="0022A"))
        self.assertTrue(HouseholdData.objects.filter(household_number="22A").exists())

    def test_functioning_of_structure_becomes_occupancy(self):
        households.save_household(subject_record(observations={"Functioning of the structure": "Shop"}))
        row = HouseholdData.objects.get(household_number="42")
        self.assertEqual(row.rhs_data["Type_of_structure_occupancy"], "Shop")
        self.assertNotIn("Functioning of the structure", row.rhs_data)

    def test_unknown_slum_is_reported_not_raised(self):
        self.assertFalse(households.save_household(subject_record(slum="Nowhere")))
        self.assertEqual(HouseholdData.objects.count(), 0)

    def test_missing_first_name_is_reported_not_raised(self):
        record = subject_record()
        del record["observations"]["First name"]
        self.assertFalse(households.save_household(record))

    def test_existing_rhs_data_none_is_tolerated(self):
        HouseholdData.objects.create(
            household_number="42", slum=self.slum, city=self.city, submission_date="2020-01-01T00:00:00Z", rhs_data=None
        )
        self.assertTrue(households.save_household(subject_record()))
        self.assertEqual(HouseholdData.objects.get(household_number="42").rhs_data["rhs_uuid"], "sub-1")


class HouseholdSyncTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def listing(self, records, pages=None):
        since = "2026-01-01T00:00:00.000Z"
        path = paths.subjects("Household", since)
        return FakeApi({path: pages or page(records)}), path

    def test_syncs_every_page_and_skips_voided(self):
        first = page([subject_record("a", number="1"), subject_record("b", number="2", voided=True)], total_pages=2)
        second = page([subject_record("c", number="3")], total_pages=2)
        api, path = self.listing([], pages=[first, second])
        saved = households.sync_households("Household", from_date="2026-01-01", api=api)
        self.assertEqual(saved, 2)
        self.assertEqual(sorted(HouseholdData.objects.values_list("household_number", flat=True)), ["1", "3"])
        self.assertEqual(api.calls, [path, path + "&page=1"])

    def test_records_and_skips_are_counted_on_the_job_step(self):
        api, path = self.listing([
            subject_record("a", number="1"),
            subject_record("b", number="2", voided=True),
            subject_record("c", number="3", slum="Nowhere"),
        ])
        recorder = reporting.start("rhs_sync", trigger="manual")
        with recorder.step("households:Household"):
            households.sync_households("Household", from_date="2026-01-01", api=api)
        run = recorder.finish()
        step = run.steps.get()
        self.assertEqual((step.records_ok, step.records_failed, step.records_skipped), (1, 1, 1))
        self.assertEqual(run.status, "partial")
        self.assertEqual(step.sample_failures[0]["slum"], "Nowhere")

    def test_window_start_is_noted_on_the_step(self):
        api, path = self.listing([])
        recorder = reporting.start("rhs_sync", trigger="manual")
        with recorder.step("households:Household") as step:
            households.sync_households("Household", from_date="2026-01-01", api=api)
            self.assertEqual(step.extras["window_start"], "2026-01-01T00:00:00.000Z")
        recorder.finish()

    def test_default_window_is_day_before_newest_household(self):
        HouseholdData.objects.create(
            household_number="9", slum=self.slum, city=self.city, submission_date="2026-03-10T10:00:00Z", rhs_data={}
        )
        self.assertEqual(window.window_start("Household"), "2026-03-09T00:00:00.000Z")

    def test_default_window_without_data_uses_today(self):
        start = window.window_start("Household")
        self.assertTrue(start.endswith("T00:00:00.000Z"))

    def last_run(self, job_key, status, started):
        from notification.models import JobRun

        JobRun.objects.create(job_key=job_key, status=status, started_on=started)

    def window_inside_run(self, job_key):
        recorder = reporting.start(job_key, trigger="manual")
        try:
            return window.window_start("Household")
        finally:
            recorder.finish()

    def test_last_successful_run_of_same_job_advances_the_window(self):
        HouseholdData.objects.create(
            household_number="9", slum=self.slum, city=self.city, submission_date="2026-03-10T10:00:00Z", rhs_data={}
        )
        self.last_run("avni_daily_sync", "success", "2026-03-14T22:00:00Z")
        self.assertEqual(self.window_inside_run("avni_daily_sync"), "2026-03-13T00:00:00.000Z")

    def test_failed_partial_or_other_jobs_runs_do_not_advance_the_window(self):
        HouseholdData.objects.create(
            household_number="9", slum=self.slum, city=self.city, submission_date="2026-03-10T10:00:00Z", rhs_data={}
        )
        self.last_run("avni_daily_sync", "failed", "2026-03-14T22:00:00Z")
        self.last_run("avni_daily_sync", "partial", "2026-03-15T22:00:00Z")
        self.last_run("encounter_sync", "success", "2026-03-16T22:00:00Z")
        self.assertEqual(self.window_inside_run("avni_daily_sync"), "2026-03-09T00:00:00.000Z")

    def test_newer_data_still_wins_over_an_older_run(self):
        HouseholdData.objects.create(
            household_number="9", slum=self.slum, city=self.city, submission_date="2026-03-10T10:00:00Z", rhs_data={}
        )
        self.last_run("avni_daily_sync", "success", "2026-03-08T22:00:00Z")
        self.assertEqual(self.window_inside_run("avni_daily_sync"), "2026-03-09T00:00:00.000Z")

    def test_list_failure_propagates(self):
        from avni.client import AvniError

        api = FakeApi({})
        with self.assertRaises(AvniError):
            households.sync_households("Household", from_date="2026-01-01", api=api)


class HouseholdByUuidTests(TestCase):
    def setUp(self):
        make_slum(make_city())

    def test_fetch_and_save_by_uuid(self):
        api = FakeApi({paths.subject("sub-1"): subject_record()})
        self.assertTrue(households.sync_household_by_uuid("sub-1", api=api))
        self.assertTrue(HouseholdData.objects.filter(household_number="42").exists())

    def test_missing_uuid_returns_false(self):
        self.assertFalse(households.sync_household_by_uuid("ghost", api=FakeApi({})))

    def test_many_uuids_counts_saved(self):
        api = FakeApi({paths.subject("a"): subject_record("a", number="1"), paths.subject("v"): subject_record("v", voided=True)})
        self.assertEqual(households.sync_households_by_uuid(["a", "v", "ghost"], api=api), 1)

    def test_merge_into_rhs_data_registers_unknown_household_first(self):
        api = FakeApi({paths.subject("sub-1"): subject_record()})
        household = households.fetch_household("sub-1", api)
        households.merge_into_rhs_data(household, {"extra": 1})
        row = HouseholdData.objects.get(household_number="42")
        self.assertEqual(row.rhs_data["extra"], 1)
        self.assertEqual(row.rhs_data["rhs_uuid"], "sub-1")
