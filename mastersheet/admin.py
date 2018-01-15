from django.contrib import admin
from .models import *

class VendorTypeAdmin(admin.ModelAdmin):
    search_fields = ['name']
admin.site.register(VendorType, VendorTypeAdmin)

class VendorAdmin(admin.ModelAdmin):
    search_fields = ['name']
admin.site.register(Vendor, VendorAdmin)

class VendorHouseholdInvoiceDetailAdmin(admin.ModelAdmin):
    search_fields = ['invoice_number']
    raw_id_fields = ['slum']
admin.site.register(VendorHouseholdInvoiceDetail, VendorHouseholdInvoiceDetailAdmin)

class SBMUploadAdmin(admin.ModelAdmin):
    search_fields = ['name']
    raw_id_fields = ['slum']
admin.site.register(SBMUpload, SBMUploadAdmin)

class ToiletConstructionAdmin(admin.ModelAdmin):
    search_fields = ['household_number']
    raw_id_fields = ['slum']
admin.site.register(ToiletConstruction, ToiletConstructionAdmin)

class ActivityTypeAdmin(admin.ModelAdmin):
    search_fields = ['name']
admin.site.register(ActivityType, ActivityTypeAdmin)

class CommunityMobilizationAdmin(admin.ModelAdmin):
    raw_id_fields = ['slum']
admin.site.register(CommunityMobilization, CommunityMobilizationAdmin)