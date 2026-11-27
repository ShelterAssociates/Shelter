"""Template editor rules: what a valid template looks like, the worst rows it must fit, and saving a changed look
as a new version (old versions stay read-only so old batches can be made again exactly)."""

import json
import re

from django.db import transaction

from design_studio.models import DesignAsset, DesignTemplate
from design_studio.services import layout, linkpattern
from design_studio.services.render import DesignRenderer
from design_studio.services.textfit import TextDoesNotFit

LOOK_FIELDS = ("output_kind", "width_mm", "height_mm", "dpi", "mode", "background_image", "background", "elements",
               "holes", "side_panel", "qr_link_pattern", "qr_caption", "slum_suffix")
ELEMENT_TYPES = ("text", "qr", "image", "card", "badge", "line")
TEXT_SOURCES = ("fixed", "qr_caption", "digipin", "digipin_display", "pluscode", "slum", "house_no", "ward", "city", "lat", "long")
COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
SAMPLE_ROWS = {
    "digipin": {"digipin": "4J6M8286K8", "digipin_display": "4J6 M828 6K8", "pluscode": "", "house_no": "1", "slum": "Nimajga Mal",
                "ward": "9", "city": "Ichalkaranji", "lat": "16.6929355", "long": "74.45952441"},
    "pluscode": {"digipin": "", "digipin_display": "", "pluscode": "7J8PMFV5+5RCH", "house_no": "1", "slum": "Nimajga Mal",
                 "ward": "9", "city": "Ichalkaranji", "lat": "16.6929355", "long": "74.45952441"},
}
WORST_SLUM = "Ambedkar Nagar Wasti Phase Two Extension Near Railway Line 2"
WORST_ROWS = {
    "digipin": dict(SAMPLE_ROWS["digipin"], digipin="MMMMMMMMMM", digipin_display="MMM MMMM MMM", slum=WORST_SLUM, house_no="WWWWW"),
    "pluscode": dict(SAMPLE_ROWS["pluscode"], pluscode="WWWWWWWW+WWWW", slum=WORST_SLUM, house_no="WWWWW"),
}


