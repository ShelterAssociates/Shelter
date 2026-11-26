from django.test import SimpleTestCase

from plates.services import codes


class DigipinTests(SimpleTestCase):
    def test_india_post_examples_are_valid_and_round_trip(self):
        for code in ("C4P8K63M4M", "4P3JK852C9"):
            self.assertEqual(codes.clean_digipin(code), code)
            self.assertEqual(codes.encode_digipin(*codes.decode_digipin(code)), code)

    def test_encode_matches_the_approved_plate(self):
        self.assertEqual(codes.encode_digipin(16.6929355, 74.45952441), "4J6M8286K8")

    def test_hyphens_spaces_and_case_are_cleaned(self):
        self.assertEqual(codes.clean_digipin("372-8F3-7K28"), "3728F37K28")
        self.assertEqual(codes.clean_digipin(" 4j6 m828 6k8 "), "4J6M8286K8")

    def test_display_is_three_four_three(self):
        self.assertEqual(codes.display_digipin("4J6M8286K8"), "4J6 M828 6K8")

    def test_bad_characters_and_lengths_are_refused(self):
        for value in ("BAD-123", "4J6M8286K", "4J6M8286K81", "4J6M8286KA", "4J6M8286K0", "", None):
            with self.assertRaises(codes.CodeError):
                codes.clean_digipin(value)

    def test_points_outside_india_are_refused(self):
        with self.assertRaises(codes.CodeError):
            codes.encode_digipin(51.5, 0.12)


class PluscodeTests(SimpleTestCase):
    def test_ten_and_twelve_digit_codes(self):
        self.assertEqual(codes.clean_pluscode("7J8PMFV5+5R"), "7J8PMFV5+5R")
        self.assertEqual(codes.clean_pluscode(" 7j8pmfv5+5rch "), "7J8PMFV5+5RCH")

    def test_refused(self):
        for value in ("PMFV5+5R Ichalkaranji", "PMFV5+5RCH", "7J8PMFV5+5", "7J8PMFV5+5RCHX", "7J8PMFV55RCH",
                      "7J8PMFV5+5RCA", "7J8PMF00+", "7J8P MFV5+5RCH", ""):
            with self.assertRaises(codes.CodeError, msg=value):
                codes.clean_pluscode(value)
