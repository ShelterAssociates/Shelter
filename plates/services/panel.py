"""The side reference panel that is cut off the plate: labelled, centred or old (grey) style."""

from PIL import ImageDraw

from plates.services import textfit
from plates.services.drawing import rgba
from plates.services.layout import MIN_TEXT_PT

LABELS = {"house_no": "HH NO.", "slum": "SLUM", "ward": "WARD", "city": "CITY"}
STYLES = {
    "labelled": {"fill": "#FFFFFF", "label": "#6B6B6B", "value": "#2A2468", "align": "left", "band": False},
    "centred": {"fill": "#ECECF2", "label": "#7A7A8C", "value": "#2A2468", "align": "centre", "band": True},
    "old": {"fill": "#D9DADB", "label": None, "value": "#000000", "align": "left", "band": False},
}
FONT = "Liberation Sans Bold"
MARGIN = 0.08


def style_of(settings):
    return STYLES.get(settings.get("style", "labelled"), STYLES["labelled"])


def blocks(geometry, settings):
    """(field, label box, value box) for every panel field, in canvas pixels."""
    x, y, width, height = geometry.panel_box()
    fields = [field for field in settings.get("fields") or ["house_no", "slum"] if field]
    pad_x, pad_y = int(width * 0.06), int(height * MARGIN)
    left, inner_w = x + pad_x, width - 2 * pad_x
    block = (height - 2 * pad_y) // max(1, len(fields))
    labelled = style_of(settings)["label"] is not None
    found = []
    for index, field in enumerate(fields):
        top = y + pad_y + index * block
        label_h = int(block * 0.28) if labelled else 0
        found.append((field, (left, top, inner_w, label_h), (left, top + label_h, inner_w, block - label_h)))
    return found


def value_element(field, settings, box_height, geometry):
    largest = box_height * (0.9 if field == "house_no" else 0.6) / geometry.height
    six_points = MIN_TEXT_PT / 72.0 * geometry.dpi / geometry.height
    return {
        "id": "side panel {}".format(field.replace("_", " ")), "font": settings.get("font", FONT),
        "max_size": largest, "min_size": min(largest, six_points),
        "align": style_of(settings)["align"], "valign": "middle", "colour": settings.get("colour") or style_of(settings)["value"],
        "wrap": "never" if field == "house_no" else "words", "max_lines": 1 if field == "house_no" else 4,
    }


def label_element(field, settings, box_height, plate_height):
    return {
        "id": "side panel label", "font": settings.get("font", FONT), "max_size": box_height * 0.7 / plate_height,
        "min_size": 0.03, "align": style_of(settings)["align"], "valign": "bottom", "colour": style_of(settings)["label"],
        "letter_spacing": 0.1,
    }


def draw_static(canvas, geometry, settings, resources):
    style = style_of(settings)
    x, y, width, height = geometry.panel_box()
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([x, y, x + width - 1, y + height - 1], fill=rgba(style["fill"]))
    if style["band"]:
        draw.rectangle([x, y, x + width - 1, y + max(2, height // 45)], fill=rgba(settings.get("colour") or style["value"]))
    if settings.get("cut_line", True):
        edge = x + 3 if geometry.panel_side == "right" else x + width - 4
        dash = max(4, height // 38)
        for top in range(0, height, 2 * dash):
            draw.line([edge, top, edge, top + dash], fill=rgba("#9A9A9A"), width=max(2, height // 190))
    if style["label"] is not None:
        fitter = textfit.TextFitter(resources)
        for field, label_box, _ in blocks(geometry, settings):
            element = label_element(field, settings, label_box[3], geometry.height)
            textfit.draw(draw, fitter.fit(element, LABELS.get(field, field.upper()), label_box, geometry.height), element)


def fitted_values(fitter, geometry, settings, row):
    for field, _, value_box in blocks(geometry, settings):
        text = str(row.get(field) or "").strip()
        if text:
            element = value_element(field, settings, value_box[3], geometry)
            yield element, fitter.fit(element, text.upper() if field == "slum" else text, value_box, geometry.height)


def fit_values(fitter, geometry, settings, row):
    list(fitted_values(fitter, geometry, settings, row))


def draw_values(canvas, fitter, geometry, settings, row):
    draw = ImageDraw.Draw(canvas)
    for element, fitted in fitted_values(fitter, geometry, settings, row):
        textfit.draw(draw, fitted, element)
