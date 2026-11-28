"""How the map splits a stored answer into the values its filters count."""

from django.test import SimpleTestCase

from component.kobotoolbox import answer_parts


class AnswerPartsTests(SimpleTestCase):
    def test_multi_answer_text_is_split_and_trimmed(self):
        self.assertEqual(answer_parts("Individual connection, None", set()), ["Individual connection", "None"])

    def test_a_whole_answer_a_filter_names_is_kept_whole(self):
        whole = {"Partial use- children, women, elderly"}
        self.assertEqual(answer_parts("Partial use- children, women, elderly", whole),
                         ["Partial use- children, women, elderly"])

    def test_list_answers_are_used_as_they_are(self):
        self.assertEqual(answer_parts(["A", "B"], set()), ["A", "B"])

    def test_single_answer(self):
        self.assertEqual(answer_parts("Own toilet", set()), ["Own toilet"])



class HomeWithShopTests(SimpleTestCase):
    def test_home_with_shop_counts_under_the_occupancy_filter(self):
        from component.kobotoolbox import occupancy_values

        record = {"Type_of_structure_occupancy": "Occupied house", "Functioning of the structure": "Individual home + shop"}
        self.assertEqual(occupancy_values(record), ["Occupied house", "Individual home + shop"])

    def test_other_households_count_once(self):
        from component.kobotoolbox import occupancy_values

        self.assertEqual(occupancy_values({"Type_of_structure_occupancy": "Shop"}), ["Shop"])
