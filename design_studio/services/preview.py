"""Template previews: a template drawn with the sample (or longest) row, and its layout problems. Both are cached
under a key made of everything that changes the picture (the look, the row, the fonts and logos, this code), so
drawing a template that was drawn before costs nothing."""

import base64
import glob
import hashlib
import io
import json
import os

from django.core.cache import caches

from design_studio.services import editor
from design_studio.services.render import DesignRenderer
from design_studio.services.resources import MissingResource, Resources
from design_studio.services.textfit import TextDoesNotFit

CACHE = "design_preview"
PREVIEW_SCALE = 0.5
CODE_STAMP = max(os.path.getmtime(path) for path in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "*.py")))


def sample_key(spec, worst, scale, resources):
    """Stable id of one preview picture; also its ETag."""
    data = {"spec": editor.numbers_as_floats(spec), "worst": bool(worst), "scale": float(scale), "code": CODE_STAMP,
            "fonts": resources.fonts, "assets": {str(ref): path for ref, path in resources.assets.items()}}
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def draw(spec, worst, scale, resources):
    """PNG bytes, or b"" when a text does not fit or a font/logo is missing."""
    rows_for = editor.WORST_ROWS if worst else editor.SAMPLE_ROWS
    dpi = max(1, int(spec["dpi"] * scale))
    try:
        image = DesignRenderer(dict(spec, dpi=dpi), resources).render(rows_for[spec["plate_type"]])
    except (TextDoesNotFit, MissingResource):
        return b""
    buffer = io.BytesIO()
    image.save(buffer, "PNG", dpi=(dpi, dpi), compress_level=1)
    return buffer.getvalue()


def sample_png(spec, worst=False, scale=1, resources=None):
    """The template drawn with a sample (or worst-case) row as PNG bytes, or None; scale < 1 draws at a lower DPI."""
    resources = resources or Resources.from_database()
    key = sample_key(spec, worst, scale, resources)
    png = caches[CACHE].get(key)
    if png is None:
        png = draw(spec, worst, scale, resources)
        caches[CACHE].set(key, png)
    return png or None


def preview(spec, worst=False, resources=None):
    """{"image": data URI or "", "problems": [...]} for the editor."""
    resources = resources or Resources.from_database()
    key = sample_key(spec, worst, PREVIEW_SCALE, resources) + ":problems"
    problems = caches[CACHE].get(key)
    if problems is None:
        problems = editor.problems(spec, resources)
        caches[CACHE].set(key, problems)
    png = sample_png(spec, worst, PREVIEW_SCALE, resources)
    return {"image": "data:image/png;base64," + base64.b64encode(png).decode("ascii") if png else "", "problems": problems}
