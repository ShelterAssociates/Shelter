"""render(template, row) -> PIL image. DesignRenderer keeps the parts that never change per row (one per batch)."""

from PIL import ImageDraw

from design_studio.services import drawing, linkpattern, panel, qr, textfit
from design_studio.services.layout import Geometry
from design_studio.services.resources import Resources

STATIC_SOURCES = ("fixed", "qr_caption")
CODE_SOURCES = ("digipin", "digipin_display", "pluscode")


def is_dynamic(element):
    if element.get("type") == "qr":
        return True
    return element.get("type") == "text" and element.get("source", "fixed") not in STATIC_SOURCES


def text_for(element, row, spec):
    """The text an element prints for a row."""
    source = element.get("source", "fixed")
    if source == "fixed":
        text = element.get("text", "")
    elif source == "qr_caption":
        text = spec.get("qr_caption", "")
    elif source == "slum":
        slum = str(row.get("slum") or "").strip()
        text = slum + spec.get("slum_suffix", "") if slum else ""
    else:
        text = str(row.get(source) or "")
    return text.upper() if element.get("uppercase") else text


class DesignRenderer(object):
    def __init__(self, spec, resources=None):
        self.spec = spec
        self.resources = resources or Resources.from_database()
        self.geometry = Geometry(spec)
        self.fitter = textfit.TextFitter(self.resources)
        self.elements = sorted(spec.get("elements") or [], key=lambda element: element.get("z", 0))
        self.static = None

    def length(self, fraction):
        return self.geometry.length(fraction)

    def static_layer(self):
        if self.static is None:
            self.static = self.draw_static()
        return self.static

    def draw_static(self):
        geometry, settings = self.geometry, self.spec.get("background") or {}
        area = (geometry.offset, 0, geometry.width, geometry.height)
        canvas = drawing.fill(geometry.size, {"fill": "none"})
        if self.spec.get("mode") == "image" and self.spec.get("background_image"):
            plate = drawing.cover(self.resources.image(self.spec["background_image"]), (geometry.width, geometry.height))
        else:
            plate = drawing.fill((geometry.width, geometry.height), settings)
        canvas.alpha_composite(plate, (geometry.offset, 0))
        if (settings.get("grid") or {}).get("on"):
            drawing.grid(canvas, area, settings["grid"])
        if (settings.get("border") or {}).get("on"):
            drawing.border(canvas, area, settings["border"], self.length)
        if (settings.get("strip") or {}).get("on"):
            drawing.strip(canvas, area, settings["strip"], self.length)
        for element in self.elements:
            if not is_dynamic(element):
                self.draw_element(canvas, element, {})
        drawing.holes(canvas, geometry)
        if geometry.panel_on:
            panel.draw_static(canvas, geometry, self.spec["side_panel"], self.resources)
        return canvas

    def draw_element(self, canvas, element, row):
        kind, box = element.get("type"), self.geometry.box(element["box"])
        if kind == "text":
            text = text_for(element, row, self.spec)
            if text:
                fitted = self.fitter.fit(element, text, box, self.geometry.height)
                textfit.draw(ImageDraw.Draw(canvas), fitted, element)
        elif kind == "qr":
            side = min(box[2], box[3])
            image = qr.qr_image(self.link(row), side, element.get("fg", "#000000"), element.get("bg", "#FFFFFF"), int(element.get("quiet_zone", 0)))
            canvas.paste(image, (box[0] + (box[2] - side) // 2, box[1] + (box[3] - side) // 2))
        elif kind == "card":
            drawing.card(canvas, element, box, self.length)
        elif kind == "badge":
            drawing.badge(canvas, element, box, self.length, self.resources)
        elif kind == "image":
            drawing.picture(canvas, element, box, self.resources)
        elif kind == "line":
            drawing.line(canvas, element, box, self.length)

    def link(self, row):
        return linkpattern.fill(self.spec.get("qr_link_pattern", ""), row)

    def code_width(self, row):
        """Width of the row's code at its largest size, to pick the widest-code demo plate."""
        for element in self.elements:
            if element.get("type") == "text" and element.get("source") in CODE_SOURCES:
                size = max(1, int(round(element.get("max_size", 0.1) * self.geometry.height)))
                return self.resources.font(element.get("font"), size).getlength(text_for(element, row, self.spec))
        return 0

    def check(self, row):
        """Fit every text (fixed texts once, then cached) without drawing; raises TextDoesNotFit."""
        for element in self.elements:
            if element.get("type") == "text":
                text = text_for(element, row, self.spec)
                if text:
                    self.fitter.fit(element, text, self.geometry.box(element["box"]), self.geometry.height)
        if self.geometry.panel_on:
            panel.fit_values(self.fitter, self.geometry, self.spec["side_panel"], row)

    def render(self, row):
        """The finished RGB plate for one row; raises TextDoesNotFit when a text cannot fit its box."""
        self.check(row)
        canvas = self.static_layer().copy()
        for element in self.elements:
            if is_dynamic(element):
                self.draw_element(canvas, element, row)
        if self.geometry.panel_on:
            panel.draw_values(canvas, self.fitter, self.geometry, self.spec["side_panel"], row)
        return canvas.convert("RGB")


DEFAULT_PANEL = {"side": "right", "width_mm": 19.1, "style": "labelled", "fields": ["house_no", "slum"], "cut_line": True}


def with_options(spec, holes=True, side_panel=False):
    """The spec with the drill holes switched off and/or the side reference panel switched on, for one plate or batch."""
    spec = dict(spec)
    if not holes:
        spec["holes"] = dict(spec.get("holes") or {}, on=False)
    if side_panel:
        panel = dict(DEFAULT_PANEL)
        panel.update(spec.get("side_panel") or {})
        panel["on"] = True
        spec["side_panel"] = panel
    return spec


def render(spec, row, resources=None):
    return DesignRenderer(spec, resources).render(row)


def save_png(image, target, dpi):
    image.save(target, "PNG", dpi=(dpi, dpi))
