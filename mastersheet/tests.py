import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from mastersheet.views import AnalyseGisTabData, allocate_paise, allocate_whole_rupees


class AllocateWholeRupeesTests(TestCase):
    """Tests for the transport/loading-charge per-household split used by
    accounts_excel_generation. The bug this guards against: dividing a whole
    rupee figure (e.g. 2500) across N households and rounding each share to
    2 decimals independently causes the rows to sum to something like
    2499.94 instead of 2500. allocate_whole_rupees must always return N
    plain integers that sum back to the (rounded) total exactly.
    """

    def test_reported_bug_example_2500_over_37_households(self):
        # The maintainer's own worked example: 2500 // 37 = 67 remainder 21,
        # so the first 21 households get 68 and the remaining 16 get 67.
        result = allocate_whole_rupees(2500, 37)
        self.assertEqual(len(result), 37)
        self.assertEqual(sum(result), 2500)
        self.assertEqual(result[:21], [68] * 21)
        self.assertEqual(result[21:], [67] * 16)

    def test_evenly_divisible_total_gives_equal_shares(self):
        result = allocate_whole_rupees(3700, 37)
        self.assertEqual(result, [100] * 37)
        self.assertEqual(sum(result), 3700)

    def test_single_household_gets_full_amount(self):
        result = allocate_whole_rupees(2500, 1)
        self.assertEqual(result, [2500])

    def test_zero_charge_gives_all_zero_shares(self):
        result = allocate_whole_rupees(0, 37)
        self.assertEqual(result, [0] * 37)
        self.assertEqual(sum(result), 0)

    def test_more_households_than_rupees_still_sums_exactly(self):
        # 5 rupees across 8 households: 5 households get 1, 3 get 0.
        result = allocate_whole_rupees(5, 8)
        self.assertEqual(len(result), 8)
        self.assertEqual(sum(result), 5)
        self.assertEqual(sorted(result, reverse=True), [1, 1, 1, 1, 1, 0, 0, 0])

    def test_float_total_is_rounded_to_nearest_rupee_before_splitting(self):
        # A stray-paise DB value (e.g. legacy data) should not leak paise
        # into the export - it gets rounded to a whole rupee first.
        result = allocate_whole_rupees(2500.49, 37)
        self.assertEqual(sum(result), 2500)  # rounds down to 2500

        result = allocate_whole_rupees(2500.5, 37)
        self.assertEqual(sum(result), 2500)  # banker's rounding: 2500.5 -> 2500

        result = allocate_whole_rupees(2500.51, 37)
        self.assertEqual(sum(result), 2501)  # rounds up to 2501

    def test_all_shares_are_plain_ints_not_floats(self):
        result = allocate_whole_rupees(2500, 37)
        for share in result:
            self.assertIsInstance(share, int)

    def test_remainder_of_zero_gives_no_extra_rupee_to_any_row(self):
        result = allocate_whole_rupees(74, 37)
        self.assertEqual(result, [2] * 37)

    def test_large_household_count_still_reconciles(self):
        result = allocate_whole_rupees(2500, 999)
        self.assertEqual(len(result), 999)
        self.assertEqual(sum(result), 2500)
        # base share is 2 (2500 // 999 = 2), remainder is 502
        self.assertEqual(result[:502], [3] * 502)
        self.assertEqual(result[502:], [2] * 497)

    def test_matches_manual_divmod_reasoning_for_arbitrary_values(self):
        # Property-style check across a spread of totals/counts: the
        # allocation must always sum exactly to the rounded total, and no
        # two shares should differ by more than 1 rupee.
        cases = [(1, 3), (2, 3), (100, 3), (999, 13), (1, 1), (0, 1), (7, 7)]
        for total, count in cases:
            with self.subTest(total=total, count=count):
                result = allocate_whole_rupees(total, count)
                self.assertEqual(len(result), count)
                self.assertEqual(sum(result), round(total))
                self.assertLessEqual(max(result) - min(result), 1)


