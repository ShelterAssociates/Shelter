import io

from django.test import SimpleTestCase
from PIL import Image, ImageDraw

from plates.services import layout, linkpattern, textfit
from plates.services.render import PlateRenderer, is_dynamic, save_png, text_for
from plates.tests.support import RESOURCES, SLUM_60, preset, row, worst_row

PLATE_TYPES = ("digipin", "pluscode")
PANEL = {"on": True, "side": "right", "width_mm": 19.1, "style": "labelled", "fields": ["house_no", "slum"], "cut_line": True}


class RenderSizeTests(SimpleTestCase):
    def test_exact_pixel_size_and_dpi_in_png(self):
        for plate_type in PLATE_TYPES:
            for dpi, size in ((300, (1500, 450)), (600, (3000, 900))):
                image = PlateRenderer(preset(plate_type, dpi=dpi), RESOURCES).render(row(plate_type))
                self.assertEqual(image.size, size)
                self.assertEqual(image.mode, "RGB")
                buffer = io.BytesIO()
                save_png(image, buffer, dpi)
                saved = Image.open(io.BytesIO(buffer.getvalue()))
                self.assertAlmostEqual(saved.info["dpi"][0], dpi, places=1)

    def test_static_layer_is_drawn_once(self):
        renderer = PlateRenderer(preset("digipin"), RESOURCES)
        renderer.render(row("digipin"))
        first = renderer.static_layer()
        renderer.render(row("digipin", house_no="2"))
        self.assertIs(renderer.static_layer(), first)


class WorstCaseTests(SimpleTestCase):
    def test_worst_cases_fit_at_both_dpis(self):
        for plate_type in PLATE_TYPES:
            for dpi in (300, 600):
                spec = preset(plate_type, dpi=dpi)
                PlateRenderer(spec, RESOURCES).render(worst_row(plate_type))
                PlateRenderer(dict(spec, side_panel=PANEL), RESOURCES).render(worst_row(plate_type, slum=SLUM_60[:30]))

    def test_no_text_pixels_outside_their_boxes(self):
        for plate_type in PLATE_TYPES:
            for dpi in (300, 600):
                spec = preset(plate_type, dpi=dpi)
                renderer = PlateRenderer(spec, RESOURCES)
                for values in (row(plate_type), worst_row(plate_type)):
                    for element in renderer.elements:
                        if element["type"] == "text":
                            self.assert_ink_inside(renderer, element, text_for(element, values, spec))

    def assert_ink_inside(self, renderer, element, text):
        box = renderer.geometry.box(element["box"])
        canvas = Image.new("RGBA", renderer.geometry.size, (0, 0, 0, 0))
        fitted = renderer.fitter.fit(element, text, box, renderer.geometry.height)
        textfit.draw(ImageDraw.Draw(canvas), fitted, dict(element, colour="#FFFFFF"))
        ink = canvas.getchannel("A").getbbox()
        self.assertIsNotNone(ink, element["id"])
        self.assertTrue(layout.inside((ink[0], ink[1], ink[2] - ink[0], ink[3] - ink[1]), box), (element["id"], text, ink, box))

    def test_too_long_text_skips_the_row(self):
        renderer = PlateRenderer(preset("digipin"), RESOURCES)
        with self.assertRaises(textfit.TextDoesNotFit) as caught:
            renderer.render(row("digipin", slum=" ".join([SLUM_60] * 3)))
        self.assertEqual(str(caught.exception), "Text too long for slum")

    def test_empty_optional_text_draws_nothing(self):
        PlateRenderer(preset("digipin"), RESOURCES).render(row("digipin", slum=""))

    def test_long_slum_wraps_but_codes_never_do(self):
        renderer = PlateRenderer(preset("digipin"), RESOURCES)
        elements = {element["id"]: element for element in renderer.elements}
        slum = renderer.fitter.fit(elements["slum"], SLUM_60, renderer.geometry.box(elements["slum"]["box"]), 900)
        code = renderer.fitter.fit(elements["code"], "MMM MMMM MMM", renderer.geometry.box(elements["code"]["box"]), 900)
        self.assertEqual(len(slum.lines), 2)
        self.assertEqual(code.lines, ["MMM MMMM MMM"])


