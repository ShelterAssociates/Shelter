"""reconcile_households: ghosts left by renumbers, moves and voids, and factsheet numbers."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from avni import paths
from avni.sync import reconcile
from avni.tests.support import FakeApi, make_city, make_slum, subject_record
from graphs.models import HouseholdData


class ReconcileTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.lines = []

    def row(self, number, uuid="sub-1", ff_data=None, slum=None):
        return HouseholdData.objects.create(
            household_number=number, slum=slum or self.slum, city=self.city, ff_data=ff_data,
            submission_date="2020-01-01T00:00:00Z", rhs_data={"rhs_uuid": uuid},
        )

    def numbers(self):
        return sorted(HouseholdData.objects.values_list("household_number", flat=True))

    def test_dry_run_reports_and_changes_nothing(self):
        self.row("109")
        self.row("110")
        counts = reconcile.run(api=FakeApi({paths.subject("sub-1"): subject_record(number="110")}), out=self.lines.append)
        self.assertEqual(counts["delete"], 1)
        self.assertEqual(self.numbers(), ["109", "110"])
        self.assertTrue(any(line.startswith("DELETE slum") and "hh 109" in line for line in self.lines), self.lines)

    def test_apply_drops_the_stale_copy_and_refreshes_from_avni(self):
        self.row("109")
        self.row("110")
        reconcile.run(apply=True, api=FakeApi({paths.subject("sub-1"): subject_record(number="110", observations={"Aadhaar number": "9"})}), out=self.lines.append)
        row = HouseholdData.objects.get()
        self.assertEqual((row.household_number, row.rhs_data["group_el9cl08/Aadhar_number"]), ("110", "9"))

    def test_apply_renames_when_avni_moved_on_to_a_new_number(self):
        self.row("0022A")
        self.row("22A")
        reconcile.run(apply=True, api=FakeApi({paths.subject("sub-1"): subject_record(number="23A")}), out=self.lines.append)
        self.assertEqual(self.numbers(), ["23A"])

    def test_apply_removes_every_row_of_a_voided_subject(self):
        self.row("109")
        self.row("110")
        self.row("7", uuid="other")
        reconcile.run(apply=True, api=FakeApi({paths.subject("sub-1"): subject_record(number="110", voided=True)}), out=self.lines.append)
        self.assertEqual(self.numbers(), ["7"])

    def test_unreachable_subject_is_skipped_not_deleted(self):
        self.row("109")
        self.row("110")
        counts = reconcile.run(apply=True, api=FakeApi({}), out=self.lines.append)
        self.assertEqual((counts["unreachable"], self.numbers()), (1, ["109", "110"]))

    def test_factsheet_number_is_set_to_the_row_number(self):
        self.row("110", ff_data={"group_vq77l17/Household_number": 109, "ff_uuid": "ff-1"})
        self.row("280", uuid="b", ff_data={"group_vq77l17/Household_number": "0280"})
        self.row("5", uuid="c", ff_data={"group_vq77l17/Household_number": "5"})
        counts = reconcile.run(apply=True, api=FakeApi({}), out=self.lines.append)
        self.assertEqual(counts["ff_number"], 2)
        inner = {r.household_number: r.ff_data["group_vq77l17/Household_number"] for r in HouseholdData.objects.all()}
        self.assertEqual(inner, {"110": "110", "280": "280", "5": "5"})
        self.assertEqual(HouseholdData.objects.get(household_number="110").ff_data["ff_uuid"], "ff-1")

    def test_command_defaults_to_a_dry_run(self):
        self.row("110", ff_data={"group_vq77l17/Household_number": 109})
        out = StringIO()
        call_command("reconcile_households", stdout=out)
        self.assertIn("re-run with --apply", out.getvalue())
        self.assertEqual(HouseholdData.objects.get().ff_data["group_vq77l17/Household_number"], 109)
