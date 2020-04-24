
from django.contrib.gis.db import models
#from picklefield.fields import PickledObjectField
from jsonfield import JSONField
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

DISPLAY_TYPE_CHOICES = (
        ('M', 'Map'),
        ('T', 'Tabular'),
    )
LEVEL_CHOICES  = (
        ('C', 'City'),
        ('S', 'Slum'),
        ('H', 'Household'),
    )
META_TYPE_CHOICES = (
        ('C', 'Component'),
        ('F', 'Filter'),
        ('S', 'Sponsor'),
    )
COMPONENT_ICON = "componentIcons/"


class Section(models.Model):
    """Section data"""
    name  = models.CharField(max_length=2048)
    order  = models.FloatField()

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Section of the components"""
        verbose_name = 'Section'
        verbose_name_plural = 'Sections'

class Metadata(models.Model):
    """Metadata of component and analysis"""
    # def validate_image(fieldfile_obj):
    #     filesize = fieldfile_obj.file.size
    #     megabyte_limit = 1.0
    #     if filesize > megabyte_limit*1024*1024:
    #         raise ValidationError("Max file size is %sMB" % str(megabyte_limit))
    name = models.CharField(max_length=2048)
    section = models.ForeignKey(Section)
    level  = models.CharField(max_length=1, choices=LEVEL_CHOICES) # slum/household
    type  = models.CharField(max_length=1, choices=META_TYPE_CHOICES) # component/filter
    display_type  = models.CharField(max_length=1, choices=DISPLAY_TYPE_CHOICES) #map/table
    visible  = models.BooleanField() # BooleanField
    authenticate = models.BooleanField(default=False)
    order  = models.FloatField()
    blob  = JSONField()
    icon = models.ImageField(upload_to=COMPONENT_ICON ,blank=True, null=True)
    code = models.CharField(max_length=512,blank=True,null=True)

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Component metadata"""
        verbose_name = 'Metadata'
        verbose_name_plural = 'Metadata'

# Create your models here.
class Component(models.Model):
    """Drawable Component Database"""
    metadata = models.ForeignKey(Metadata)
    housenumber = models.CharField(max_length=100)
    shape = models.GeometryField(srid=4326)
    content_type = models.ForeignKey(ContentType, default=ContentType.objects.get(model='slum').id, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField() #Fields for reverse relationship with slum and city table
    content_object = GenericForeignKey('content_type','object_id')
    objects = models.GeoManager()

    def __unicode__(self):
        """Returns string representation of object"""
        return self.content_type.model + ' - '+ self.metadata.name + ':'+ self.housenumber

    class Meta:
        """Metadata for class Component"""
        permissions = (
            ("can_upload_KML", "Can upload KML file"),
        )
        verbose_name = 'Component'
        verbose_name_plural = 'Components'
