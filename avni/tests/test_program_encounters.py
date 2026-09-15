"""Family factsheet and Daily Reporting program encounters."""

from datetime import date

from django.test import TestCase

from avni import paths
from avni.sync import program_encounters as pe
from avni.tests.support import FakeApi, make_city, make_slum, page, program_encounter_record, subject_record
from graphs.models import HouseholdData
from mastersheet.models import ToiletConstruction
from notification.services import reporting

SINCE = "2026-01-01T00:00:00.000Z"


class DailyReportingFieldTests(TestCase):
    """toilet_construction_fields is pure; cover every status branch."""

    def test_agreement_only_is_material_not_given(self):
        fields = pe.toilet_construction_fields({"Date of agreement": "2026-01-05", "x": 1})
        self.assertEqual(fields["agreement_date"], date(2026, 1, 5))
        self.assertEqual(fields["status"], pe.STATUS_MATERIAL_NOT_GIVEN)
        self.assertFalse(fields["agreement_cancelled"])

    def test_phase_one_material_is_under_construction_with_latest_date(self):
        fields = pe.toilet_construction_fields({
            "Date of agreement": "2026-01-05",
            "Date on which bricks are given": "2026-01-10",
            "Date on which cement is given": "2026-01-12",
        })
        self.assertEqual(fields["phase_one_material_date"].date(), date(2026, 1, 12))
        self.assertEqual(fields["status"], pe.STATUS_UNDER_CONSTRUCTION)

    def test_completion_wins(self):
        fields = pe.toilet_construction_fields({
            "Date on which bricks are given": "2026-01-10",
            "Date on which toilet construction is complete": "2026-02-01",
        })
        self.assertEqual(fields["completion_date"], date(2026, 2, 1))
        self.assertEqual(fields["status"], pe.STATUS_COMPLETED)

    def test_cancelled_agreement_blocks_material_dates_and_reads_shifts(self):
        fields = pe.toilet_construction_fields({
            "Date of agreement": "2026-01-05",
            "Date on which agreement is cancelled": "2026-01-20",
            "Date on which bricks are given": "2026-01-10",
            "House numbers of houses where PHASE 1 material bricks, sand and cement is given": "17",
        })
        self.assertTrue(fields["agreement_cancelled"])
        self.assertIsNone(fields["phase_one_material_date"])
        self.assertEqual(fields["p1_material_shifted_to"], 17)
        self.assertIsNone(fields["p2_material_shifted_to"])
        self.assertEqual(fields["status"], pe.STATUS_AGREEMENT_CANCELLED)

    def test_shift_within_slum_blocks_only_shifted_phase(self):
        fields = pe.toilet_construction_fields({
            "Is the material is shifted ?": "Yes, Within the Slum",
            "Date on which bricks are given": "2026-01-10",
            "Date on which pan is given": "2026-01-15",
            "House numbers of houses where PHASE 1 material bricks, sand and cement is given": "9",
        })
        self.assertIsNone(fields["phase_one_material_date"])
        self.assertEqual(fields["phase_two_material_date"].date(), date(2026, 1, 15))
        self.assertEqual(fields["p1_material_shifted_to"], 9)

    def test_shift_outside_slum_means_nothing_to_record(self):
        self.assertIsNone(pe.toilet_construction_fields({"Is the material is shifted ?": "Yes, Outside the Slum"}))

    def test_no_dates_at_all_has_no_status(self):
        self.assertIsNone(pe.toilet_construction_fields({"Comment if any ?": "hi"})["status"])

    def test_blank_shift_number_is_none(self):
        fields = pe.toilet_construction_fields({
            "Date on which agreement is cancelled": "2026-01-20",
            "House numbers of houses where Septic Tank is given": "",
        })
        self.assertIsNone(fields["st_material_shifted_to"])

    def test_bad_date_raises(self):
        with self.assertRaises(Exception):
            pe.toilet_construction_fields({"Date of agreement": "not a date", "x": 1})


class DailyReportingSaveTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_creates_then_updates_same_row_keeping_source_uuid(self):
        self.assertTrue(pe.save_daily_reporting({"Date of agreement": "2026-01-05", "x": 1}, "Lokmanya Nagar", "42", "penc-1"))
        row = ToiletConstruction.objects.get(household_number="42", slum=self.slum)
        self.assertEqual(row.status, str(pe.STATUS_MATERIAL_NOT_GIVEN))
        self.assertEqual(row.source_uuid, "penc-1")

        pe.save_daily_reporting({"Date on which bricks are given": "2026-01-10", "x": 1}, "Lokmanya Nagar", "42", None)
        row.refresh_from_db()
        self.assertEqual(row.status, str(pe.STATUS_UNDER_CONSTRUCTION))
        self.assertEqual(row.source_uuid, "penc-1", "a Kobo-path update must not wipe the AVNI uuid")
        self.assertEqual(ToiletConstruction.objects.count(), 1)

    def test_single_answer_is_ignored(self):
        self.assertFalse(pe.save_daily_reporting({"Date of agreement": "2026-01-05"}, "Lokmanya Nagar", "42"))
        self.assertEqual(ToiletConstruction.objects.count(), 0)

    def test_unknown_slum_raises(self):
        with self.assertRaises(LookupError):
            pe.save_daily_reporting({"Date of agreement": "2026-01-05", "x": 1}, "Nowhere", "42")


class FamilyFactsheetTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.api = FakeApi({paths.subject("sub-1"): subject_record()})

    def factsheet(self, **observations):
        base = {"Use of toilet": ["Men", "Women"], "Where the individual toilet is connected ?": "Sewer"}
        base.update(observations)
        return program_encounter_record(encounter_type=pe.FAMILY_FACTSHEET, observations=base)

    def test_registers_household_and_writes_ff_data(self):
        from avni.sync import households

        record = self.factsheet()
        household = households.fetch_household("sub-1", self.api)
        pe.save_family_factsheet(record, household)
        row = HouseholdData.objects.get(household_number="42")
        self.assertEqual(row.ff_data["ff_uuid"], "penc-1")
        self.assertEqual(row.ff_data["group_ne3ao98/Use_of_toilet"], "Men,Women")

    def test_toilet_construction_dates_follow_answers(self):
        from avni.sync import households

        ToiletConstruction.objects.create(household_number="42", slum=self.slum)
        household = households.fetch_household("sub-1", self.api)
        pe.save_family_factsheet(self.factsheet(), household)
        toilet = ToiletConstruction.objects.get(household_number="42")
        self.assertEqual(toilet.factsheet_done, date(2026, 9, 1))
        self.assertEqual(toilet.toilet_connected_to, date(2026, 9, 1))
        self.assertEqual(toilet.use_of_toilet, date(2026, 9, 1))

        pe.save_family_factsheet(self.factsheet(**{"Where the individual toilet is connected ?": "Not connected"}), household)
        toilet.refresh_from_db()
        self.assertIsNone(toilet.toilet_connected_to)


class ProgramEncounterSyncTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_daily_reporting_sync_end_to_end(self):
        records = [
            program_encounter_record("p1", observations={"Date of agreement": "2026-01-05", "x": 1}),
            program_encounter_record("p2", voided=True),
            program_encounter_record("p3", observations={}),
            program_encounter_record("p4", subject_uuid="ghost", observations={"Date of agreement": "2026-01-05", "x": 1}),
            program_encounter_record("p5", observations={"Date of agreement": "garbage", "x": 1}),
        ]
        api = FakeApi({paths.program_encounters("Daily Reporting", SINCE): page(records), paths.subject("sub-1"): subject_record()})
        recorder = reporting.start("daily_reporting_sync", trigger="manual")
        with recorder.step("daily_reporting"):
            saved = pe.sync_daily_reporting(from_date="2026-01-01", api=api)
        step = recorder.finish().steps.get()
        self.assertEqual(saved, 1)
        self.assertEqual((step.records_ok, step.records_failed, step.records_skipped), (1, 2, 2))
        self.assertEqual(ToiletConstruction.objects.get(household_number="42").source_uuid, "p1")

    def test_unknown_program_encounter_type_is_a_failure(self):
        record = program_encounter_record(encounter_type="Mystery", observations={"a": 1})
        api = FakeApi({paths.program_encounter("penc-1"): record, paths.subject("sub-1"): subject_record()})
        recorder = reporting.start("x", trigger="manual")
        with recorder.step("s"):
            self.assertFalse(pe.sync_program_encounter_by_uuid("penc-1", api=api))
        step = recorder.finish().steps.get()
        self.assertEqual(step.records_failed, 1)
