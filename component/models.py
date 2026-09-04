from django.contrib.gis.db import models

# from picklefield.fields import PickledObjectField
from jsonfield import JSONField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

METRIC_UNIT_CHOICES = (
    ("m", "Meters"),
    ("km", "Kilometers"),
    ("count", "Count"),
    ("other", "Other"),
)

DISPLAY_TYPE_CHOICES = (
    ("M", "Map"),
    ("T", "Tabular"),
)
LEVEL_CHOICES = (
    ("C", "City"),
    ("S", "Slum"),
    ("H", "Household"),
)
META_TYPE_CHOICES = (
    ("C", "Component"),
    ("F", "Filter"),
    ("S", "Sponsor"),
)
COMPONENT_ICON = "componentIcons/"


class Section(models.Model):
    """Section data"""

    name = models.CharField(max_length=2048)
    order = models.FloatField()

    def __str__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Section of the components"""

        verbose_name = "Section"
        verbose_name_plural = "Sections"
        permissions = [
            ("can_refresh_section", "Can refresh sections"),
        ]


class Metadata(models.Model):
    """Metadata of component and analysis"""

    # def validate_image(fieldfile_obj):
    #     filesize = fieldfile_obj.file.size
    #     megabyte_limit = 1.0
    #     if filesize > megabyte_limit*1024*1024:
    #         raise ValidationError("Max file size is %sMB" % str(megabyte_limit))
    name = models.CharField(max_length=2048)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    level = models.CharField(max_length=1, choices=LEVEL_CHOICES)  # slum/household
    type = models.CharField(max_length=1, choices=META_TYPE_CHOICES)  # component/filter
    display_type = models.CharField(
        max_length=1, choices=DISPLAY_TYPE_CHOICES
    )  # map/table
    visible = models.BooleanField()  # BooleanField
    authenticate = models.BooleanField(default=False)
    show_metric = models.BooleanField(default=True)  # show count/length badge on the feature box
    order = models.FloatField()
    blob = JSONField()
    icon = models.ImageField(upload_to=COMPONENT_ICON, blank=True, null=True)
    code = models.CharField(max_length=512, blank=True, null=True)

    def __str__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Component metadata"""

        verbose_name = "Metadata"
        verbose_name_plural = "Metadata"


def get_default_slum_content_type():
    return ContentType.objects.get(model="slum")


# Create your models here.
class Component(models.Model):
    """Drawable Component Database"""

    metadata = models.ForeignKey(Metadata, on_delete=models.CASCADE)
    housenumber = models.CharField(max_length=100)
    shape = models.GeometryField(srid=4326)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, default=get_default_slum_content_type
    )

    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return (
            self.content_type.model
            + " - "
            + self.metadata.name
            + ":"
            + self.housenumber
        )


class ComponentMetric(models.Model):
    """Manually-entered metric (length, count, etc.) for one component type
    within one slum. Uploading/re-uploading a KML for a slum replaces
    exactly one component type's ("layer") worth of components at a time,
    so a metric override is scoped the same way — one row per (slum,
    metadata) pair. If no row exists here, the value is auto-calculated
    from geometry (see component.services.helper.compute_auto_metric)
    instead of ever being hardcoded.

    A "reason" is required to create/update this (enforced in the view),
    same as component delete, but — also same as delete — the reason is
    only ever emailed, never stored here.
    """

    slum = models.ForeignKey(
        "master.Slum", on_delete=models.CASCADE, related_name="component_metrics"
    )
    metadata = models.ForeignKey(Metadata, on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=16, choices=METRIC_UNIT_CHOICES)
    unit_label = models.CharField(max_length=32, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("slum", "metadata")

    def __str__(self):
        return "{} - {}: {} {}".format(
            self.slum.name, self.metadata.name, self.value, self.unit
        )