def number_between(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high


def box_problems(element):
    box = element.get("box")
    if not (isinstance(box, list) and len(box) == 4 and all(number_between(value, 0, 1) for value in box)):
        return ["{} needs a box of four numbers between 0 and 1.".format(layout.name(element))]
    if box[2] <= 0 or box[3] <= 0 or box[0] + box[2] > 1.0001 or box[1] + box[3] > 1.0001:
        return ["{} must have a width and height and stay on the plate.".format(layout.name(element))]
    return []


def colour_problems(element, keys):
    return ["{} has an invalid colour in {} (use #RRGGBB).".format(layout.name(element), key)
            for key in keys if element.get(key) is not None and not COLOUR.match(str(element.get(key)))]


def text_problems(element, fonts):
    found = []
    if element.get("source", "fixed") not in TEXT_SOURCES:
        found.append("{} has an unknown source.".format(layout.name(element)))
    if element.get("font") and element["font"] not in fonts:
        found.append('{} uses the font "{}", which is not installed.'.format(layout.name(element), element["font"]))
    largest, smallest = element.get("max_size"), element.get("min_size", element.get("max_size"))
    if not (number_between(largest, 0.005, 1) and number_between(smallest, 0.005, 1) and smallest <= largest):
        found.append("{} needs sizes between 0.005 and 1 with the smallest no bigger than the largest.".format(layout.name(element)))
    if element.get("align", "left") not in ("left", "centre", "right") or element.get("valign", "middle") not in ("top", "middle", "bottom"):
        found.append("{} has an unknown alignment.".format(layout.name(element)))
    if element.get("wrap", "never") not in ("never", "words") or not number_between(element.get("max_lines", 1), 1, 5):
        found.append("{} wraps over 1 to 5 lines only.".format(layout.name(element)))
    if "<" in str(element.get("text", "")) or ">" in str(element.get("text", "")):
        found.append("{} text may not contain < or >.".format(layout.name(element)))
    return found + colour_problems(element, ("colour",))


def asset_problems(element, ref):
    if isinstance(ref, str) and ref.startswith("auto:"):
        return [] if ref[5:] in ("digipin_symbol", "india_post_logo", "maps_logo") else ["{} uses an unknown logo.".format(layout.name(element))]
    if str(ref).isdigit() and DesignAsset.objects.filter(pk=int(ref)).exists():
        return []
    return ["{} uses a logo that does not exist.".format(layout.name(element))]


def element_problems(element, fonts, ids):
    if not isinstance(element, dict) or element.get("type") not in ELEMENT_TYPES:
        return ["Every element needs a type: {}.".format(", ".join(ELEMENT_TYPES))]
    found = box_problems(element)
    kind = element["type"]
    if kind == "text":
        found += text_problems(element, fonts)
    elif kind == "qr":
        found += colour_problems(element, ("fg", "bg"))
        if not number_between(element.get("quiet_zone", 0), 0, 8):
            found.append("{} quiet zone must be 0 to 8 modules.".format(layout.name(element)))
    elif kind == "image":
        found += asset_problems(element, element.get("asset")) + colour_problems(element, ("recolour",))
    elif kind == "badge":
        found += colour_problems(element, ("fill", "ring_colour", "gap_colour"))
        if element.get("child"):
            found += asset_problems(element, element["child"].get("asset")) + colour_problems(element["child"], ("recolour",))
    elif kind in ("card", "line"):
        found += colour_problems(element, ("fill", "colour"))
    if element.get("parent") and element["parent"] not in ids:
        found.append("{} belongs to a card or badge that does not exist.".format(layout.name(element)))
    return found


def elements_problems(elements, fonts):
    if not isinstance(elements, list) or not elements:
        return ["The template needs at least one element."]
    ids = [element.get("id") for element in elements if isinstance(element, dict)]
    found = []
    if len(set(ids)) != len(ids) or not all(isinstance(value, str) and value and "<" not in value and ">" not in value for value in ids):
        found.append("Every element needs its own id (no < or >).")
    containers = {element["id"] for element in elements if isinstance(element, dict) and element.get("type") in layout.CONTAINERS}
    for element in elements:
        found += element_problems(element, fonts, containers)
    return found


PANEL_SLUM_CHARACTERS = 30


def worst_case_problems(spec, resources):
    """The plate must fit the longest values; a side panel must fit a 30-character slum name (longer rows are skipped)."""
    worst = WORST_ROWS[spec["plate_type"]]
    plate_only = dict(spec, side_panel=dict(spec.get("side_panel") or {}, on=False))
    checks = ((plate_only, worst, "code {}, a 60-character slum name, a 5-character house number".format(
        worst.get("digipin_display") or worst.get("pluscode"))),)
    if (spec.get("side_panel") or {}).get("on"):
        checks += ((spec, dict(worst, slum=WORST_SLUM[:PANEL_SLUM_CHARACTERS]), "a {}-character slum name in the side panel".format(PANEL_SLUM_CHARACTERS)),)
    for checked_spec, row, values in checks:
        try:
            DesignRenderer(checked_spec, resources).check(row)
        except TextDoesNotFit as exc:
            return ['"{}" cannot fit the longest values ({}). Make its box bigger or its smallest size smaller.'.format(exc.element_id, values)]
    return []


def problems(spec, resources):
    """Every reason the template cannot be saved, in plain language."""
    found = elements_problems(spec.get("elements"), resources.fonts)
    if spec.get("mode") == "image" and not spec.get("background_image"):
        found.append("Pick a background image, or switch the background to designed.")
    found += linkpattern.problems(spec.get("qr_link_pattern"), spec.get("plate_type"))
    if found:
        return found
    found += layout.problems(spec, linkpattern.worst_case_version(spec["qr_link_pattern"]))
    return found or worst_case_problems(spec, resources)


def numbers_as_floats(value):
    if isinstance(value, dict):
        return {key: numbers_as_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [numbers_as_floats(item) for item in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return value


def comparable(spec):
    """Look fields as text; 5 and 5.0 compare equal."""
    return {field: json.dumps(numbers_as_floats(spec.get(field)), sort_keys=True) for field in LOOK_FIELDS}


def describe_changes(old, new):
    """Short lines for the "template changed" email."""
    labels = {"width_mm": "Width (mm)", "height_mm": "Height (mm)", "dpi": "DPI", "output_kind": "Plate or sticker", "mode": "Background mode",
              "background_image": "Background image", "background": "Colours, grid, border, strip", "holes": "Drill holes",
              "side_panel": "Side panel", "qr_link_pattern": "QR link", "qr_caption": "Text under QR", "slum_suffix": "Slum suffix"}
    old_values, new_values = comparable(old), comparable(new)
    lines = ["{}: {} -> {}".format(label, old.get(field), new.get(field)) if field not in ("background", "holes", "side_panel") else "{} changed".format(label)
             for field, label in labels.items() if old_values[field] != new_values[field]]
    old_elements = {element.get("id"): element for element in old.get("elements") or []}
    changed = [element.get("id") for element in new.get("elements") or [] if old_elements.get(element.get("id")) != element]
    removed = [key for key in old_elements if key not in {element.get("id") for element in new.get("elements") or []}]
    if changed:
        lines.append("Elements changed or added: {}".format(", ".join(str(item) for item in changed)))
    if removed:
        lines.append("Elements removed: {}".format(", ".join(str(item) for item in removed)))
    return lines


def apply_settings(template, values):
    for field, value in values.items():
        setattr(template, field, value)


def apply_look(template, spec):
    for field in LOOK_FIELDS:
        if field == "background_image":
            template.background_image_id = spec.get("background_image") or None
        else:
            setattr(template, field, spec[field])


@transaction.atomic
def save(template, spec, values, user):
    """Create, update or version a template. Returns (saved template, look_changed)."""
    if template.pk is None:
        apply_look(template, spec)
        template.created_by = user
        apply_settings(template, values)
        template.save()
        return template, True
    if comparable(template.spec()) == comparable(spec):
        apply_settings(template, values)
        template.save()
        return template, False
    fresh = DesignTemplate(plate_type=template.plate_type, parent=template, version=template.version + 1, created_by=user)
    apply_look(fresh, spec)
    apply_settings(fresh, values)
    fresh.save()
    DesignTemplate.objects.filter(pk=template.pk).update(is_active=False, is_default=False)
    return fresh, True


def family(template):
    """The template and all its older versions (each version points to the one before it)."""
    members, current = [], template
    while current is not None:
        members.append(current)
        current = current.parent
    return members


def is_archived(template):
    return template.is_latest and not template.is_active


def archive(template):
    DesignTemplate.objects.filter(pk=template.pk).update(is_active=False, is_default=False)


def restore(template):
    DesignTemplate.objects.filter(pk=template.pk).update(is_active=True)


def batch_count(template):
    from design_studio.models import DesignBatch

    return DesignBatch.objects.filter(template__in=[member.pk for member in family(template)]).count()


@transaction.atomic
def delete_permanently(template):
    """Delete an archived template with all its versions, newest first. Refused while any batch used one of them."""
    if not is_archived(template):
        raise ValueError("Only an archived template can be deleted. Archive it first.")
    used = batch_count(template)
    if used:
        raise ValueError("This template was used by {} batch{}, so it cannot be deleted: those batches must stay "
                         "possible to make again. It stays archived and hidden from every picker.".format(used, "" if used == 1 else "es"))
    members = family(template)
    for member in members:
        member.delete()
    return len(members)
