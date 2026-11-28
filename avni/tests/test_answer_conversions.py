"""AVNI answers converted to the answers the map filters (component Metadata codes) look for."""

from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from avni import mappings
from avni.sync import encounters, households, structures
from avni.tests.support import make_city, make_slum, subject_record
from graphs.models import HouseholdData

WATER = "group_el9cl08/Type_of_water_connection"
TOILET = "group_oi8ts04/Current_place_of_defecation"
OD = "group_oi8ts04/OD1"
CONNECTED = "group_oi8ts04/What_is_the_toilet_connected_to"
OCCUPANCY = "Type_of_structure_occupancy"


class ConvertAnswersTests(SimpleTestCase):
    def test_each_confirmed_answer_is_converted(self):
        cases = [
            (WATER, "Group connection", "Group connection (paid by all users)"),
            (WATER, "Borewell/Submersible", "Borewell"),
            (CONNECTED, "Biogas", "Individual bio-gas"),
            (OD, "only children", "Only children"),
            (OD, "only men", "Only men"),
            (OD, "only women", "Only women"),
            (TOILET, "Toilet by SA ", "Toilet by SA"),
            (TOILET, "Toilet by sa ", "Toilet by SA"),
            (TOILET, "HHs Use CTB of neighbouring slum", "Use CTB of neighbouring slum"),
            (TOILET, "Toilet by other NGO / Agency", "Toilet by other NGO"),
            (TOILET, "No household toilet", "No Toilet"),
        ]
        for key, avni, ours in cases:
            with self.subTest(avni=avni):
                self.assertEqual(mappings.convert_answers({key: avni})[key], ours)

    def test_each_part_of_a_multi_answer_is_converted(self):
        self.assertEqual(mappings.convert_answers({WATER: "Individual connection, Group connection"})[WATER],
                         "Individual connection, Group connection (paid by all users)")
        self.assertEqual(mappings.convert_answers({WATER: ["Group connection", "Hand pump"]})[WATER],
                         ["Group connection (paid by all users)", "Hand pump"])

    def test_other_answers_and_keys_are_left_alone(self):
        data = {WATER: "Hand pump", TOILET: "Own toilet", "Other": "Group connection"}
        self.assertEqual(mappings.convert_answers(dict(data)), data)

    def test_home_with_shop_becomes_the_occupancy(self):
        data = mappings.convert_answers({"Functioning of the structure": "Individual home + shop", OCCUPANCY: "Occupied house"})
        self.assertEqual(data[OCCUPANCY], "Individual home + shop")
        self.assertEqual(data["Functioning of the structure"], "Individual home + shop")

    def test_converting_twice_changes_nothing_more(self):
        once = mappings.convert_answers({TOILET: "Toilet by sa ", WATER: "Group connection"})
        self.assertEqual(mappings.convert_answers(dict(once)), once)


class WritersConvertTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def row(self):
        return HouseholdData.objects.get().rhs_data

    def test_household_registration_is_converted(self):
        households.save_household(subject_record(observations={"Water Sub Category": "Group connection"}))
        self.assertEqual(self.row()[WATER], "Group connection (paid by all users)")

    def test_household_update_is_converted(self):
        households.save_household(subject_record())
        households.save_household(subject_record(observations={"Current place of defecation": "Toilet by sa "},
                                                 modified="2026-10-01T00:00:00.000Z"))
        self.assertEqual(self.row()[TOILET], "Toilet by SA")

    def test_structure_survey_is_converted(self):
        record = subject_record(subject_type="Detailed Socio Economic Survey",
                                observations={"Final current place of defecation": "No household toilet"})
        structures.save_structure_record(record)
        self.assertEqual(self.row()[TOILET], "No Toilet")

    def test_form_answers_merged_into_a_household_are_converted(self):
        households.save_household(subject_record())
        households.merge_into_rhs_data(households.household_from_record(subject_record()), {OD: "only women"})
        self.assertEqual(self.row()[OD], "Only women")


class ConvertStoredAnswersCommandTests(TestCase):
    def setUp(self):
        city = make_city()
        self.row = HouseholdData.objects.create(household_number="42", slum=make_slum(city), city=city,
                                                submission_date="2026-01-01T00:00:00Z",
                                                rhs_data={TOILET: "No household toilet", WATER: "Hand pump"})

    def test_dry_run_changes_nothing(self):
        out = StringIO()
        call_command("convert_household_answers", stdout=out)
        self.row.refresh_from_db()
        self.assertEqual(self.row.rhs_data[TOILET], "No household toilet")
        self.assertIn("1 household", out.getvalue())

    def test_apply_converts_stored_answers(self):
        call_command("convert_household_answers", apply=True, stdout=StringIO())
        self.row.refresh_from_db()
        self.assertEqual(self.row.rhs_data[TOILET], "No Toilet")
        self.assertEqual(self.row.rhs_data[WATER], "Hand pump")
