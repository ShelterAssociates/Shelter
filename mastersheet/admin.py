from django.contrib import admin
from .models import *
from .forms import VendorHouseholdInvoiceDetailForm, SBMUploadForm, ToiletConstructionForm, CommunityMobilizationForm
import datetime
from django.contrib.auth.models import User
from django.utils.html import format_html



# class CustomButton():
#     class Media:
#         js = ['js/copy_above.js']

#     def add_custom_button(self, obj):
#         print 'hello there'
#         return format_html(
#                 '<button type="button" class="btn btn-success btn-sm"  data-target="#kmlModal" href="{}">Copy above</button>'
#             )

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
    model = InvoiceItems
    fields = ['copy_above','invoice', 'material_type','phase','slum','household_numbers','quantity','unit','rate','tax','total']
    readonly_fields = ('copy_above',)
    search_fields = ('name',)
    raw_id_fields = ('slum',)
    extra = 0
    min_num = 1

    class Media:
        js = ['js/copy_above.js']

    def copy_above(self, obj):
        return '<button type="button" onclick = "copy_this(this)" class="b glyphicon glyphicon-copy" ></button>'
    copy_above.allow_tags=True

    def save_formset(self, request, form, formset, change):
        super(InvoiceItemsInline, self).save_formset(self, request, form, formset, change)
        if formset.model == InvoiceItems:
            obj = formset.instance
            if obj.reformat:
                obj.delete()
                # creating new objects
            obj.save()

    exclude = ('created_by','created_on','modified_by','modified_on',)


class InvoiceAdmin(admin.ModelAdmin):
    list_filter = ['vendor']
    list_display = ('vendor', 'invoice_number','challan_number','invoice_date')
    search_fields = ['vendor__name', 'invoice_number','challan_number','invoice_date']
    ordering = ['vendor']
    inlines = [InvoiceItemsInline]
    exclude = ('created_by','created_on','modified_by','modified_on',)


    class Media:
        js = ['js/calculate_total_invoice.js']

    def save_related(self,request, form, formset, change):        
        inst = formset[0].save(commit = False)
        for instance in inst:
            instance.created_by = request.user
            instance.modified_by = request.user
            instance.save()
        super(InvoiceAdmin, self).save_related(request, form, formset, change)
    
    def save_model(self, request, obj, form, change):
        user = User.objects.get(pk = request.user.id)
        if not obj.pk :
            obj.created_by = user
            obj.created_on = datetime.datetime.now()
        obj.modified_by = user
        obj.modified_on = datetime.datetime.now()
        obj.save()
        super(InvoiceAdmin, self).save_model(request, obj, form, change)

    def vendor_type_name(self, obj):
        return obj.vendor.name
admin.site.register(Invoice, InvoiceAdmin)


class MaterialTypeAdmin(admin.ModelAdmin):
    list_display = ('name','description','display_flag','display_order')
    search_fields = ['name']
    ordering = ['name']
admin.site.register(MaterialType, MaterialTypeAdmin)


class InvoiceItemsAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'material_type','phase','slum','household_numbers','quantity','unit','rate','tax','total')
    search_fields = ['invoice__vendor__name', 'material_type__name','slum__name', 'phase']
    ordering = ['invoice']
    exclude = ('created_by','created_on','modified_by','modified_on',)

    # def save_model(self, request, obj, form, change):
    #     print 'gotcha'
    #     super(InvoiceItemAdmin, self).save_model(request, obj, form, change)

admin.site.register(InvoiceItems, InvoiceItemsAdmin)


class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'gst_number','phone_number','email_address')
    search_fields = ['name', 'gst_number','phone_number','email_address']
    ordering = ['name']

    
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
    list_display = ('slum_name', 'household_number','agreement_date','agreement_cancelled','status','use_of_toilet','toilet_connected_to','factsheet_done')
    search_fields = ['slum__name','household_number','agreement_date','agreement_cancelled','status']
    ordering = ['slum__name','household_number']
    raw_id_fields = ['slum']
    form = ToiletConstructionForm

    def slum_name(self, obj):
        return obj.slum.name

admin.site.register(ToiletConstruction, ToiletConstructionAdmin)

class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ('name','key','display_flag','display_order')
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
