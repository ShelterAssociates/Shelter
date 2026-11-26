import datetime
from unittest import mock

from django.test import SimpleTestCase, override_settings

from plates.services import linkpattern, naming, qr
from plates.services.render import PlateRenderer
from plates.tests.support import RESOURCES, preset, row

HOSTS = ["dac.indiapost.gov.in", "www.google.com"]


@override_settings(PLATES_QR_ALLOWED_HOSTS=HOSTS)
class LinkPatternTests(SimpleTestCase):
    def test_starting_patterns_are_accepted(self):
        for _, pattern in linkpattern.STARTING_PATTERNS:
            self.assertEqual(linkpattern.problems(pattern), [], pattern)

    def test_fill_url_encodes_every_value(self):
        link = linkpattern.fill("https://www.google.com/maps/search/?api=1&query={pluscode}", {"pluscode": "7J8PMFV5+5RCH"})
        self.assertEqual(link, "https://www.google.com/maps/search/?api=1&query=7J8PMFV5%2B5RCH")
        self.assertEqual(linkpattern.fill("https://www.google.com/x/{slum}", {"slum": "A&B /C"}), "https://www.google.com/x/A%26B%20%2FC")

    def test_other_host_refused(self):
        self.assertIn("may only point to", linkpattern.problems("https://evil.example.com/{digipin}")[0])
        self.assertIn("may only point to", linkpattern.problems("https://www.google.com.evil.io/{digipin}")[0])

    def test_http_refused(self):
        self.assertIn("https://", linkpattern.problems("http://www.google.com/maps/place/{lat},{long}")[0])

    def test_unknown_variable_refused(self):
        self.assertIn("{secret}", linkpattern.problems("https://www.google.com/{secret}")[0])

    def test_variable_the_plate_type_does_not_have_is_refused(self):
        self.assertIn("DIGIPIN plates have no {pluscode}", linkpattern.problems("https://www.google.com/maps/search/?api=1&query={pluscode}", "digipin")[0])
        self.assertEqual(linkpattern.problems("https://www.google.com/maps/search/?api=1&query={pluscode}", "pluscode"), [])

    def test_stray_brace_refused(self):
        self.assertIn("{ or }", linkpattern.problems("https://www.google.com/{digipin")[0])

    def test_worst_case_fits_a_qr(self):
        self.assertLessEqual(linkpattern.worst_case_version(linkpattern.DEFAULT_PATTERNS["digipin"]), 10)


class QrTests(SimpleTestCase):
    def test_data_passed_to_qrcode_is_the_filled_link(self):
        for plate_type, expected in (("digipin", "https://dac.indiapost.gov.in/mydigipin/home/4J6M8286K8"),
                                     ("pluscode", "https://www.google.com/maps/place/16.6929355,74.45952441")):
            renderer = PlateRenderer(preset(plate_type), RESOURCES)
            with mock.patch.object(qr.qrcode.QRCode, "add_data", autospec=True, wraps=qr.qrcode.QRCode.add_data) as add:
                renderer.render(row(plate_type))
            self.assertEqual([call[0][1] for call in add.call_args_list], [expected])

    def test_image_size_and_crisp_modules(self):
        image = qr.qr_image("https://dac.indiapost.gov.in/mydigipin/home/4J6M8286K8", 528, "#2A2468", "#FFFFFF")
        self.assertEqual(image.size, (528, 528))
        self.assertLessEqual(len(image.getcolors()), 2)


class NamingTests(SimpleTestCase):
    def test_plate_names(self):
        self.assertEqual(naming.plate_base_name("4J6 M828 6K8", "1"), "4J6M8286K8_1")
        self.assertEqual(naming.plate_base_name("7J8PMFV5+5RCH", "1"), "7J8PMFV5+5RCH_1")

    def test_unsafe_characters(self):
        self.assertEqual(naming.clean('a/b\\c:d*e?f"g<h>i|j'), "a-b-c-d-e-f-g-h-i-j")
        self.assertEqual(naming.clean("a//\x00b"), "a-b")
        self.assertEqual(naming.clean("../../etc"), "etc")
        self.assertEqual(naming.clean("..hidden"), "hidden")
        self.assertEqual(naming.clean("-x"), "x")
        self.assertEqual(len(naming.clean("x" * 300)), 120)
        self.assertEqual(naming.clean("  "), "plate")

    def test_duplicates_get_numbers(self):
        names = naming.UniqueNames()
        self.assertEqual([names.take("4J6M8286K8_1") for _ in range(3)], ["4J6M8286K8_1.png", "4J6M8286K8_1_2.png", "4J6M8286K8_1_3.png"])
        self.assertEqual(names.take("4j6m8286k8_1"), "4j6m8286k8_1_4.png")

    def test_zip_name(self):
        self.assertEqual(naming.zip_name("Nimajga Mal", "digipin", datetime.date(2026, 11, 27), 418),
                         "nimajga-mal_digipin_2026-11-27_batch-418.zip")
