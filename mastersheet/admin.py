from django.contrib import admin
from .models import *

class VendorTypeAdmin(admin.ModelAdmin):
    list_display = ('name','description','display_flag','display_order')
    search_fields = ['name']
    ordering = ['name']
admin.site.register(VendorType, VendorTypeAdmin)

class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor_type_name','gst_number','phone_number','email_address')
    search_fields = ['name', 'vendor_type__name', 'gst_number','phone_number','email_address']
    ordering = ['name']

    def vendor_type_name(self, obj):
        return obj.vendor_type.name
admin.site.register(Vendor, VendorAdmin)

class VendorHouseholdInvoiceDetailAdmin(admin.ModelAdmin):
    list_display = ('vendor_name','slum_name','invoice_number','invoice_date','household_number')
    search_fields = ['invoice_number','vendor__name','slum__name', 'invoice_date', 'household_number']
    ordering = ['invoice_number']
    raw_id_fields = ['slum']

    class Media:
        js = ['js/mastersheet_collapse_household_code.js']

    def vendor_name(self,obj):
        return obj.vendor.name

    def slum_name(self,obj):
        return obj.slum.name

admin.site.register(VendorHouseholdInvoiceDetail, VendorHouseholdInvoiceDetailAdmin)

class SBMUploadAdmin(admin.ModelAdmin):
    list_display = ('slum_name', 'household_number', 'name','application_id','photo_uploaded','photo_verified','photo_approved',
                    'application_verified','application_approved')
    search_fields = ['slum_name','household_number', 'name','application_id','photo_uploaded','photo_verified','photo_approved',
                    'application_verified','application_approved']
    ordering = ['slum__name', 'household_number']
    raw_id_fields = ['slum']

    def slum_name(self, obj):
        return obj.slum.name
admin.site.register(SBMUpload, SBMUploadAdmin)

class ToiletConstructionAdmin(admin.ModelAdmin):
    list_display = ('slum_name', 'household_number','agreement_date','agreement_cancelled','status','material_shifted_to')
    search_fields = ['slum__name','household_number','agreement_date','agreement_cancelled','status','material_shifted_to']
    ordering = ['slum__name','household_number']
    raw_id_fields = ['slum']

    def slum_name(self, obj):
        return obj.slum.name

admin.site.register(ToiletConstruction, ToiletConstructionAdmin)

class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name','display_flag','display_order')
    search_fields = ['name']
    ordering = ['name']
admin.site.register(ActivityType, ActivityTypeAdmin)

class CommunityMobilizationAdmin(admin.ModelAdmin):
    list_display = ('slum_name','household_number', 'activity_type_name','activity_date')
    search_fields = ['slum__name','household_number', 'activity_type__name','activity_date']
    raw_id_fields = ['slum']

    def activity_type_name(self, obj):
        return obj.activity_type.name

    def slum_name(self, obj):
        return obj.slum.name

    class Media:
        js = ['js/mastersheet_collapse_household_code.js']

admin.site.register(CommunityMobilization, CommunityMobilizationAdmin)