from django.db import models
from django.contrib.auth.models import User
from django.contrib import messages
from master.models import City, Slum
from jsonfield import JSONField
import datetime
from datetime import date
import pandas
import django.dispatch
from django.db.models.signals import pre_save,post_save
from django.dispatch import receiver





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
    gst_number = models.CharField(max_length=100)
    city = models.ForeignKey(City)
    created_date = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name 

class VendorHouseholdInvoiceDetail(models.Model):
    """
    Account invoice details with respective household numbers.
    """
    vendor = models.ForeignKey(Vendor)
    slum = models.ForeignKey(Slum)
    invoice_number = models.CharField(max_length=100)
    invoice_date = models.DateField()
    household_number = JSONField(null=True, blank=True)
    quantity = models.CharField(max_length=100, null=True, blank=True)
    amount = models.CharField(max_length=100, null=True, blank=True)
    created_date = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        unique_together = ("vendor","slum", "invoice_number")
        verbose_name = 'Vendor to household invoice detail'
        verbose_name_plural = 'Vendor to household invoice details'

    def __unicode__(self):
        return self.vendor.name + ' - '+ self.slum.name + '(' + self.invoice_number + ')'

class Invoice(models.Model):
    vendor = models.ForeignKey(Vendor)
    invoice_date = models.DateField(null=True, blank=True)
    invoice_number = models.CharField(max_length=100,null=True, blank=True)
    challan_number = models.CharField(max_length=100,null=True, blank=True)
    total = models.FloatField(default = 0)
    loading_unloading_charges = models.FloatField(default = 0)
    transport_charges = models.FloatField(default = 0)
    roundoff = models.FloatField(default = 0)
    final_total = models.FloatField(default = 0)
    paid = models.BooleanField(default=False)
    created_on = models.DateTimeField(default=datetime.datetime.now)
    created_by = models.ForeignKey(User,related_name='invoice_created_by')
    modified_on = models.DateTimeField(default=datetime.datetime.now)
    modified_by = models.ForeignKey(User, related_name='invoice_modified_by')

    class Meta:
        unique_together = ("vendor", "invoice_number")
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def __unicode__(self):
        """Returns string representation of object"""
        return self.vendor.name + '(' + self.invoice_number + ')' 
    


class MaterialType(models.Model):
    name = models.CharField(max_length=512)
    description = models.TextField(null=True, blank=True)
    display_flag = models.BooleanField()
    display_order = models.FloatField()
    created_date = models.DateTimeField(default=datetime.datetime.now)
    

    class Meta:
        verbose_name = 'Material Type'
        verbose_name_plural = 'Material Types'

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name
        
UNITS=(('1', 'Tempo/Piago'),
                ('2', 'Bags'),
                ('3', 'Nos'))
PHASE = (('1', 'Phase One'),
            ('2', 'Phase Two'),
            ('3', 'Phase Three'))


class InvoiceItems(models.Model):
    invoice = models.ForeignKey(Invoice)
    material_type = models.ForeignKey(MaterialType)
    slum = models.ForeignKey(Slum)
    household_numbers = JSONField()
    phase = models.CharField(max_length=2, choices = PHASE,null=True, blank=True)
    quantity = models.FloatField(default = 0)
    unit = models.CharField(max_length=100,choices = UNITS,null=True, blank=True)
    rate = models.FloatField(default = 0)
    tax = models.FloatField(default = 0)
    total = models.FloatField(default = 0)
    created_on = models.DateTimeField(default=datetime.datetime.now)
    created_by = models.ForeignKey(User, related_name='invoiceitem_created_by')
    modified_on = models.DateTimeField(default=datetime.datetime.now)
    modified_by = models.ForeignKey(User, related_name='invoiceitem_modified_by')

    class Meta:
        verbose_name = 'Invoice item'
        verbose_name_plural = 'Invoice items'

    def __unicode__(self):
        """Returns string representation of object"""
        return self.material_type.name

class SBMUpload(models.Model):
    """
    SBM upload detials
    """
    slum = models.ForeignKey(Slum)
    household_number = models.CharField(max_length=5)
    name = models.CharField(max_length=512)
    application_id = models.CharField(max_length=512,null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    aadhar_number = models.CharField(max_length=15, null=True, blank=True)
    photo_uploaded = models.BooleanField(default=False)
    photo_verified = models.BooleanField(default=False)
    photo_approved = models.BooleanField(default=False)
    application_verified = models.BooleanField(default=False)
    application_approved = models.BooleanField(default=False)
    sbm_comment = models.TextField(null=True, blank=True)
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
                ('6', 'Completed'),
                ('7', 'Written-off'))

