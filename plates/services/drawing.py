"""Shapes on the plate: background, grid, border, strip, holes, cards, badges, images and lines."""

import math

from PIL import Image, ImageColor, ImageDraw, ImageFilter

WHITE = "#FFFFFF"


def rgba(colour, opacity=1.0):
    red, green, blue = ImageColor.getrgb(colour)[:3]
    return red, green, blue, int(round(255 * float(opacity)))


def lerp(first, second, t):
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(ImageColor.getrgb(first), ImageColor.getrgb(second)))


def gradient(size, colours, angle):
    """Two-colour gradient drawn on a 64 x 16 grid and stretched, so it is smooth at any size."""
    radians = math.radians(float(angle))
    total = math.cos(radians) + math.sin(radians)
    across, down = round(math.cos(radians) / total, 6), round(math.sin(radians) / total, 6)
    small = Image.new("RGB", (64, 16))
    pixels = small.load()
    for x in range(64):
        for y in range(16):
            pixels[x, y] = lerp(colours[0], colours[-1], (x / 63.0) * across + (y / 15.0) * down)
    return small.resize(size, Image.BILINEAR).convert("RGBA")


def fill(size, background):
    kind = background.get("fill", "gradient")
    colours = background.get("colours") or [WHITE]
    if kind == "gradient":
        return gradient(size, colours, background.get("gradient_angle", 0))
    if kind == "solid":
        return Image.new("RGBA", size, rgba(colours[0]))
    return Image.new("RGBA", size, (255, 255, 255, 0))


def cover(image, size):
    """Image scaled to fill size and centre-cropped."""
    scale = max(size[0] / float(image.width), size[1] / float(image.height))
    resized = image.resize((max(1, int(round(image.width * scale))), max(1, int(round(image.height * scale)))), Image.LANCZOS)
    left, top = (resized.width - size[0]) // 2, (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1])).convert("RGBA")


def grid(canvas, area, settings):
    """Faint grid; vertical lines fade towards the right."""
    x0, y0, width, height = area
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    base = int(round(255 * float(settings.get("opacity", 0.09))))
    major = max(1, int(round(float(settings.get("major", 0.5)) * height)))
    step = max(1, major // int(settings.get("divisions", 4)))
    thick, thin = max(1, int(round(height / 300.0))), max(1, int(round(height / 450.0)))
    for gx in range(0, width + major, step):
        alpha = max(0, int(base * (1 - gx / float(width))))
        is_major = gx % major == 0
        draw.line([x0 + gx, y0, x0 + gx, y0 + height], fill=(255, 255, 255, alpha * 2 if is_major else alpha), width=thick if is_major else thin)
    for gy in range(0, height + major, step):
        is_major = gy % major == 0
        draw.line([x0, y0 + gy, x0 + width, y0 + gy], fill=(255, 255, 255, base if is_major else base // 2), width=thick if is_major else thin)
    layer = layer.crop((x0, y0, x0 + width, y0 + height))
    canvas.alpha_composite(layer, (x0, y0))


def border(canvas, area, settings, length):
    x0, y0, width, height = area
    inset, radius, line = length(settings.get("inset", 0.04)), length(settings.get("radius", 0.05)), max(1, length(settings.get("width", 0.005)))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        [x0 + inset, y0 + inset, x0 + width - inset, y0 + height - inset], radius,
        outline=rgba(settings.get("colour", WHITE), settings.get("opacity", 1)), width=line)
    canvas.alpha_composite(layer)


def strip(canvas, area, settings, length):
    """Bands of colour (e.g. the tricolour) along the top or bottom edge."""
    x0, y0, width, height = area
    band = max(1, length(settings.get("height", 0.03)))
    colours = settings.get("colours") or ["#F58220", WHITE, "#138808"]
    top = y0 if settings.get("position") == "top" else y0 + height - band
    draw = ImageDraw.Draw(canvas)
    for index, colour in enumerate(colours):
        left = x0 + width * index // len(colours)
        right = x0 + width * (index + 1) // len(colours)
        draw.rectangle([left, top, right, top + band - 1], fill=rgba(colour))


def holes(canvas, geometry):
    """Drill marks: white circle with a thin cross."""
    settings = geometry.holes
    radius = geometry.hole_radius()
    scale = geometry.dpi / 600.0
    outline, cross, inset = max(1, int(round(4 * scale))), max(1, int(round(3 * scale))), int(round(14 * scale))
    ink = rgba(settings.get("outline", "#2A2468"))
    draw = ImageDraw.Draw(canvas)
    for cx, cy in geometry.hole_centres():
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=rgba(settings.get("fill", WHITE)), outline=ink, width=outline)
        if settings.get("marker", True):
            draw.line([cx - radius + inset, cy, cx + radius - inset, cy], fill=ink, width=cross)
            draw.line([cx, cy - radius + inset, cx, cy + radius - inset], fill=ink, width=cross)


def shadow(canvas, box, radius, settings, length):
    x, y, width, height = box
    dx, dy, blur = length(settings.get("dx", 0.009)), length(settings.get("dy", 0.013)), length(settings.get("blur", 0.013))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        [x + dx, y + dy, x + width + dx, y + height + dy], radius, fill=(0, 0, 0, int(round(255 * float(settings.get("opacity", 0.35))))))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def card(canvas, element, box, length):
    radius = length(element.get("radius", 0.04))
    if (element.get("shadow") or {}).get("on"):
        shadow(canvas, box, radius, element["shadow"], length)
    outline = element.get("outline") or {}
    x, y, width, height = box
    ImageDraw.Draw(canvas).rounded_rectangle(
        [x, y, x + width, y + height], radius, fill=rgba(element.get("fill", WHITE)),
        outline=rgba(outline["colour"]) if outline.get("on") else None, width=max(1, length(outline.get("width", 0.003))))


