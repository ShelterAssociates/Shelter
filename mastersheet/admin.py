from django.contrib import admin
from .models import *
from .forms import VendorHouseholdInvoiceDetailForm, SBMUploadForm, ToiletConstructionForm, CommunityMobilizationForm

class BaseAdmin(admin.ModelAdmin):
    '''
        Base admin class
    '''
    def get_form(self, request, obj=None, **kwargs):
        """
        Adding request param to form. Need this to be accessed in form class for permission check 
        """
        form = super(BaseAdmin, self).get_form(request, obj=obj, **kwargs)
        form.request = request
        return form

class VendorTypeAdmin(admin.ModelAdmin):
    list_display = ('name','description','display_flag','display_order')
    search_fields = ['name']
    ordering = ['name']
admin.site.register(VendorType, VendorTypeAdmin)

class InvoiceItemsInline(admin.TabularInline):
    """Display panel of WardOfficeContacts Model"""
    model = InvoiceItems
    search_fields = ('name',)
    extra = 1


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'invoice_number','challan_number','invoice_date')
    search_fields = ['vendor', 'invoice_number','challan_number','invoice_date']
    ordering = ['vendor']
    inlines = [InvoiceItemsInline]

    def vendor_type_name(self, obj):
        return obj.vendor.name
admin.site.register(Invoice, InvoiceAdmin)


class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = ('name','description','display_flag','display_order')
    search_fields = ['name']
    ordering = ['name']
admin.site.register(MaterialType, MaterialTypeAdmin)


class InvoiceItemsAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'material_type','slum','household_numbers','quantity','unit','rate','tax','total')
    search_fields = ['invoice', 'material_type','slum']
    ordering = ['invoice']

    def vendor_type_name(self, obj):
        return obj.invoice.vendor.name
admin.site.register(InvoiceItems, InvoiceItemsAdmin)


class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor_type_name','gst_number','phone_number','email_address')
    search_fields = ['name', 'vendor_type__name', 'gst_number','phone_number','email_address']
    ordering = ['name']

    def vendor_type_name(self, obj):
        return obj.vendor_type.name
admin.site.register(Vendor, VendorAdmin)

class VendorHouseholdInvoiceDetailAdmin(BaseAdmin):
    list_display = ('vendor_name','slum_name','invoice_number','invoice_date','household_number')
    search_fields = ['invoice_number','vendor__name','slum__name', 'invoice_date', 'household_number']
    ordering = ['invoice_number']
    raw_id_fields = ['slum']
    form = VendorHouseholdInvoiceDetailForm

    class Media:
        js = ['js/mastersheet_collapse_household_code.js']

    def vendor_name(self,obj):
        return obj.vendor.name

    def slum_name(self,obj):
        return obj.slum.name

admin.site.register(VendorHouseholdInvoiceDetail, VendorHouseholdInvoiceDetailAdmin)

class SBMUploadAdmin(BaseAdmin):
    list_display = ('slum_name', 'household_number', 'name','application_id','photo_uploaded','photo_verified','photo_approved',
                    'application_verified','application_approved')
    search_fields = ['slum__name','household_number', 'name','application_id','photo_uploaded','photo_verified','photo_approved',
                    'application_verified','application_approved']
    ordering = ['slum__name', 'household_number']
    raw_id_fields = ['slum']
    form = SBMUploadForm

    def slum_name(self, obj):
        return obj.slum.name
admin.site.register(SBMUpload, SBMUploadAdmin)

class ToiletConstructionAdmin(BaseAdmin):
    list_display = ('slum_name', 'household_number','agreement_date','agreement_cancelled','status')
    search_fields = ['slum__name','household_number','agreement_date','agreement_cancelled','status']
    ordering = ['slum__name','household_number']
    raw_id_fields = ['slum']
    form = ToiletConstructionForm

    def slum_name(self, obj):
        return obj.slum.name

admin.site.register(ToiletConstruction, ToiletConstructionAdmin)

class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name','display_flag','display_order')
    search_fields = ['name']
    ordering = ['name']
admin.site.register(ActivityType, ActivityTypeAdmin)

class CommunityMobilizationAdmin(BaseAdmin):
    list_display = ('slum_name','household_number', 'activity_type_name','activity_date')
    search_fields = ['slum__name','household_number', 'activity_type__name','activity_date']
    raw_id_fields = ['slum']
    form = CommunityMobilizationForm

    def activity_type_name(self, obj):
        return obj.activity_type.name

    def slum_name(self, obj):
        return obj.slum.name

    class Media:
        js = ['js/mastersheet_collapse_household_code.js']

admin.site.register(CommunityMobilization, CommunityMobilizationAdmin)

admin.site.register(KoboDDSyncTrack)
