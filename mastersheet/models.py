from django.db import models
from django.contrib.auth.models import User
from master.models import City, Slum
from jsonfield import JSONField
import datetime
import pandas

class VendorType(models.Model):
    """
    All the type of vendors.
    """
    name = models.CharField(max_length=512)
    description = models.TextField(null=True, blank=True)
    display_flag = models.BooleanField()
    display_order = models.FloatField()
    created_date = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        verbose_name = 'Vendor type'
        verbose_name_plural = 'Vendor types'

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

class Vendor(models.Model):
    """
    Vendor name accordingly to the vendor types.
    """
    name = models.CharField(max_length=512)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    email_address = models.CharField(max_length=512, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    vendor_type = models.ForeignKey(VendorType)
    gst_number = models.CharField(max_length=100)
    city = models.ForeignKey(City)
    created_date = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name + '(' + self.vendor_type.name + ')'

class VendorHouseholdInvoiceDetail(models.Model):
    """
    Account invoice details with respective household numbers.
    """
    vendor = models.ForeignKey(Vendor)
    slum = models.ForeignKey(Slum)
    invoice_number = models.CharField(max_length=100)
    invoice_date = models.DateField()
    household_number = JSONField(null=True, blank=True)
    created_date = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        unique_together = ("vendor","slum", "invoice_number")
        verbose_name = 'Vendor to household invoice detail'
        verbose_name_plural = 'Vendor to household invoice details'

    def __unicode__(self):
        return self.vendor.name + ' - '+ self.slum.name + '(' + self.invoice_number + ')'

class SBMUpload(models.Model):
    """
    SBM upload detials
    """
    slum = models.ForeignKey(Slum)
    household_number = models.CharField(max_length=5)
    name = models.CharField(max_length=512)
    application_id = models.CharField(max_length=512)
    photo_uploaded = models.BooleanField(default=False)
    created_date = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        unique_together = ("slum", "household_number")
        verbose_name = 'SBM application upload'
        verbose_name_plural = 'SBM application uploads'

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.household_number

STATUS_CHOICES=(('1', 'Agreement done'),
                ('2', 'Agreement cancel'),
                ('3', 'Material not given'),
                ('4', 'Construction not started'),
                ('5', 'Under construction'),
                ('6', 'completed'))

class ToiletConstruction(models.Model):
    """
    Toilet construction track of dates at each level of construction.
    """
    slum = models.ForeignKey(Slum)
    household_number = models.CharField(max_length=5)
    agreement_date = models.DateField(default=datetime.datetime.now)
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

    def __str__(self):
        return self.household_number


    def update_model(self, df1):
        if pandas.isnull(df1.loc['Agreement Cancelled']) is False:
            self.agreement_cancelled = True
        else:
            self.agreement_cancelled = False

        if not self.septic_tank_date:
            self.septic_tank_date = df1.loc['Date of Septic Tank supplied'] if pandas.isnull(df1.loc['Date of Septic Tank supplied']) is False else None

        if not self.phase_one_material_date:
            self.phase_one_material_date = df1.loc['Material Supply Date 1st'] if pandas.isnull(df1.loc['Material Supply Date 1st']) is False else None

        if not self.phase_two_material_date:
            self.phase_two_material_date = df1.loc['Material Supply Date-2nd'] if pandas.isnull(df1.loc['Material Supply Date-2nd']) is False else None

        if not self.phase_three_material_date:
            self.phase_three_material_date = df1.loc['Material Supply Date-3rd'] if pandas.isnull(df1.loc['Material Supply Date-3rd']) is False else None

        if not self.completion_date:
            self.completion_date = df1.loc['Construction Completion Date'] if pandas.isnull(df1.loc['Construction Completion Date']) is False else None

        if not self.comment:
            self.comment = df1.loc['Comment']

        stat = df1.loc['Final Status']
        for j in range(len(STATUS_CHOICES)):
            if str(STATUS_CHOICES[j][1]).lower() == str(stat).lower():
                self.status = STATUS_CHOICES[j][0]

        self.save()

    def check_n(self, s):
        if pandas.isnull(s):
            return None
        else:
            return s

class ActivityType(models.Model):
    """
    Types of Community mobilization activities
    """
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
    """
    Track of household that were present for that particular mobilization activity.
    """
    slum = models.ForeignKey(Slum)
    household_number = JSONField(null=True, blank=True)
    activity_type = models.ForeignKey(ActivityType)
    activity_date = models.DateField(default=datetime.datetime.now)

    class Meta:
        unique_together = ("slum", "activity_type")
        verbose_name = 'Community mobilization'
        verbose_name_plural = 'Community mobilization'

    def __unicode__(self):
        return self.slum.name + '-' + self.activity_type.name

class KoboDDSyncTrack(models.Model):
    """
    Sync date track for each slum. The data will be pulled from kobotoolbox and accordingly date will be updated.
    """
    slum = models.ForeignKey(Slum)
    sync_date = models.DateTimeField()
    created_on = models.DateTimeField(default=datetime.datetime.now)
    created_by = models.ForeignKey(User)

    def __unicode__(self):
        return self.slum.name + '-' + self.sync_date