def badge(canvas, element, box, length, resources):
    """Ring, gap and filled circle, with an optional image in the middle."""
    radius = min(box[2], box[3]) // 2
    cx, cy = box[0] + box[2] // 2, box[1] + box[3] // 2
    ring, gap = length(element.get("ring_width", 0)), length(element.get("gap", 0))
    draw = ImageDraw.Draw(canvas)
    for r, colour in ((radius, element.get("ring_colour", WHITE)), (radius - ring, element.get("gap_colour", element.get("fill", WHITE))),
                      (radius - ring - gap, element.get("fill", WHITE))):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgba(colour))
    child = element.get("child")
    if child:
        inner = radius - ring - gap
        icon = scaled(resources.image(child["asset"]), height=int(round(2 * inner * float(child.get("size", 0.65)))), colour=child.get("recolour"))
        canvas.alpha_composite(icon, (int(cx - icon.width / 2.0), int(cy - icon.height / 2.0)))


def scaled(image, height=None, width=None, colour=None):
    if colour:
        solid = Image.new("RGBA", image.size, rgba(colour))
        solid.putalpha(image.getchannel("A"))
        image = solid
    scale = min(height / float(image.height) if height else 9e9, width / float(image.width) if width else 9e9)
    return image.resize((max(1, int(round(image.width * scale))), max(1, int(round(image.height * scale)))), Image.LANCZOS)


def picture(canvas, element, box, resources):
    """An asset fitted inside its box (contain), centred."""
    icon = scaled(resources.image(element["asset"]), height=box[3], width=box[2], colour=element.get("recolour"))
    canvas.alpha_composite(icon, (box[0] + (box[2] - icon.width) // 2, box[1] + (box[3] - icon.height) // 2))


def line(canvas, element, box, length):
    """A rule along the longer side of its box, solid or dashed."""
    width = max(1, length(element.get("width", 0.004)))
    x, y, w, h = box
    start, end = ((x, y + h // 2), (x + w, y + h // 2)) if w >= h else ((x + w // 2, y), (x + w // 2, y + h))
    dash = length(element.get("dash", 0))
    draw = ImageDraw.Draw(canvas)
    colour = rgba(element.get("colour", WHITE))
    if not dash:
        draw.line([start, end], fill=colour, width=width)
        return
    total = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
    for offset in range(0, total, 2 * dash):
        stop = min(offset + dash, total)
        if w >= h:
            draw.line([(start[0] + offset, start[1]), (start[0] + stop, start[1])], fill=colour, width=width)
        else:
            draw.line([(start[0], start[1] + offset), (start[0], start[1] + stop)], fill=colour, width=width)