class ToiletConstruction(models.Model):
    """
    Toilet construction track of dates at each level of construction.
    """
    slum = models.ForeignKey(Slum)
    household_number = models.CharField(max_length=5)
    pocket = models.IntegerField(null=True, blank=True)
    agreement_date = models.DateField(null=True, blank=True)
    agreement_cancelled = models.NullBooleanField(null=True, blank=True)
    septic_tank_date = models.DateField(null=True, blank=True)
    phase_one_material_date = models.DateField(null=True, blank=True)
    phase_two_material_date = models.DateField(null=True, blank=True)
    phase_three_material_date = models.DateField(null=True, blank=True)
    completion_date =  models.DateField(null=True, blank=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=2,null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    p1_material_shifted_to = models.CharField(max_length=5, null=True, blank=True)
    p2_material_shifted_to = models.CharField(max_length=5, null=True, blank=True)
    p3_material_shifted_to = models.CharField(max_length=5, null=True, blank=True)
    st_material_shifted_to = models.CharField(max_length=5, null=True, blank=True)
    use_of_toilet = models.DateField(null=True, blank=True)
    toilet_connected_to = models.DateField(null=True, blank=True)
    factsheet_done = models.DateField(null=True, blank=True)

    class Meta:
        permissions = (
            ("can_view_mastersheet", "Can view the mastersheet"),
            ("can_sync_toilet_status", "Can sync toilet status"),
            ("can_upload_mastersheet", "Can upload mastersheet"),
            ("can_delete_kobo_record", "Can delete kobo record"),
            ("can_view_mastersheet_report", "Can view mastersheet report"),
            ("can_export_mastersheet_report", "Can export mastersheet report"),

        )
        unique_together = ("slum", "household_number")
        verbose_name = 'Toilet construction progress'
        verbose_name_plural = 'Toilet construction progress'

    def __str__(self):
        return str(self.household_number) +", "+ str(self.slum)
    @staticmethod
    def get_status_display(z):
        return STATUS_CHOICES[int(z)-1][1]
    @staticmethod
    def check_bool(s):
        if str(s).lower() == 'yes' or str(s).lower() == "true":
            return True
        else:
            return False


    def update_model(self, df1):
        
        if check_bool(df1.loc['Agreement Cancelled']) is not False:
            self.agreement_cancelled = True
        else:
            self.agreement_cancelled = False

        if not self.agreement_date:
            self.agreement_date = df1.loc['Date of Agreement'] if pandas.isnull(df1.loc['Date of Agreement']) is False else None


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

        if not self.pocket:
            self.pocket = df1.loc['Pocket'] if pandas.isnull(df1.loc['Pocket']) is False else None

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
        unique_together = ("slum", "activity_type","activity_date")
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

    class Meta:
        unique_together = ("slum", "sync_date")
        verbose_name = 'KoBo daily reporting sync'
        verbose_name_plural = 'KoBo daily reporting sync'

    def __unicode__(self):
        return self.slum.name + '-' + str(self.sync_date)
@receiver(pre_save, sender=ToiletConstruction)
def update_status(sender ,instance, **kwargs):
    #instance.status = STATUS_CHOICES[4][0]#Under Construction
    if instance.status != STATUS_CHOICES[6][0]:
        if instance.agreement_cancelled is None:
            instance.status = ""
        if instance.agreement_date is None:
            instance.status = ""
        if instance.agreement_date:
            instance.status = STATUS_CHOICES[2][0]#material not given
        
        
        '''
            The method below is put in place because some unexpected data format ('Timestamp') was found with some
            agreement_date. The method covers inconsistencies only for agreement date. Requirement may arise in furture 
            to inculcate other date fields also.  
        '''
        if type(instance.agreement_date) != datetime.date and instance.agreement_date:
            instance.agreement_date = instance.agreement_date.to_datetime()
            instance.agreement_date = instance.agreement_date.date()


        if (instance.phase_one_material_date is None) and instance.agreement_date and (datetime.date.today() - instance.agreement_date > datetime.timedelta(days=8)):
            instance.status = STATUS_CHOICES[2][0]#material not given

        if instance.phase_one_material_date or instance.phase_two_material_date or instance.phase_three_material_date:
            instance.status = STATUS_CHOICES[4][0]#Under Construction

        if instance.completion_date:
            instance.status = STATUS_CHOICES[5][0]#completed
            
        if instance.agreement_cancelled :
            instance.status = STATUS_CHOICES[1][0]#agreement cancelled

    

    #if instance.p1_material_shifted_to is not None and instance.p2_material_shifted_to is not None instance.p3_material_shifted_to is not None instance.st_material_shifted_to is not None:
        #if len(instance.p1material_shifted_to) != 0 and len(instance.p2material_shifted_to) != 0 and len(instance.p3material_shifted_to) != 0 and len(instance.st_material_shifted_to) != 0:
            #instance.status = STATUS_CHOICES[1][0]#agreement cancelled



@receiver(pre_save, sender=ToiletConstruction)
def handle_shifted_material(sender ,instance, **kwargs):
    temp = {}
    temp['slum'] = instance.slum
    temp['defaults'] = {'agreement_cancelled' : False}
    temp['flag'] = False

    
    if instance.p1_material_shifted_to is not None:
        flag = True
        try:
            hh_does_exist = ToiletConstruction.objects.get(slum = instance.slum, household_number = instance.p1_material_shifted_to)
            if hh_does_exist.phase_one_material_date:
                flag = False
        except Exception as e:
            pass
        if flag and len(instance.p1_material_shifted_to)!=0 and instance.phase_one_material_date is not None:
            temp['flag'] = True
            temp['household_number'] = int(instance.p1_material_shifted_to)
            temp['defaults']['phase_one_material_date'] = instance.phase_one_material_date
            instance.phase_one_material_date = None

    if instance.p2_material_shifted_to is not None:
        flag = True
        try:
            hh_does_exist = ToiletConstruction.objects.get(slum = instance.slum, household_number = instance.p2_material_shifted_to)
            if hh_does_exist.phase_two_material_date:
                flag = False
        except Exception as e:
            pass
        if flag and len(instance.p2_material_shifted_to)!=0 and instance.phase_two_material_date is not None:
            temp['flag'] = True
            temp['household_number'] = int(instance.p2_material_shifted_to)
            temp['defaults']['phase_two_material_date'] = instance.phase_two_material_date
            instance.phase_two_material_date = None
            
    if instance.p3_material_shifted_to is not None:
        flag = True
        try:
            hh_does_exist = ToiletConstruction.objects.get(slum = instance.slum, household_number = instance.p3_material_shifted_to)
            if hh_does_exist.phase_three_material_date:
                flag = False
        except Exception as e:
            pass
        if flag and len(instance.p3_material_shifted_to)!=0 and instance.phase_three_material_date is not None:
            temp['flag'] = True
            temp['household_number'] = int(instance.p3_material_shifted_to)
            temp['defaults']['phase_three_material_date'] = instance.phase_three_material_date
            instance.phase_three_material_date = None
            
    if instance.st_material_shifted_to is not None:
        flag = True
        try:
            hh_does_exist = ToiletConstruction.objects.get(slum = instance.slum, household_number = instance.st_material_shifted_to)
            if hh_does_exist.phase_septic_tank_material_date:
                flag = False
        except Exception as e:
            pass
        if flag and len(instance.st_material_shifted_to)!=0 and instance.septic_tank_date is not None:
            temp['flag'] = True
            temp['household_number'] = int(instance.st_material_shifted_to)
            temp['defaults']['phase_three_material_date'] = instance.septic_tank_date
            instance.septic_tank_date = None
            
    if temp['flag']:
        del(temp['flag'])
        TC_instance, is_created = ToiletConstruction.objects.update_or_create(**temp)
        TC_instance.save()
        print is_created

    


@receiver(pre_save, sender = InvoiceItems)
def check_duplicate_house(sender, instance, **kwargs):
    if instance.id is not None:
        all_records = InvoiceItems.objects.filter(slum = instance.slum).exclude(id = instance.id)
    else:
        all_records = InvoiceItems.objects.filter(slum = instance.slum)

    for record in all_records:
        if record.material_type == instance.material_type:
            common_households = list(set(record.household_numbers).intersection(instance.household_numbers))
            if len(common_households) != 0:
                    raise Exception("household numbers "+str(common_households)+ " are repeated in " +str(record.invoice)+ " and "+str(instance.invoice))
                    #messages.error(request, "household numbers "+str(common_households)+ " are repeated in " +str(record.vendor.name)+ " and "+instance.vendor.name)
                    #return Exception("household numbers "+str(common_households)+ " are repeated in " +str(record.vendor.name)+ " and "+instance.vendor.name)

def check_bool(s):
        if str(s).lower() == 'yes' or str(s).lower() == "true":
            return True
        else:
            return False
