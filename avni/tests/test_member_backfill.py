"""Putting household numbers back on members from an AVNI member export."""

import csv
import io
import os
import tempfile

from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook

from avni.sync import member_backfill
from avni.tests.support import make_city, make_slum
from graphs.models import HouseholdData, MemberData
from survey.models import SlumAlias

HEADER = ["City", "Slum", "household__uuid", "household__first_name",
          "family_member - member_subject_id__uuid", "family_member - member_subject_id__first_name"]


class BackfillCase(TestCase):
    def setUp(self):
        self.city = make_city("Pune")
        self.slum = make_slum(self.city, name="Antule Nagar, Pisoli", code="AN1")
        self.other = make_slum(self.city, name="Indira Vasahat", code="IV1")
        for slum, number in ((self.slum, "42"), (self.slum, "33A"), (self.slum, "70"), (self.other, "42")):
            HouseholdData.objects.create(household_number=number, slum=slum, city=self.city,
                                         submission_date="2026-01-01T00:00:00Z")
        self.folder = tempfile.mkdtemp()

    def member(self, uuid, number=None, slum=None):
        return MemberData.objects.create(slum=slum or self.slum, member_uuid=uuid, household_number=number,
                                         member_first_name="Asha")

    def sheet(self, rows, name="export.csv"):
        path = os.path.join(self.folder, name)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(HEADER)
            for city, slum, number, uuid in rows:
                writer.writerow([city, slum, "hh-" + number, number, uuid, "Asha Patil"])
        return path

    def run_backfill(self, path, apply=False):
        report = os.path.join(self.folder, "report.csv")
        lines = []
        counts = member_backfill.run(path, apply=apply, report=report, out=lines.append)
        with open(report, encoding="utf-8") as handle:
            self.report = {row["member_uuid"]: row for row in csv.DictReader(handle)}
        self.output = "\n".join(lines)
        return counts

    def number(self, uuid):
        return MemberData.objects.get(member_uuid=uuid).household_number


class FillTests(BackfillCase):
    def test_dry_run_writes_nothing(self):
        self.member("m1")
        counts = self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1")]))
        self.assertEqual(counts["updated"], 1)
        self.assertIsNone(self.number("m1"))
        self.assertIn("dry run", self.output.lower())

    def test_blank_number_is_filled_without_leading_zeros(self):
        self.member("m1")
        self.member("m2", number="")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1"),
                                      ("Pune", "Antule Nagar, Pisoli", "0033A", "m2")]), apply=True)
        self.assertEqual(self.number("m1"), "42")
        self.assertEqual(self.number("m2"), "33A")
        self.assertEqual(self.report["m1"]["action"], "updated")
        self.assertEqual(self.report["m1"]["old_number"], "")

    def test_alias_slum_name_counts_as_the_members_slum(self):
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="loc-new",
                                 external_name="Antule Nagar, Pisoli New", is_primary=False)
        self.member("m1")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli New", "0042", "m1")]), apply=True)
        self.assertEqual(self.number("m1"), "42")

    def test_same_number_is_left_alone(self):
        self.member("m1", number="42")
        counts = self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1")]), apply=True)
        self.assertEqual(counts["unchanged"], 1)
        self.assertEqual(self.report["m1"]["action"], "unchanged")

    def test_float_spelling_is_corrected(self):
        self.member("m1", number="70.0")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0070", "m1")]), apply=True)
        self.assertEqual(self.number("m1"), "70")

    def test_a_different_number_is_kept(self):
        self.member("m1", number="33A")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1")]), apply=True)
        self.assertEqual(self.number("m1"), "33A")
        self.assertEqual(self.report["m1"]["reason"], member_backfill.CONFLICT)

    def test_number_set_after_planning_is_not_overwritten(self):
        self.member("m1")
        plan = member_backfill.plan(member_backfill.read_rows(
            self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1")])))
        MemberData.objects.filter(member_uuid="m1").update(household_number="70")
        self.assertEqual(member_backfill.apply_changes(plan), 0)
        self.assertEqual(self.number("m1"), "70")


class SkipTests(BackfillCase):
    def assertSkipped(self, uuid, reason):
        self.assertEqual(self.report[uuid]["action"], "skipped")
        self.assertEqual(self.report[uuid]["reason"], reason)

    def test_household_in_another_slum_is_skipped(self):
        self.member("m1")
        self.run_backfill(self.sheet([("Pune", "Indira Vasahat", "0042", "m1")]), apply=True)
        self.assertIsNone(self.number("m1"))
        self.assertSkipped("m1", member_backfill.OTHER_SLUM)

    def test_member_in_two_households_is_skipped(self):
        self.member("m1")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1"),
                                      ("Pune", "Antule Nagar, Pisoli", "0070", "m1")]), apply=True)
        self.assertIsNone(self.number("m1"))
        self.assertSkipped("m1", member_backfill.TWO_HOUSEHOLDS)

    def test_member_stored_twice_is_skipped(self):
        self.member("m1")
        self.member("m1", slum=self.other)
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1")]), apply=True)
        self.assertEqual(list(MemberData.objects.filter(member_uuid="m1").values_list("household_number", flat=True)),
                         [None, None])
        self.assertSkipped("m1", member_backfill.STORED_TWICE)

    def test_number_with_no_household_row_is_skipped(self):
        self.member("m1")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0999", "m1")]), apply=True)
        self.assertIsNone(self.number("m1"))
        self.assertSkipped("m1", member_backfill.NO_HOUSEHOLD)

    def test_unknown_slum_is_skipped(self):
        self.member("m1")
        self.run_backfill(self.sheet([("Pune", "Nowhere", "0042", "m1")]), apply=True)
        self.assertSkipped("m1", member_backfill.NO_SLUM)

    def test_member_missing_from_the_database_is_reported(self):
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "ghost")]), apply=True)
        self.assertSkipped("ghost", member_backfill.NOT_STORED)

    def test_test_city_is_skipped_whatever_its_case(self):
        self.member("m1")
        counts = self.run_backfill(self.sheet([("test_CITY", "Antule Nagar, Pisoli", "0042", "m1")]), apply=True)
        self.assertIsNone(self.number("m1"))
        self.assertEqual(counts[member_backfill.SKIPPED_CITY], 1)
        self.assertNotIn("m1", self.report)

    def test_blank_cells_are_skipped(self):
        self.member("m1")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "nan", "m1")]), apply=True)
        self.assertIsNone(self.number("m1"))
        self.assertSkipped("m1", member_backfill.INCOMPLETE)


