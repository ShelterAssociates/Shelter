"""Plate geometry (fractions and mm to pixels, holes, side panel) and the template layout checks."""

import math

HOLE_CLEARANCE_MM = 1.5
EDGE_CLEARANCE_MM = 1.5
MIN_TEXT_PT = 6
MIN_QR_MM = 15
MIN_QUIET_MODULES = 2
CONTAINERS = ("card", "badge")
DEFAULT_HOLES = {"on": True, "diameter_mm": 4.5, "edge_mm": 5, "position": "sides"}


def mm_to_px(value, dpi):
    return int(round(float(value) / 25.4 * dpi))


class Geometry(object):
    """Pixel sizes of one template; element boxes are fractions of the plate (side panel excluded)."""

    def __init__(self, spec):
        self.dpi = int(spec["dpi"])
        self.width = mm_to_px(spec["width_mm"], self.dpi)
        self.height = mm_to_px(spec["height_mm"], self.dpi)
        panel = spec.get("side_panel") or {}
        self.panel_on = bool(panel.get("on"))
        self.panel_side = panel.get("side", "right")
        self.panel_width = mm_to_px(panel.get("width_mm", 19.1), self.dpi) if self.panel_on else 0
        self.offset = self.panel_width if self.panel_on and self.panel_side == "left" else 0
        self.holes = dict(DEFAULT_HOLES, **(spec.get("holes") or {}))

    @property
    def size(self):
        return self.width + self.panel_width, self.height

    def mm(self, value):
        return mm_to_px(value, self.dpi)

    def box(self, fractions):
        """(x, y, w, h) in canvas pixels."""
        x, y, w, h = fractions
        return (self.offset + int(round(x * self.width)), int(round(y * self.height)),
                int(round(w * self.width)), int(round(h * self.height)))

    def length(self, fraction):
        """A size given as a fraction of the plate height, in pixels."""
        return int(round(float(fraction) * self.height))

    def panel_box(self):
        x = 0 if self.panel_side == "left" else self.width
        return x, 0, self.panel_width, self.height

    def hole_radius(self):
        return self.mm(self.holes["diameter_mm"]) // 2

    def hole_centres(self):
        if not self.holes.get("on"):
            return []
        edge = self.mm(self.holes["edge_mm"])
        left, right = self.offset + edge, self.offset + self.width - edge
        if self.holes.get("position") == "corners":
            return [(left, edge), (right, edge), (left, self.height - edge), (right, self.height - edge)]
        return [(left, self.height // 2), (right, self.height // 2)]


def overlaps(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def inside(inner, outer):
    return (inner[0] >= outer[0] and inner[1] >= outer[1]
            and inner[0] + inner[2] <= outer[0] + outer[2] and inner[1] + inner[3] <= outer[1] + outer[3])


def distance_to_box(point, box):
    dx = max(box[0] - point[0], 0, point[0] - (box[0] + box[2]))
    dy = max(box[1] - point[1], 0, point[1] - (box[1] + box[3]))
    return math.hypot(dx, dy)


def name(element):
    return '"{}"'.format(element.get("id", "?"))


def overlap_problems(geometry, elements):
    by_id = {element.get("id"): element for element in elements}
    found = []
    for element in elements:
        parent = by_id.get(element.get("parent"))
        if parent is not None and not inside(geometry.box(element["box"]), geometry.box(parent["box"])):
            found.append("{} sticks out of {}. Move it inside or resize it.".format(name(element), name(parent)))
    top = [element for element in elements if not element.get("parent")]
    for index, first in enumerate(top):
        for second in top[index + 1:]:
            if overlaps(geometry.box(first["box"]), geometry.box(second["box"])):
                found.append("{} overlaps {}. Move or resize one of them.".format(name(first), name(second)))
    return found


def clearance_problems(geometry, elements):
    found = []
    edge = geometry.mm(EDGE_CLEARANCE_MM)
    plate = (geometry.offset + edge, edge, geometry.width - 2 * edge, geometry.height - 2 * edge)
    hole_gap = geometry.hole_radius() + geometry.mm(HOLE_CLEARANCE_MM)
    for element in elements:
        box = geometry.box(element["box"])
        if not inside(box, plate):
            found.append("{} is closer than {} mm to the plate edge.".format(name(element), EDGE_CLEARANCE_MM))
        if any(distance_to_box(centre, box) < hole_gap for centre in geometry.hole_centres()):
            found.append("{} is closer than {} mm to a drill hole.".format(name(element), HOLE_CLEARANCE_MM))
    return found


def size_problems(geometry, elements, qr_version):
    found = []
    min_text = MIN_TEXT_PT / 72.0 * geometry.dpi
    for element in elements:
        changes_per_row = element.get("source", "fixed") not in ("fixed", "qr_caption")
        if element.get("type") == "text" and changes_per_row and geometry.length(element.get("min_size", 0)) < min_text - 0.5:
            found.append("{} can shrink below {} pt when printed. Raise its smallest size.".format(name(element), MIN_TEXT_PT))
        if element.get("type") == "qr":
            found.extend(qr_problems(geometry, element, elements, qr_version))
    return found


def qr_problems(geometry, element, elements, qr_version):
    box = geometry.box(element["box"])
    side = min(box[2], box[3])
    found = []
    if side < geometry.mm(MIN_QR_MM):
        found.append("{} is smaller than {} mm when printed.".format(name(element), MIN_QR_MM))
    quiet = int(element.get("quiet_zone", 0))
    module = side / float(17 + 4 * (qr_version or 40) + 2 * quiet)
    extra = int(math.ceil(max(0, MIN_QUIET_MODULES - quiet) * module))
    if extra:
        grown = (box[0] - extra, box[1] - extra, box[2] + 2 * extra, box[3] + 2 * extra)
        card = next((e for e in elements if e.get("id") == element.get("parent") and e.get("type") == "card"), None)
        siblings = [e for e in elements if e.get("parent") == element.get("parent") and e is not element]
        if (card is None or not inside(grown, geometry.box(card["box"]))
                or any(overlaps(grown, geometry.box(e["box"])) for e in siblings)):
            found.append("{} needs a blank margin of {} modules around it.".format(name(element), MIN_QUIET_MODULES))
    return found


def problems(spec, qr_version=None):
    """Layout problems of a template spec, in plain language; empty when the layout is fine."""
    geometry = Geometry(spec)
    elements = spec.get("elements") or []
    return (overlap_problems(geometry, elements) + clearance_problems(geometry, elements)
            + size_problems(geometry, elements, qr_version))
