"""Re-sync by uuid, Structure/DSES saving, and the Excel/uuid bulk helpers."""

import os
import tempfile

from django.test import TestCase

from avni import paths
from avni.sync import by_uuid, structures
from avni.tests.support import FakeApi, encounter_record, make_city, make_slum, page, program_encounter_record, subject_record
from graphs.models import HouseholdData
from mastersheet.models import ActivityType, CommunityMobilizationActivityAttendance, ToiletConstruction
from notification.services import reporting


class ByUuidTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        activity = ActivityType.objects.create(name="Workshop for Women", key="0", display_order=1)
        activity.key = str(activity.id)
        activity.save()
        self.api = FakeApi({
            paths.subject("sub-1"): subject_record(),
            paths.subject("sub-v"): subject_record("sub-v", voided=True),
            paths.encounter("enc-1"): encounter_record(observations={"A": 1}),
            paths.encounter("act-1"): encounter_record("act-1", encounter_type="Daily Mobilization Activity", observations={
                "Type of Activity": "Workshop for Women", "Date of the activity conducted": "2026-03-03", "Number of Women present": 4}),
            paths.program_encounter("penc-1"): program_encounter_record(observations={"Date of agreement": "2026-01-05", "x": 1}),
        })

    def run_kind(self, kind, uuids):
        recorder = reporting.start("by_uuid", trigger="manual")
        with recorder.step(kind):
            counts = by_uuid.sync_by_uuid(kind, uuids, api=self.api)
        return counts, recorder.finish().steps.get()

    def test_subjects(self):
        counts, step = self.run_kind("subject", ["sub-1", "sub-v", "ghost"])
        self.assertEqual(counts, {"saved": 1, "skipped": 1, "failed": 1})
        self.assertTrue(HouseholdData.objects.filter(household_number="42").exists())
        self.assertEqual(step.records_failed, 1)

    def test_encounters_including_activity(self):
        counts, step = self.run_kind("encounter", ["enc-1", "act-1"])
        self.assertEqual(counts["saved"], 2)
        self.assertEqual(HouseholdData.objects.get(household_number="42").rhs_data["A"], 1)
        self.assertEqual(CommunityMobilizationActivityAttendance.objects.get().females_attended_activity, 4)

    def test_program_encounters(self):
        counts, step = self.run_kind("program_encounter", ["penc-1"])
        self.assertEqual(counts["saved"], 1)
        self.assertEqual(ToiletConstruction.objects.get(household_number="42").source_uuid, "penc-1")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            by_uuid.sync_by_uuid("thing", ["x"], api=self.api)

    def test_unknown_subject_type_rejected(self):
        with self.assertRaises(ValueError):
            by_uuid.sync_by_uuid("subject", ["sub-1"], api=self.api, subject_type="Yadav Nagar")

    def test_mobilization_subject_type(self):
        from mastersheet.models import CommunityMobilization

        activity = ActivityType.objects.create(name="Samitee meeting 1", key="0", display_order=1)
        activity.key = str(activity.id)
        activity.save()
        self.api.routes[paths.subject("mob")] = subject_record("mob", number="", observations={
            "Type of Activity": "Samitee meeting 1", "Date of Survey": "2026-02-01"})
        counts = by_uuid.sync_by_uuid("subject", ["mob"], api=self.api, subject_type="New_Mobilization_Form")
        self.assertEqual(counts["saved"], 1)
        self.assertEqual(CommunityMobilization.objects.count(), 1)


class StructureTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def structure(self, uuid="st-1", number="0007", voided=False, **observations):
        data = {"Ward No": "12", "Number of flats in the building ?": 4, "Do you have a toilet at home?": "Yes"}
        data.update(observations)
        return subject_record(uuid, number=number, voided=voided, observations=data)

    def test_save_maps_known_questions_and_passes_unknown_through(self):
        self.assertTrue(structures.save_structure_record(self.structure(**{"Brand new question": "v"})))
        row = HouseholdData.objects.get(household_number="7")
        self.assertEqual(row.rhs_data["Select Ward"], "12")
        self.assertEqual(row.rhs_data["Number of units in the building ?"], 4)
        self.assertEqual(row.rhs_data["Brand new question"], "v")
        self.assertEqual(row.rhs_data["group_oi8ts04/Current_place_of_defecation"], "Own toilet")
        self.assertEqual(row.rhs_data["Household_number"], "7")

    def test_empty_observations_not_saved(self):
        record = self.structure()
        record["observations"] = {}
        self.assertFalse(structures.save_structure_record(record))

    def test_missing_slum_not_saved(self):
        record = self.structure()
        record["location"] = {}
        self.assertFalse(structures.save_structure_record(record))

    def test_sync_subject_type_pages_and_skips_voided(self):
        path = paths.subjects("Structure", "2026-01-01T00:00:00.000Z")
        api = FakeApi({path: [page([self.structure("a", "1"), self.structure("v", "2", voided=True)], 2), page([self.structure("c", "3")], 2)]})
        self.assertEqual(structures.sync_subject_type("Structure", "2026-01-01T00:00:00.000Z", api=api), 2)

    def test_by_uuid_counts_every_outcome(self):
        api = FakeApi({paths.subject("a"): self.structure("a", "1"), paths.subject("v"): self.structure("v", "2", voided=True)})
        api.routes[paths.subject("e")] = self.structure("e", "3")
        api.routes[paths.subject("e")]["observations"] = {}
        counts = structures.sync_subjects_by_uuid(["a", "v", "e", "ghost", " "], workers=1, api=api)
        self.assertEqual(counts, {"saved": 1, "voided": 1, "fetch_failed": 1, "save_failed": 1, "errors": 0})

    def test_from_excel(self):
        api = FakeApi({paths.subject("a"): self.structure("a", "1")})
        handle, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(handle)
        try:
            from openpyxl import Workbook

            book = Workbook()
            book.active.append(["uuid", "note"])
            book.active.append(["a", ""])
            book.active.append([None, "blank uuid"])
            book.active.append([" ", ""])
            book.save(path)
            counts = structures.sync_subjects_from_excel(path, workers=1, api=api)
        finally:
            os.remove(path)
        self.assertEqual(counts["saved"], 1)

    def test_summary_counts_without_writing(self):
        path = paths.subjects("Structure", "2026-01-01T00:00:00.000Z", "loc")
        api = FakeApi({path: page([self.structure("a", "1"), self.structure("v", "2", voided=True)])})
        summary = structures.subject_summary("Structure", "loc", "2026-01-01T00:00:00.000Z", api=api)
        self.assertEqual((summary["total"], summary["voided"], summary["not_voided"]), (2, 1, 1))
        self.assertEqual(summary["ward_distribution"], {"Unknown": 1})
        self.assertEqual(HouseholdData.objects.count(), 0)
