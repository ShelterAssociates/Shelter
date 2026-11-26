"""Plate templates, their logos and fonts, generation batches and the audit trail."""

import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from jsonfield import JSONField

PLATE_TYPES = (("digipin", "DIGIPIN"), ("pluscode", "Plus Code"))
OUTPUT_KINDS = (("plate", "Plate"), ("sticker", "Sticker"))
DPI_CHOICES = ((300, "300 DPI"), (600, "600 DPI"))
TEMPLATE_MODES = (("designed", "Designed"), ("image", "Uploaded background image"))
ASSET_KINDS = (
    ("digipin_symbol", "DIGIPIN symbol"),
    ("india_post_logo", "India Post logo"),
    ("maps_logo", "Google Maps logo"),
    ("background", "Background image"),
    ("other", "Other"),
)
BATCH_SOURCES = (("single", "Single plate"), ("excel", "Excel upload"))
OUTPUT_FORMATS = (("png", "PNG files"),)
BATCH_STATUSES = (
    ("draft", "Draft"),
    ("queued", "Queued"),
    ("running", "Running"),
    ("done", "Done"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
    ("expired", "Expired"),
)
ACTIVITY_ACTIONS = (
    ("upload", "Upload"),
    ("confirm", "Confirm"),
    ("cancel", "Cancel"),
    ("download", "Download"),
    ("generate_again", "Generate again"),
    ("single_plate", "Single plate"),
    ("template_created", "Template created"),
    ("template_changed", "Template changed"),
    ("asset_uploaded", "Asset uploaded"),
    ("font_uploaded", "Font uploaded"),
)


def random_name(directory, filename):
    extension = os.path.splitext(filename or "")[1].lower()
    return os.path.join(directory, "{}{}".format(uuid.uuid4().hex, extension))


def asset_path(asset, filename):
    return random_name(getattr(settings, "PLATES_ASSET_DIR_NAME", "plate_assets"), filename)


def font_path(font, filename):
    return random_name(getattr(settings, "PLATES_FONT_DIR_NAME", "plate_fonts"), filename)


def upload_path(batch, filename):
    directory = os.path.join(getattr(settings, "PLATES_UPLOAD_DIR_NAME", "plate_uploads"), batch.public_id.hex)
    return random_name(directory, filename)


class PlateAsset(models.Model):
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=30, choices=ASSET_KINDS)
    image = models.FileField(upload_to=asset_path)
    recolourable = models.BooleanField(default=False, help_text="One-colour symbol that may be drawn in any colour")
    is_default = models.BooleanField(default=False, help_text="Used wherever a template asks for auto:<kind>")
    preset_key = models.CharField(max_length=60, blank=True, help_text="Set on rows made by seed_plate_presets")
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("kind", "name")

    def __str__(self):
        return "{} ({})".format(self.name, self.get_kind_display())

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            PlateAsset.objects.filter(kind=self.kind, is_default=True).exclude(pk=self.pk).update(is_default=False)