class AllocatePaiseTests(TestCase):
    """Tests for the material-line (InvoiceItems.total) per-household split
    used by accounts_excel_generation's Amount column. Unlike transport /
    loading charges, a material line's total can legitimately be fractional
    (quantity x a fractional rate), so this must reconcile exactly to the
    paisa rather than being forced to a whole rupee.
    """

    def test_fractional_total_over_households_reconciles_to_the_paisa(self):
        # 37.50 across 3 households: 12.50 each, divides evenly.
        result = allocate_paise(37.50, 3)
        self.assertEqual(result, [12.5, 12.5, 12.5])
        self.assertAlmostEqual(sum(result), 37.50, places=2)

    def test_non_evenly_divisible_fractional_total(self):
        # This is the material-cost analogue of the reported transport-charge
        # bug: 5000 / 13 = 384.615..., independent per-row rounding used to
        # sum to 4999.99. allocate_paise must sum to exactly 5000.00.
        result = allocate_paise(5000, 13)
        self.assertEqual(len(result), 13)
        self.assertAlmostEqual(sum(result), 5000.00, places=2)
        # base paisa share is floor(500000/13)=38461 paise=384.61, remainder 7
        self.assertEqual(result[:7], [384.62] * 7)
        self.assertEqual(result[7:], [384.61] * 6)

    def test_single_household_gets_full_amount_incl_paise(self):
        result = allocate_paise(384.61, 1)
        self.assertEqual(result, [384.61])

    def test_zero_total_gives_all_zero_shares(self):
        result = allocate_paise(0, 5)
        self.assertEqual(result, [0.0] * 5)

    def test_shares_are_rounded_to_the_nearest_paisa(self):
        # Sub-paisa float noise in the source value must not leak through.
        self.assertEqual(allocate_paise(10.004, 1), [10.0])
        self.assertEqual(allocate_paise(10.006, 1), [10.01])

    def test_property_sum_always_reconciles_to_nearest_paisa(self):
        cases = [(37.5, 3), (5000, 13), (0.01, 3), (999.99, 7), (100, 1)]
        for total, count in cases:
            with self.subTest(total=total, count=count):
                result = allocate_paise(total, count)
                self.assertEqual(len(result), count)
                self.assertAlmostEqual(sum(result), round(total * 100) / 100, places=2)
                self.assertLessEqual(round((max(result) - min(result)) * 100), 1)


SLUM = (5, "Test Slum", "Testville")


def household(number):
    return SimpleNamespace(
        household_number=number,
        rhs_data={"Type_of_structure_occupancy": "Occupied house"},
        ff_data=None,
        submission_date=datetime.datetime(2026, 1, 1),
    )


def toilet(number, status):
    return SimpleNamespace(household_number=number, status=status, pocket=None, comment=None)


class AnalyseGisTabDataTests(SimpleTestCase):
    """Kobo-era '0022A' and Avni-era '22A' are the same house."""

    def run_with(self, households, toilets):
        patches = {
            "Slum": {"objects.filter.return_value.values_list.return_value": [SLUM]},
            "SponsorProjectDetails": {"objects.filter.return_value.exclude.return_value": []},
            "ToiletConstruction": {"objects.filter.return_value.exclude.return_value": toilets},
            "HouseholdData": {"objects.filter.return_value": households},
            "FollowupData": {"objects.filter.return_value.values.return_value": []},
            "communityActivityData": {"return_value": {}},
        }
        with patch.multiple(
            "mastersheet.views", **{k: MagicMock(**v) for k, v in patches.items()}
        ), patch("mastersheet.views.ToiletConstruction.get_status_display", lambda s: "Completed"):
            return AnalyseGisTabData(SLUM[0])[0]

    def test_zero_padded_and_plain_spellings_collapse_to_one_row(self):
        rows = self.run_with([household("0022A"), household("22A")], [toilet("22A", "6")])

        self.assertEqual([r["household_number"] for r in rows], ["22A"])
        self.assertEqual(rows[0]["final_status"], "Completed")


class FactsheetByHouseholdTests(SimpleTestCase):
    """FF data is keyed by the row it is stored on, not by the number typed inside the form."""

    def record(self, number, ff_data):
        return SimpleNamespace(household_number=number, ff_data=ff_data)

    def test_keyed_by_the_row_number_even_when_the_form_says_otherwise(self):
        from mastersheet.views import factsheet_by_household
        rows = factsheet_by_household([
            self.record("110", {"group_vq77l17/Household_number": 109, "ff_uuid": "ff-1", "ignored": 1}),
        ])
        self.assertEqual(list(rows), ["110"])
        self.assertEqual(rows["110"]["ff_uuid"], "ff-1")
        self.assertNotIn("ignored", rows["110"])

    def test_rows_without_factsheet_are_left_out_and_numbers_are_normalised(self):
        from mastersheet.views import factsheet_by_household
        rows = factsheet_by_household([
            self.record("0042", {"group_ne3ao98/Use_of_toilet": "Yes"}),
            self.record("43", None),
            self.record("44", {}),
        ])
        self.assertEqual(list(rows), ["42"])
