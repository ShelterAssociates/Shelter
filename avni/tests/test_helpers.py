"""Pure helpers shared by the sync modules: API paths, windows, key maps."""

from datetime import date, datetime

from django.test import SimpleTestCase

from avni import mappings, paths, watermark


class PathTests(SimpleTestCase):
    def test_subjects_path_quotes_values(self):
        path = paths.subjects("Slum-RIM Registration", "2021-10-31T01:30:00.000Z", location_uuid="abc")
        self.assertEqual(
            path,
            "api/subjects?lastModifiedDateTime=2021-10-31T01%3A30%3A00.000Z"
            "&subjectType=Slum-RIM%20Registration&locationIds=abc",
        )

    def test_encounter_list_paths(self):
        self.assertEqual(
            paths.encounters("Property tax", "2026-01-01T00:00:00.000Z"),
            "api/encounters?lastModifiedDateTime=2026-01-01T00%3A00%3A00.000Z&encounterType=Property%20tax",
        )
        self.assertTrue(paths.program_encounters("Daily Reporting", "x").startswith("api/programEncounters?"))

    def test_single_entity_paths(self):
        self.assertEqual(paths.subject("u1"), "api/subject/u1")
        self.assertEqual(paths.encounter("u1"), "api/encounter/u1")
        self.assertEqual(paths.program_encounter("u1"), "api/programEncounter/u1")
        self.assertEqual(paths.program_enrolment("u1"), "api/programEnrolment/u1")


class WatermarkTests(SimpleTestCase):
    def test_format_accepts_date_datetime_and_string(self):
        expected = "2026-03-05T00:00:00.000Z"
        self.assertEqual(watermark.format_from_date(date(2026, 3, 5)), expected)
        self.assertEqual(watermark.format_from_date(datetime(2026, 3, 5, 14, 2)), expected)
        self.assertEqual(watermark.format_from_date("2026-03-05"), expected)

    def test_full_iso_string_passes_through(self):
        self.assertEqual(watermark.format_from_date(watermark.EPOCH), watermark.EPOCH)

    def test_window_start_prefers_explicit_from_date(self):
        self.assertEqual(watermark.window_start(from_date="2026-03-05"), "2026-03-05T00:00:00.000Z")

    def test_day_before(self):
        self.assertEqual(watermark.day_before(datetime(2026, 3, 5, 9, 0)), "2026-03-04T00:00:00.000Z")


class HouseholdNumberTests(SimpleTestCase):
    def test_digits_lose_leading_zeros(self):
        self.assertEqual(mappings.household_number_from("0042"), "42")
        self.assertEqual(mappings.household_number_from(42.0), "42")

    def test_alphanumeric_keeps_suffix(self):
        self.assertEqual(mappings.household_number_from("0022A"), "22A")
        self.assertEqual(mappings.household_number_from("123A"), "123A")

    def test_blank(self):
        self.assertEqual(mappings.household_number_from(None), "")


class RhsKeyMapTests(SimpleTestCase):
    def test_incoming_concepts_are_renamed_to_rhs_keys(self):
        merged = mappings.merge_rhs_keys({}, {"First name": "12", "Aadhaar number": "x"})
        self.assertEqual(merged["Household_number"], "12")
        self.assertEqual(merged["group_el9cl08/Aadhar_number"], "x")

    def test_shop_drops_shop_only_questions(self):
        existing = {"Type_of_structure_occupancy": "Shop", "Type of shop": "Kirana"}
        merged = mappings.merge_rhs_keys(existing, {})
        self.assertNotIn("Type of shop", merged)

    def test_unoccupied_drops_parent_household(self):
        existing = {"Type_of_structure_occupancy": "Unoccupied house", "Parent_household_number": "3"}
        merged = mappings.merge_rhs_keys(existing, {})
        self.assertNotIn("Parent_household_number", merged)


class FactsheetKeyMapTests(SimpleTestCase):
    def test_multiselect_joined_under_rhs_key(self):
        mapped = mappings.map_factsheet_keys({"Use of toilet": ["Men", "Women"], "Note": "n"})
        self.assertEqual(mapped["group_ne3ao98/Use_of_toilet"], "Men,Women")
        self.assertEqual(mapped["Note"], "n")

    def test_unknown_keys_pass_through(self):
        self.assertEqual(mappings.map_factsheet_keys({"Brand new": 1}), {"Brand new": 1})


class SanitationKeyMapTests(SimpleTestCase):
    def test_renames_and_keeps_others(self):
        mapped = mappings.map_sanitation_keys({"Status of toilet under SBM ?": "Done", "Other": 1})
        self.assertEqual(mapped["group_oi8ts04/Status_of_toilet_under_SBM"], "Done")
        self.assertNotIn("Status of toilet under SBM ?", mapped)
        self.assertEqual(mapped["Other"], 1)


class OverrideTests(SimpleTestCase):
    def test_toilet_at_home_sets_own_toilet(self):
        data = mappings.apply_household_overrides({"Do you have a toilet at home?": "Yes"})
        self.assertEqual(data["Current place of defecation"], "Own toilet")

    def test_own_house_shop_normalised(self):
        data = mappings.apply_household_overrides({"Ownership status of the house_1": "Own house/Shop"})
        self.assertEqual(data["Ownership status of the house_1"], "Own house")

    def test_functioning_shop_becomes_occupancy(self):
        data = mappings.normalize_occupancy({"Functioning of the structure": "Shop"})
        self.assertEqual(data, {"Type_of_structure_occupancy": "Shop"})
