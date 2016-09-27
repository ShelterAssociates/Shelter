#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Admin Page for master app"""
from django.contrib import admin
from django.contrib.gis import admin
from master.models import CityReference, City, \
    AdministrativeWard, ElectoralWard, Slum, WardOfficeContact, ElectedRepresentative, Rapid_Slum_Appraisal, Survey
from master.forms import CityFrom, AdministrativeWardFrom, ElectoralWardForm, SlumForm

# Register your models here.
admin.site.register(WardOfficeContact)
# admin.site.register(ProjectMaster)
# admin.site.register(ShapeCode)
# admin.site.register(DrawableComponent)
# admin.site.register(RoleMaster)
admin.site.register(ElectedRepresentative)
# admin.site.register(UserRoleMaster)

class CityReferenceAdmin(admin.ModelAdmin):
    """Display panel of CityReference Model"""
    list_display = (
        'city_name',
        'city_code',
        'district_name',
        'district_code',
        'state_name',
        'state_code',
        )
    search_fields = ('city_name',)


admin.site.register(CityReference, CityReferenceAdmin)

class WardOfficeContactInline(admin.TabularInline):
    """Display panel of WardOfficeContacts Model"""
    model = WardOfficeContact
    search_fields = ('name',)

class ElectedRepresentativeInline(admin.TabularInline):
    """Display panel of ElectedRepresentative Model"""
    model = ElectedRepresentative
    search_fields = ('name',)

class ElectedRepresentativeAdmin(admin.ModelAdmin):
    """Display panel of ElectedRepresentativeAdmin Model"""
    list_display = ('name', 'ward_no', 'ward_code',
                    'administrative_ward')
    search_fields = ('name',)
    inlines = [ElectedRepresentativeInline]

admin.site.register(ElectoralWard, ElectedRepresentativeAdmin)

class SlumDetailAdmin(admin.ModelAdmin):
    form = SlumForm
    search_fields = ('name',)
admin.site.register(Slum, SlumDetailAdmin)

# class SurveyDetailAdmin(admin.ModelAdmin):
#     list_display = (
#                    "name",
# ....                "description",
# ...................."city",
# ...................."survey_type", ....
# ...................."analysis_threshold",
# ...................."kobotool_survey_id",
# ...................."kobotool_survey_url")
# admin.site.register(Survey,SurveyDetailAdmin)

class PlottedShapeAdmin(admin.ModelAdmin):
    """Display panel of PlottedShapeAdmin Model"""
    list_display = ('slum', 'name', 'lat_long', 'drawable_component')
    exclude = ('created_by', 'created_on')

    def save_model(self, request, obj, form, change):
        obj.createdBy = request.user
        obj.save()

# admin.site.register(PlottedShape,PlottedShapeAdmin)
class CityAdmin(admin.ModelAdmin):
    """Display panel of CityAdmin Model"""
    form = CityFrom 
    model = City
    search_fields = ('name',)
    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.save()
admin.site.register(City, CityAdmin)



class WardOfficeContactAdmin(admin.ModelAdmin):
    """Display panel of WardOfficeContact Model"""
    inlines = [WardOfficeContactInline]
    list_display = ('name', 'ward_no', 'city', 'office_address')
    search_fields = ('name',)
admin.site.register(AdministrativeWard, WardOfficeContactAdmin)

admin.site.unregister(AdministrativeWard)

class AdministrativeWardAdmin(admin.ModelAdmin):
    form = AdministrativeWardFrom
    search_fields = ('name',)
admin.site.register(AdministrativeWard,AdministrativeWardAdmin)    


admin.site.unregister(ElectoralWard)

class ElectoralWardFormAdmin(admin.ModelAdmin):
    form = ElectoralWardForm
    search_fields = ('name',)
admin.site.register(ElectoralWard,ElectoralWardFormAdmin) 