class PlateFont(models.Model):
    name = models.CharField(max_length=80, unique=True)
    file = models.FileField(upload_to=font_path)
    variation = models.CharField(max_length=40, blank=True, help_text="Named style of a variable font, e.g. Bold")
    preset_key = models.CharField(max_length=60, blank=True)
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class PlateTemplate(models.Model):
    name = models.CharField(max_length=120)
    plate_type = models.CharField(max_length=20, choices=PLATE_TYPES)
    output_kind = models.CharField(max_length=20, choices=OUTPUT_KINDS, default="plate")
    width_mm = models.DecimalField(max_digits=6, decimal_places=2, default=127)
    height_mm = models.DecimalField(max_digits=6, decimal_places=2, default=38.1)
    dpi = models.PositiveIntegerField(choices=DPI_CHOICES, default=600)
    mode = models.CharField(max_length=20, choices=TEMPLATE_MODES, default="designed")
    background_image = models.ForeignKey(PlateAsset, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    background = JSONField(default=dict, blank=True)
    elements = JSONField(default=list, blank=True)
    holes = JSONField(default=dict, blank=True)
    side_panel = JSONField(default=dict, blank=True)
    qr_link_pattern = models.CharField(max_length=300)
    qr_caption = models.CharField(max_length=60, blank=True, help_text="Fixed text under the QR; empty hides it")
    slum_suffix = models.CharField(max_length=40, blank=True, default=", IMC")
    version = models.PositiveIntegerField(default=1)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="versions")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    preset_key = models.CharField(max_length=60, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_on = models.DateTimeField(default=timezone.now)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("plate_type", "name", "-version")

    def __str__(self):
        return "{} (v{})".format(self.name, self.version)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            PlateTemplate.objects.filter(
                plate_type=self.plate_type, output_kind=self.output_kind, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)

    @property
    def is_latest(self):
        return not self.versions.exists()

    def spec(self):
        """The template as the plain dict the renderer reads."""
        return {
            "plate_type": self.plate_type,
            "output_kind": self.output_kind,
            "width_mm": float(self.width_mm),
            "height_mm": float(self.height_mm),
            "dpi": int(self.dpi),
            "mode": self.mode,
            "background_image": self.background_image_id,
            "background": self.background or {},
            "elements": self.elements or [],
            "holes": self.holes or {},
            "side_panel": self.side_panel or {},
            "qr_link_pattern": self.qr_link_pattern,
            "qr_caption": self.qr_caption,
            "slum_suffix": self.slum_suffix,
        }


class PlateBatch(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    template = models.ForeignKey(PlateTemplate, on_delete=models.PROTECT, related_name="batches")
    plate_type = models.CharField(max_length=20, choices=PLATE_TYPES)
    source = models.CharField(max_length=20, choices=BATCH_SOURCES, default="excel")
    upload = models.FileField(upload_to=upload_path, blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    sheet_name = models.CharField(max_length=120, blank=True)
    slum_name = models.CharField(max_length=120, blank=True, help_text="Slum of the first valid row, for subjects and names")
    city_name = models.CharField(max_length=120, blank=True)
    columns = JSONField(null=True, blank=True, help_text="Headers found in the upload")
    output_format = models.CharField(max_length=10, choices=OUTPUT_FORMATS, default="png")
    holes = models.BooleanField(default=True, help_text="Draw the template's drill holes; off makes full plates without them")
    side_panel = models.BooleanField(default=False, help_text="Add the cut-off side panel with house number and slum")

    row_count = models.IntegerField(default=0)
    made_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=BATCH_STATUSES, default="draft")
    file_path = models.CharField(max_length=1000, null=True, blank=True)
    bytes_total = models.BigIntegerField(default=0)
    failures = JSONField(null=True, blank=True, help_text='First 200 skipped rows: [{"row": 14, "reason": "..."}]')
    warnings = JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    job_request = models.ForeignKey("notification.JobRequest", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    regenerated_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    email = models.CharField(max_length=254, blank=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    confirmed_on = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    cancelled_on = models.DateTimeField(null=True, blank=True)
    created_on = models.DateTimeField(default=timezone.now)
    started_on = models.DateTimeField(null=True, blank=True)
    finished_on = models.DateTimeField(null=True, blank=True)
    delete_after = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_on",)
        verbose_name_plural = "plate batches"
        indexes = [models.Index(fields=["status", "created_on"])]

    def __str__(self):
        return "{} {} ({})".format(self.get_plate_type_display(), self.original_name or self.public_id, self.status)


class PlateActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=30, choices=ACTIVITY_ACTIONS)
    batch = models.ForeignKey(PlateBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")
    template = models.ForeignKey(PlateTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    detail = models.CharField(max_length=200, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_on",)
        verbose_name_plural = "plate activities"
        indexes = [models.Index(fields=["user", "action", "created_on"])]

    def __str__(self):
        return "{} {} {}".format(self.created_on, self.user, self.action)
