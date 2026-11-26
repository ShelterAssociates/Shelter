"""Shrink-to-fit text: measured with the real font, aligned by its ink, never drawn outside its box."""

PADDING = 0.04
STEP = 0.98
LINE_SPACING = 1.2


class TextDoesNotFit(ValueError):
    def __init__(self, element_id):
        super().__init__("Text too long for {}".format(element_id))
        self.element_id = element_id


def inner_box(box, padding=PADDING):
    pad_x, pad_y = int(round(box[2] * padding)), int(round(box[3] * padding))
    return box[0] + pad_x, box[1] + pad_y, box[2] - 2 * pad_x, box[3] - 2 * pad_y


def line_ink(font, text, spacing):
    """Ink (left, top, right, bottom) of one line drawn at origin (0, 0)."""
    if not spacing or len(text) < 2:
        return font.getbbox(text) if text else (0, 0, 0, 0)
    x, left, top, right, bottom = 0.0, None, None, None, None
    for char in text:
        l, t, r, b = font.getbbox(char)
        if r > l and b > t:
            left = x + l if left is None else min(left, x + l)
            right = x + r if right is None else max(right, x + r)
            top = t if top is None else min(top, t)
            bottom = b if bottom is None else max(bottom, b)
        x += font.getlength(char) + spacing
    return (left or 0, top or 0, right or 0, bottom or 0)


def sizes(largest, smallest):
    size = largest
    yield size
    while size > smallest:
        size = max(smallest, min(size - 1, int(round(size * STEP))))
        yield size


def wrap(font, text, spacing, width, max_lines):
    """Lines broken at spaces to fit width, or None when more than max_lines are needed."""
    lines = []
    for word in text.split():
        candidate = (lines[-1] + " " + word) if lines else word
        ink = line_ink(font, candidate, spacing)
        if lines and ink[2] - ink[0] <= width:
            lines[-1] = candidate
        else:
            lines.append(word)
        if len(lines) > max_lines:
            return None
    return lines or [""]


class Fitted(object):
    def __init__(self, lines, font, spacing, line_height, inks, inner):
        self.lines = lines
        self.font = font
        self.spacing = spacing
        self.line_height = line_height
        self.inks = inks
        self.inner = inner
        self.top = min(ink[1] + index * line_height for index, ink in enumerate(inks))
        self.bottom = max(ink[3] + index * line_height for index, ink in enumerate(inks))
        self.width = max(ink[2] - ink[0] for ink in inks)

    @property
    def height(self):
        return self.bottom - self.top

    def fits(self):
        return self.width <= self.inner[2] and self.height <= self.inner[3]


class TextFitter(object):
    """Fits text elements; the fitted size is cached per element and text value."""

    def __init__(self, resources):
        self.resources = resources
        self.cache = {}

    def fit(self, element, text, box, plate_height):
        key = (element.get("id"), text, tuple(box))
        if key not in self.cache:
            self.cache[key] = self.measure(element, text, box, plate_height)
        return self.cache[key]

    def measure(self, element, text, box, plate_height):
        inner = inner_box(box, element.get("padding", PADDING))
        largest = max(1, int(round(element.get("max_size", 0.1) * plate_height)))
        smallest = min(largest, max(1, int(round(element.get("min_size", element.get("max_size", 0.1)) * plate_height))))
        max_lines = int(element.get("max_lines", 1)) if element.get("wrap") == "words" else 1
        for line_count in range(1, max(1, max_lines) + 1):
            for size in sizes(largest, smallest):
                fitted = self.attempt(element, text, size, inner, line_count)
                if fitted is not None and fitted.fits():
                    return fitted
        raise TextDoesNotFit(element.get("id", "text"))

    def attempt(self, element, text, size, inner, line_count):
        font = self.resources.font(element.get("font"), size)
        spacing = int(size * float(element.get("letter_spacing", 0)))
        lines = [text] if line_count == 1 else wrap(font, text, spacing, inner[2], line_count)
        if lines is None:
            return None
        inks = [line_ink(font, line, spacing) for line in lines]
        line_height = int(round(size * float(element.get("line_spacing", LINE_SPACING))))
        return Fitted(lines, font, spacing, line_height, inks, inner)


def origins(fitted, align, valign):
    """(x, y) drawing origin of every line."""
    x0, y0, width, height = fitted.inner
    if valign == "top":
        first = y0 - fitted.top
    elif valign == "bottom":
        first = y0 + height - fitted.bottom
    else:
        first = y0 + (height - fitted.height) / 2.0 - fitted.top
    points = []
    for index, (left, _, right, _) in enumerate(fitted.inks):
        if align == "right":
            x = x0 + width - right
        elif align == "centre":
            x = x0 + (width - (right - left)) / 2.0 - left
        else:
            x = x0 - left
        points.append((x, first + index * fitted.line_height))
    return points


def draw(draw_on, fitted, element):
    colour = element.get("colour", "#000000")
    for line, (x, y) in zip(fitted.lines, origins(fitted, element.get("align", "left"), element.get("valign", "middle"))):
        if not fitted.spacing:
            draw_on.text((x, y), line, font=fitted.font, fill=colour)
            continue
        for char in line:
            draw_on.text((x, y), char, font=fitted.font, fill=colour)
            x += fitted.font.getlength(char) + fitted.spacing