class FileTests(BackfillCase):
    def test_excel_export_is_read(self):
        self.member("m1")
        self.member("m2")
        book = Workbook()
        sheet = book.active
        sheet.title = "Query result"
        sheet.append(HEADER)
        sheet.append(["nan", "Antule Nagar, Pisoli", "hh-1", "0042", "m1", "Asha"])
        sheet.append(["Pune", "Antule Nagar, Pisoli", "hh-2", 70, "m2", "Asha"])
        path = os.path.join(self.folder, "export.xlsx")
        book.save(path)
        self.run_backfill(path, apply=True)
        self.assertEqual(self.number("m1"), "42")
        self.assertEqual(self.number("m2"), "70")

    def test_detailed_survey_export_columns_are_read(self):
        self.member("m1")
        path = os.path.join(self.folder, "ichalkaranji.csv")
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["detailed_survey_registration_uuid", "detailet_survey_House_Number", "address__City",
                             "address__Slum", "family_member_uuid", "family_member_first_name"])
            writer.writerow(["hh-1", "0042", "Ichalkaranji", "Antule Nagar, Pisoli", "m1", "Asha"])
        self.run_backfill(path, apply=True)
        self.assertEqual(self.number("m1"), "42")

    def test_missing_column_is_refused(self):
        path = os.path.join(self.folder, "bad.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("City,Slum\nPune,X\n")
        with self.assertRaises(ValueError):
            list(member_backfill.read_rows(path))

    def test_report_holds_no_names(self):
        self.member("m1")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1")]))
        with open(os.path.join(self.folder, "report.csv"), encoding="utf-8") as handle:
            self.assertNotIn("Asha", handle.read())

    def test_restore_puts_old_values_back(self):
        self.member("m1")
        self.member("m2")
        self.run_backfill(self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1"),
                                      ("Pune", "Antule Nagar, Pisoli", "0070", "m2")]), apply=True)
        MemberData.objects.filter(member_uuid="m2").update(household_number="33A")
        restored = member_backfill.restore(os.path.join(self.folder, "report.csv"), apply=True, out=lambda line: None)
        self.assertEqual(restored, 1)
        self.assertIsNone(self.number("m1"))
        self.assertEqual(self.number("m2"), "33A")


class CommandTests(BackfillCase):
    def test_command_is_a_dry_run_unless_told(self):
        self.member("m1")
        path = self.sheet([("Pune", "Antule Nagar, Pisoli", "0042", "m1")])
        report = os.path.join(self.folder, "out.csv")
        out = io.StringIO()
        call_command("backfill_member_households", path, report=report, stdout=out)
        self.assertIsNone(self.number("m1"))
        call_command("backfill_member_households", path, report=report, apply=True, stdout=out)
        self.assertEqual(self.number("m1"), "42")
        self.assertTrue(os.path.exists(report))
