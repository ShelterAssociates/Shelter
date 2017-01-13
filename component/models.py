from django.contrib.gis.db import models
from master.models import Slum
#from picklefield.fields import PickledObjectField
from jsonfield import JSONField

DISPLAY_TYPE_CHOICES = (
        ('M', 'Map'),
        ('T', 'Tabular'),
    )
LEVEL_CHOICES  = (
        ('S', 'Slum'),
        ('H', 'Household'),
    )
META_TYPE_CHOICES = (
        ('C', 'Component'),
        ('F', 'Filter'),
    )
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
    name = models.CharField(max_length=2048)
    section = models.ForeignKey(Section)
    level  = models.CharField(max_length=1, choices=LEVEL_CHOICES) # slum/household
    type  = models.CharField(max_length=1, choices=META_TYPE_CHOICES) # component/filter
    display_type  = models.CharField(max_length=1, choices=DISPLAY_TYPE_CHOICES) #map/table
    visible  = models.BooleanField() # BooleanField
    order  = models.FloatField()
    blob  = JSONField()
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
    housenumber = models.CharField(max_length=5)
    shape = models.GeometryField(srid=4326)
    slum  = models.ForeignKey(Slum)
    objects = models.GeoManager()

    def __unicode__(self):
        """Returns string representation of object"""
        return self.metadata.name

    class Meta:
        """Metadata for class Component"""
        verbose_name = 'Component'
        verbose_name_plural = 'Components'

class Fact(models.Model):
    """Fact analysis data"""
    metadata  = models.ForeignKey(Metadata)
    slum  = models.ForeignKey(Slum)
    blob  = JSONField()

    def __unicode__(self):
        """Returns string representation of object"""
        return self.slum.name

    class Meta:
        """Metadata for class Fact"""
        verbose_name = 'Fact'
        verbose_name_plural = 'Fact'
