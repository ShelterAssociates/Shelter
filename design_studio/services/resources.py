"""Fonts and logos for rendering. Files never change under a path (uploads get random names), so each worker
loads a font size or logo once and every render after that reuses it."""

import functools
import os

from django.conf import settings
from PIL import Image, ImageFont

STATIC_DIR = os.path.join(settings.BASE_DIR, "design_studio", "static", "design_studio")
DEFAULT_FONT = "Liberation Sans Bold"
BUNDLED_FONTS = (
    ("Liberation Sans Bold", "LiberationSans-Bold.ttf", ""),
    ("Merriweather Bold", "Merriweather.ttf", "Bold"),
    ("Roboto Bold", "Roboto.ttf", "Bold"),
    ("Roboto Condensed Bold", "Roboto.ttf", "Condensed Bold"),
)
BUNDLED_ASSETS = (
    ("DIGIPIN symbol", "digipin_symbol", "digipin_symbol.png", True),
    ("India Post logo", "india_post_logo", "india_post_logo.png", False),
    ("Google Maps logo", "maps_logo", "google_maps_logo.png", False),
)


class MissingResource(ValueError):
    pass


def load_font(path, size, variation=""):
    font = ImageFont.truetype(path, size)
    if variation:
        names = font.get_variation_names()
        # FreeType counts named styles from 1; Pillow before 10.1 passed the 0-based index (one weight too light).
        font.font.setvarname(names.index(variation.encode()) + 1)
    return font


def trimmed(image):
    """RGBA image cropped to its visible pixels."""
    image = image.convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    return image.crop(bbox) if bbox else image


@functools.lru_cache(maxsize=512)
def cached_font(path, size, variation=""):
    return load_font(path, size, variation)


@functools.lru_cache(maxsize=64)
def cached_image(path):
    """The image at path, trimmed; shared, so callers must not change it."""
    with Image.open(path) as source:
        return trimmed(source)


class Resources(object):
    """fonts: {name: (path, variation)}; assets: {"auto:<kind>" or id: path}."""

    def __init__(self, fonts, assets):
        self.fonts = dict(fonts)
        self.assets = dict(assets)
        self.font_cache = {}
        self.image_cache = {}

    @classmethod
    def bundled(cls):
        """The fonts and logos shipped in design_studio/static/design_studio/ (tests, and before seeding)."""
        fonts = {name: (os.path.join(STATIC_DIR, "fonts", file), variation) for name, file, variation in BUNDLED_FONTS}
        assets = {"auto:" + kind: os.path.join(STATIC_DIR, "assets", file) for _, kind, file, _ in BUNDLED_ASSETS}
        return cls(fonts, assets)

    @classmethod
    def from_database(cls):
        from design_studio.models import DesignAsset, DesignFont

        fonts = {font.name: (font.file.path, font.variation) for font in DesignFont.objects.all()}
        assets = {asset.pk: asset.image.path for asset in DesignAsset.objects.all()}
        for asset in DesignAsset.objects.filter(is_default=True):
            assets["auto:" + asset.kind] = asset.image.path
        return cls(fonts, assets)

    def font(self, name, size):
        key = (name or DEFAULT_FONT, int(size))
        if key not in self.font_cache:
            if key[0] not in self.fonts:
                raise MissingResource('Font "{}" is not installed.'.format(key[0]))
            path, variation = self.fonts[key[0]]
            self.font_cache[key] = cached_font(path, key[1], variation)
        return self.font_cache[key]

    def image(self, ref):
        """The asset as RGBA, cropped to its visible pixels."""
        if ref not in self.image_cache:
            path = self.assets.get(ref)
            if path is None and isinstance(ref, str) and ref.isdigit():
                path = self.assets.get(int(ref))
            if path is None:
                raise MissingResource('Image "{}" is not available.'.format(ref))
            self.image_cache[ref] = cached_image(path)
        return self.image_cache[ref]
