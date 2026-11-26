"""Creates the plates group, the bundled fonts and logos, and the two approved templates. Safe to run again."""

import json
import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from plates.models import PlateAsset, PlateFont, PlateTemplate
from plates.services.resources import BUNDLED_ASSETS, BUNDLED_FONTS, STATIC_DIR

PRESET_DIR = os.path.join(settings.BASE_DIR, "plates", "fixtures", "presets")
PRESETS = ("digipin_plate.json", "pluscode_plate.json")
LOOK_FIELDS = (
    "name", "output_kind", "width_mm", "height_mm", "dpi", "mode", "background", "elements",
    "holes", "side_panel", "qr_link_pattern", "qr_caption", "slum_suffix",
)


def load_preset(file_name):
    with open(os.path.join(PRESET_DIR, file_name)) as handle:
        return json.load(handle)


def same_look(template, preset):
    current = template.spec()
    current["name"] = template.name
    return all(json.dumps(current.get(field), sort_keys=True) == json.dumps(preset[field], sort_keys=True) for field in LOOK_FIELDS)


class Command(BaseCommand):
    help = "Create the plates group, bundled fonts and logos, and the approved DIGIPIN and Plus Code templates."

    @transaction.atomic
    def handle(self, *args, **options):
        for name in getattr(settings, "PLATES_GROUPS", []) or []:
            group, created = Group.objects.get_or_create(name=name)
            self.report("Group", name, "created" if created else "already there")
        for name, file_name, variation in BUNDLED_FONTS:
            self.seed_font(name, file_name, variation)
        for name, kind, file_name, recolourable in BUNDLED_ASSETS:
            self.seed_asset(name, kind, file_name, recolourable)
        for file_name in PRESETS:
            self.seed_template(load_preset(file_name))

    def report(self, kind, name, outcome):
        self.stdout.write("{:<9} {:<32} {}".format(kind, name, outcome))

    def seed_font(self, name, file_name, variation):
        if PlateFont.objects.filter(name=name).exists():
            self.report("Font", name, "already there")
            return
        font = PlateFont(name=name, variation=variation, preset_key=name)
        with open(os.path.join(STATIC_DIR, "fonts", file_name), "rb") as handle:
            font.file.save(file_name, File(handle), save=True)
        self.report("Font", name, "created")

    def seed_asset(self, name, kind, file_name, recolourable):
        if PlateAsset.objects.filter(preset_key=kind).exists():
            self.report("Logo", name, "already there")
            return
        is_default = not PlateAsset.objects.filter(kind=kind, is_default=True).exists()
        asset = PlateAsset(name=name, kind=kind, recolourable=recolourable, is_default=is_default, preset_key=kind)
        with open(os.path.join(STATIC_DIR, "assets", file_name), "rb") as handle:
            asset.image.save(file_name, File(handle), save=True)
        self.report("Logo", name, "created" + ("" if is_default else " (another default is in use)"))

    def seed_template(self, preset):
        key = preset["preset_key"]
        current = PlateTemplate.objects.filter(preset_key=key).order_by("-version").first()
        if current is None:
            self.create_template(preset, None)
            return self.report("Template", preset["name"], "created")
        if current.versions.exists():
            return self.report("Template", preset["name"], "left alone: edited in the template editor")
        if same_look(current, preset):
            return self.report("Template", preset["name"], "up to date")
        if current.batches.exists():
            self.create_template(preset, current)
            return self.report("Template", preset["name"], "new version {} (old one is used by batches)".format(current.version + 1))
        for field in LOOK_FIELDS:
            setattr(current, field, preset[field])
        current.save()
        self.report("Template", preset["name"], "updated")

    def create_template(self, preset, parent):
        values = {field: preset[field] for field in LOOK_FIELDS}
        is_default = preset.get("is_default", False) and (parent is not None and parent.is_default or not PlateTemplate.objects.filter(
            plate_type=preset["plate_type"], output_kind=preset["output_kind"], is_default=True).exists())
        template = PlateTemplate.objects.create(
            plate_type=preset["plate_type"], preset_key=preset["preset_key"], is_default=is_default,
            version=parent.version + 1 if parent else 1, parent=parent, **values)
        if parent is not None:
            PlateTemplate.objects.filter(pk=parent.pk).update(is_active=False, is_default=False)
        return template
