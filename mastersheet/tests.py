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


CTB_A = {
    "ctb name": "CTB A",
    "is_the_CTB_in_use": "Yes",
    "number_of_seats_allotted_to_me": "6",
}
CTB_B = {"ctb name": "CTB B", "is_the_CTB_in_use": "Closed"}
TOILET_COMMENT_ENTRY = {"toilet_comment": "No CTB in this slum"}
RIM_DATA = {
    "General": {"landmark": "Old temple"},
    "Toilet": [TOILET_COMMENT_ENTRY, CTB_A, CTB_B],
}


def rim_slum():
    city = SimpleNamespace(name=SimpleNamespace(city_name="Pune"))
    return SimpleNamespace(
        name="Slum One",
        shelter_slum_code="S-1",
        electoral_ward=SimpleNamespace(
            administrative_ward=SimpleNamespace(city=city)
        ),
    )


def rim_patches(rim_data):
    """Patches the one SlumData row (and an absent appraisal) the builders read."""
    row = SimpleNamespace(
        rim_data=rim_data,
        submission_date=datetime.datetime(2026, 1, 2),
        modified_on=datetime.datetime(2026, 3, 4),
    )
    return patch.multiple(
        "mastersheet.views",
        SlumData=MagicMock(
            **{"objects.filter.return_value.order_by.return_value.first.return_value": row}
        ),
        Rapid_Slum_Appraisal=MagicMock(
            **{"objects.filter.return_value.first.return_value": None}
        ),
    )


class CtbEntriesTests(SimpleTestCase):
    """A Toilet entry is a toilet block only if it carries a "ctb name"; the
    RIM registration form's slum-level comment entry is not one."""

    def test_general_form_comment_alone_is_not_a_ctb(self):
        from mastersheet.views import _count_ctbs
        self.assertEqual(_count_ctbs({"Toilet": [TOILET_COMMENT_ENTRY]}), 0)

    def test_comment_skipped_and_named_blocks_counted_in_order(self):
        from mastersheet.views import _count_ctbs, ctb_entries
        self.assertEqual(_count_ctbs(RIM_DATA), 2)
        self.assertEqual(
            [entry["ctb name"] for entry in ctb_entries(RIM_DATA)], ["CTB A", "CTB B"]
        )

    def test_entry_with_answers_but_no_name_does_not_count(self):
        # Legacy Kobo-era entries carry real answers but no "ctb name".
        from mastersheet.views import _count_ctbs
        self.assertEqual(_count_ctbs({"Toilet": [{"is_the_CTB_in_use": "Closed"}]}), 0)

    def test_repeated_name_counts_once(self):
        from mastersheet.views import _count_ctbs
        self.assertEqual(_count_ctbs({"Toilet": [CTB_A, dict(CTB_A)]}), 1)

    def test_blank_name_does_not_count(self):
        from mastersheet.views import _count_ctbs
        self.assertEqual(_count_ctbs({"Toilet": [{"ctb name": ""}]}), 0)

    def test_missing_or_malformed_toilet_section(self):
        from mastersheet.views import _count_ctbs
        for rim_data in (None, {}, {"Toilet": None}, {"Toilet": "x"}, {"Toilet": [None, 7]}):
            self.assertEqual(_count_ctbs(rim_data), 0, rim_data)


class SlumToiletCommentTests(SimpleTestCase):
    def test_taken_from_the_entry_without_a_ctb_name(self):
        from mastersheet.views import slum_toilet_comment
        self.assertEqual(
            slum_toilet_comment([TOILET_COMMENT_ENTRY, CTB_A]), "No CTB in this slum"
        )

    def test_a_comment_on_a_named_block_is_not_the_slum_comment(self):
        from mastersheet.views import slum_toilet_comment
        self.assertIsNone(slum_toilet_comment([dict(CTB_A, toilet_comment="block note")]))

    def test_none_when_absent(self):
        from mastersheet.views import slum_toilet_comment
        for entries in ([CTB_A], [], None, "x"):
            self.assertIsNone(slum_toilet_comment(entries), entries)

    def test_blank_comment_is_still_a_value(self):
        # "" is an answered-but-empty note; only a missing key means no column.
        from mastersheet.views import slum_toilet_comment
        self.assertEqual(slum_toilet_comment([{"toilet_comment": ""}]), "")


class RimSummaryCsvTests(SimpleTestCase):
    def test_toilet_section_contributes_only_the_slum_comment(self):
        from mastersheet.views import _build_rim_csv_rows
        with rim_patches(RIM_DATA):
            rows = _build_rim_csv_rows([rim_slum()], ["General", "Toilet"])

        groups, fields, data = rows
        # Toilet sits right after General, per RIM_SECTION_ORDER.
        self.assertEqual(groups[6:], ["General", "Toilet"])
        self.assertEqual(fields[6:], ["landmark", "toilet_comment"])
        self.assertEqual(data[5], 2)  # Number of CTBs
        self.assertEqual(data[6:], ["Old temple", "No CTB in this slum"])

    def test_toilet_column_absent_when_section_not_selected(self):
        from mastersheet.views import _build_rim_csv_rows
        with rim_patches(RIM_DATA):
            rows = _build_rim_csv_rows([rim_slum()], ["General"])

        self.assertNotIn("toilet_comment", rows[1])
        self.assertEqual(rows[2][5], 2)  # the count column is always included

    def test_no_column_when_the_slum_has_no_comment_entry(self):
        from mastersheet.views import _build_rim_csv_rows
        with rim_patches({"General": {"landmark": "X"}, "Toilet": [CTB_A]}):
            rows = _build_rim_csv_rows([rim_slum()], ["General", "Toilet"])

        self.assertNotIn("toilet_comment", rows[1])


class RimToiletCsvTests(SimpleTestCase):
    def test_only_named_blocks_become_rows_renumbered_from_one(self):
        from mastersheet.views import _build_rim_toilet_csv_rows
        with rim_patches(RIM_DATA):
            rows = _build_rim_toilet_csv_rows([rim_slum()])

        self.assertEqual(rows[0][:4], ["Slum Name", "Slum Code", "CTB #", "ctb name"])
        self.assertNotIn("toilet_comment", rows[0])
        self.assertEqual([row[2] for row in rows[1:]], [1, 2])
        self.assertEqual([row[3] for row in rows[1:]], ["CTB A", "CTB B"])

    def test_comment_only_slum_produces_no_rows(self):
        from mastersheet.views import _build_rim_toilet_csv_rows
        with rim_patches({"Toilet": [TOILET_COMMENT_ENTRY]}):
            rows = _build_rim_toilet_csv_rows([rim_slum()])

        self.assertEqual(len(rows), 1)  # header only

    def test_row_count_matches_the_summary_csv_count(self):
        from mastersheet.views import _build_rim_csv_rows, _build_rim_toilet_csv_rows
        with rim_patches(RIM_DATA):
            summary = _build_rim_csv_rows([rim_slum()], ["Toilet"])
            toilet_rows = _build_rim_toilet_csv_rows([rim_slum()])

        self.assertEqual(summary[2][5], len(toilet_rows) - 1)
