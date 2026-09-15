"""JSON file imports (encounter_sync.sh) and member imports."""

import json
import os
import tempfile

from django.test import TestCase

from avni import paths
from avni.sync import file_imports, members
from avni.tests.support import FakeApi, make_city, make_slum, subject_record
from graphs.models import FollowupData, HouseholdData, MemberData, MemberEncounterData, MemberProgramData
from notification.services import reporting


def json_file(rows):
    handle, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(handle, "w") as out:
        json.dump(rows, out)
    return path


def encounter_row(**extra):
    row = {
        "household_number": "42", "Slum": "Lokmanya Nagar", "Household_uuid": "sub-1",
        "HH_created_date": "2021-08-17T04:37:33.023Z", "HH_last_modified_date": "2026-09-01T06:47:34.548Z",
        "Last_modified_date": "2026-09-01T06:47:34.548Z", "empty": "", "answer": "yes",
    }
    row.update(extra)
    return row


class EncounterFileImportTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.api = FakeApi({paths.subject("sub-1"): subject_record()})
        self.paths = []

    def tearDown(self):
        for path in self.paths:
            os.remove(path)

    def file(self, rows):
        path = json_file(rows)
        self.paths.append(path)
        return path

    def test_sanitation_registers_household_merges_and_creates_followup(self):
        path = self.file([encounter_row(Sanitation_encounter_uuid="s-1")])
        self.assertEqual(file_imports.import_sanitation(path, api=self.api), 1)
        row = HouseholdData.objects.get(household_number="42")
        self.assertEqual(row.rhs_data["answer"], "yes")
        self.assertNotIn("empty", row.rhs_data)
        self.assertNotIn("Sanitation_encounter_uuid", row.rhs_data)
        self.assertEqual(FollowupData.objects.get(household_number="42").followup_data["answer"], "yes")

    def test_water_requires_connection_type(self):
        path = self.file([encounter_row(), encounter_row(**{"group_el9cl08/Type_of_water_connection": "Own"})])
        self.assertEqual(file_imports.import_water(path, api=self.api), 1)

    def test_bad_row_is_recorded_and_others_continue(self):
        path = self.file([encounter_row(household_number="abc"), encounter_row()])
        recorder = reporting.start("file_import", trigger="manual")
        with recorder.step("import:waste"):
            saved = file_imports.import_encounter_rows(path, api=self.api)
        step = recorder.finish().steps.get()
        self.assertEqual(saved, 1)
        self.assertEqual((step.records_ok, step.records_failed), (1, 1))

    def test_electricity_nested_under_its_own_key(self):
        path = self.file([{
            "household__first_name": "42", "household__uuid": "sub-1", "Slum": "Lokmanya Nagar",
            "uuid": "e-1", "Date of Survey": "2026-01-01", "Name on the electricity bill": "None",
            "Do you have electricity in the house ?": "Yes",
        }])
        self.assertEqual(file_imports.import_electricity(path, api=self.api), 1)
        electricity = HouseholdData.objects.get(household_number="42").rhs_data["Electricity_data"]
        self.assertEqual(electricity, {"uuid": "e-1", "Do you have electricity in the house ?": "Yes"})

    def test_households_file_of_subject_records(self):
        path = self.file([subject_record("a", number="1"), subject_record("v", number="2", voided=True)])
        self.assertEqual(file_imports.import_households(path), 1)


class MemberImportTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.paths = []

    def tearDown(self):
        for path in self.paths:
            os.remove(path)

    def file(self, rows):
        path = json_file(rows)
        self.paths.append(path)
        return path

    def member_row(self, **extra):
        row = {
            "member_uuid": "m-1", "slum": "Lokmanya Nagar", "created_date": "2026-01-01", "submission_date": "2026-01-02",
            "date_of_birth": "March 5, 1990", "household_number": " 42 ", "gender": "Female", "member_first_name": "A",
        }
        row.update(extra)
        return row

    def test_members_then_programs_then_encounters(self):
        self.assertEqual(members.import_members(self.file([self.member_row(), self.member_row(slum="Nowhere", member_uuid="m-2")])), 1)
        member = MemberData.objects.get(member_uuid="m-1")
        self.assertEqual((member.gender, member.household_number), ("2", "42"))

        programs = self.file([{
            "member_id": "m-1", "created_date": "2026-01-01", "submission_date": "2026-01-02", "program_exit_date": "",
            "family_member_menstrual_hygiene__uuid": "p-1", "first_name": "A",
        }, {"member_id": "ghost", "created_date": "2026-01-01", "submission_date": "2026-01-02",
            "program_exit_date": "", "family_member_menstrual_hygiene__uuid": "p-2", "first_name": "B"}])
        self.assertEqual(members.import_member_programs(programs), 1)
        self.assertEqual(MemberProgramData.objects.get(member=member).program_uuid, "p-1")

        encounters = self.file([{
            "member_id": "m-1", "created_date": "2026-01-01", "submission_date": "2026-01-02",
            "program_id": 1, "program__name": "x", "first_name": "A", "encounter_uuid": "e-1",
        }])
        self.assertEqual(members.import_member_encounters(encounters), 1)
        self.assertEqual(MemberEncounterData.objects.get(member=member).encounter_uuid, "e-1")

    def test_reimport_updates_instead_of_duplicating(self):
        path = self.file([self.member_row()])
        members.import_members(path)
        members.import_members(path)
        self.assertEqual(MemberData.objects.count(), 1)