class HoleAndPanelTests(SimpleTestCase):
    def pixel_near_hole(self, spec, image):
        geometry = PlateRenderer(spec, RESOURCES).geometry
        edge, radius = geometry.mm(5), geometry.mm(4.5) // 2
        return image.getpixel((geometry.offset + edge + radius // 2, geometry.height // 2 + radius // 2))

    def test_holes_on_and_off(self):
        on = preset("digipin")
        off = preset("digipin", holes=dict(on["holes"], on=False))
        self.assertEqual(self.pixel_near_hole(on, PlateRenderer(on, RESOURCES).render(row())), (255, 255, 255))
        self.assertNotEqual(self.pixel_near_hole(off, PlateRenderer(off, RESOURCES).render(row())), (255, 255, 255))

    def test_corner_holes(self):
        spec = preset("digipin", holes={"on": True, "diameter_mm": 4.5, "edge_mm": 5, "position": "corners"})
        self.assertEqual(len(PlateRenderer(spec, RESOURCES).geometry.hole_centres()), 4)

    def test_side_panel_styles(self):
        fills = {"labelled": (255, 255, 255), "centred": (236, 236, 242), "old": (217, 218, 219)}
        for style, colour in fills.items():
            for side in ("right", "left"):
                spec = preset("digipin", side_panel=dict(PANEL, style=style, side=side))
                renderer = PlateRenderer(spec, RESOURCES)
                image = renderer.render(worst_row("digipin", slum=SLUM_60[:30]))
                self.assertEqual(image.size, (3000 + 451, 900))
                x = 3000 + 440 if side == "right" else 10
                self.assertEqual(image.getpixel((x, 890)), colour, (style, side))

    def test_side_panel_text_that_cannot_fit_skips_the_row(self):
        spec = preset("digipin", side_panel=PANEL)
        with self.assertRaises(textfit.TextDoesNotFit) as caught:
            PlateRenderer(spec, RESOURCES).render(row("digipin", house_no="W" * 60))
        self.assertIn("side panel house no", str(caught.exception))
        with self.assertRaises(textfit.TextDoesNotFit) as caught:
            PlateRenderer(spec, RESOURCES).render(row("digipin", slum=SLUM_60))
        self.assertIn("side panel slum", str(caught.exception))


class LayoutTests(SimpleTestCase):
    def problems(self, spec):
        return layout.problems(spec, linkpattern.worst_case_version(spec["qr_link_pattern"]))

    def test_presets_have_no_overlaps_and_clear_the_holes(self):
        for plate_type in PLATE_TYPES:
            for dpi in (300, 600):
                spec = preset(plate_type, dpi=dpi)
                self.assertEqual(self.problems(spec), [], (plate_type, dpi))

    def test_row_text_below_six_points_is_refused_fixed_text_keeps_its_approved_size(self):
        spec = preset("digipin")
        self.element(spec, "slum")["min_size"] = 0.03
        self.assertIn('"slum" can shrink below 6 pt when printed. Raise its smallest size.', self.problems(spec))
        self.assertFalse(any('"qr_caption"' in problem for problem in self.problems(spec)))

    def element(self, spec, element_id):
        return next(element for element in spec["elements"] if element["id"] == element_id)

    def test_overlap_is_refused(self):
        spec = preset("digipin")
        self.element(spec, "code")["box"][2] = 0.6
        self.assertTrue(any("overlaps" in problem and '"code"' in problem and '"qr_card"' in problem for problem in self.problems(spec)))

    def test_box_near_a_hole_or_edge_is_refused(self):
        spec = preset("digipin")
        self.element(spec, "badge")["box"][0] = 0.04
        found = " ".join(self.problems(spec))
        self.assertIn('"badge" is closer than 1.5 mm to a drill hole', found)
        self.element(spec, "badge")["box"][0] = 0.001
        self.assertIn('"badge" is closer than 1.5 mm to the plate edge', " ".join(self.problems(spec)))

    def test_small_qr_and_missing_quiet_zone_are_refused(self):
        spec = preset("digipin")
        qr_element = self.element(spec, "qr")
        qr_element["box"] = [0.74, 0.2, 0.03, 0.1]
        self.assertTrue(any("smaller than 15 mm" in problem for problem in self.problems(spec)))
        spec = preset("digipin")
        self.element(spec, "qr")["box"] = list(self.element(spec, "qr_card")["box"])
        self.assertTrue(any("blank margin of 2 modules" in problem for problem in self.problems(spec)))

    def test_child_must_stay_inside_its_card(self):
        spec = preset("digipin")
        self.element(spec, "ip_logo")["box"][0] = 0.6
        self.assertTrue(any('"ip_logo" sticks out of "ip_card"' in problem for problem in self.problems(spec)))

    def test_dynamic_elements(self):
        spec = preset("digipin")
        dynamic = sorted(element["id"] for element in spec["elements"] if is_dynamic(element))
        self.assertEqual(dynamic, ["code", "qr", "slum"])
