from django.contrib import admin
from .models import *

admin.site.register(VendorType)
admin.site.register(Vendor)
admin.site.register(VendorHouseholdInvoiceDetail)
admin.site.register(SBMUpload)
admin.site.register(ToiletConstruction)
admin.site.register(ActivityType)
admin.site.register(CommunityMobilization)