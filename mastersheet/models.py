from django.db import models
from master.models import City, Slum
from jsonfield import JSONField
import datetime

class VendorType(models.Model):
    name = models.CharField(max_length=512)
    description = models.TextField(null=True, blank=True)
    display_flag = models.BooleanField()
    display_order = models.FloatField()
    created_date = models.DateTimeField(default=datetime.datetime.now())

    class Meta:
        verbose_name = 'Vendor type'
        verbose_name_plural = 'Vendor types'

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

class Vendor(models.Model):
    name = models.CharField(max_length=512)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    email_address = models.CharField(max_length=512, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    vendor_type = models.ForeignKey(VendorType)
    gst_number = models.CharField(max_length=100)
    city = models.ForeignKey(City)
    created_date = models.DateTimeField(default=datetime.datetime.now())

    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name + '(' + self.vendor_type.name + ')'

class VendorHouseholdInvoiceDetail(models.Model):
    vendor = models.ForeignKey(Vendor)
    slum = models.ForeignKey(Slum)
    invoice_number = models.CharField(max_length=100)
    invoice_date = models.DateField()
    household_number = JSONField(null=True, blank=True)
    created_date = models.DateTimeField(default=datetime.datetime.now())

    class Meta:
        unique_together = ("slum", "invoice_number")
        verbose_name = 'Vendor to household invoice detail'
        verbose_name_plural = 'Vendor to household invoice details'

    def __unicode__(self):
        return self.vendor.name + ' - '+ self.slum.name + '(' + self.invoice_number + ')'

class SBMUpload(models.Model):
    slum = models.ForeignKey(Slum)
    household_number = models.CharField(max_length=5)
    name = models.CharField(max_length=512)
    application_id = models.CharField(max_length=512)
    photo_uploaded = models.BooleanField(default=False)
    created_date = models.DateTimeField(default=datetime.datetime.now())

    class Meta:
        unique_together = ("slum", "household_number")
        verbose_name = 'SBM application upload'
        verbose_name_plural = 'SBM application uploads'

    def __unicode__(self):
        return self.name

STATUS_CHOICES=(('1', 'Agreement done'),
                ('2', 'Agreement cancel'),
                ('3', 'Material not given'),
                ('4', 'Construction not started'),
                ('5', 'Under construction'),
                ('6', 'completed'))

class ToiletConstruction(models.Model):
    slum = models.ForeignKey(Slum)
    household_number = models.CharField(max_length=5)
    agreement_date = models.DateField()
    agreement_cancelled = models.BooleanField(default=False)
    septic_tank_date = models.DateField(null=True, blank=True)
    phase_one_material_date = models.DateField(null=True, blank=True)
    phase_two_material_date = models.DateField(null=True, blank=True)
    phase_three_material_date = models.DateField(null=True, blank=True)
    completion_date =  models.DateField(null=True, blank=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=2)
    comment = models.TextField(null=True, blank=True)
    material_shifted_to = models.CharField(max_length=5, null=True, blank=True)

    class Meta:
        unique_together = ("slum", "household_number")
        verbose_name = 'Toilet construction progress'
        verbose_name_plural = 'Toilet construction progress'

class ActivityType(models.Model):
    name = models.CharField(max_length=512)
    key = models.CharField(max_length=2)
    display_flag = models.BooleanField(default=False)
    display_order = models.FloatField()

    class Meta:
        verbose_name = 'Activity type'
        verbose_name_plural = 'Activity types'

    def __unicode__(self):
        return self.name

class CommunityMobilization(models.Model):
    slum = models.ForeignKey(Slum)
    household_number = JSONField(null=True, blank=True)
    activity_type = models.ForeignKey(ActivityType)
    activity_date = models.DateField()

    class Meta:
        unique_together = ("slum", "activity_type")
        verbose_name = 'Community mobilization'
        verbose_name_plural = 'Community mobilization'

    def __unicode__(self):
        return self.slum.name