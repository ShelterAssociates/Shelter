#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Admin Page for master app"""
from django.contrib import admin
from django.contrib.gis import admin
from master.models import CityReference, City, \
    AdministrativeWard, ElectoralWard, Slum, WardOfficeContact, ElectedRepresentative
from master.forms import CityFrom

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

admin.site.register(CityReference, CityReferenceAdmin)

class WardOfficeContactInline(admin.TabularInline):
    """Display panel of WardOfficeContacts Model"""
    model = WardOfficeContact

class WardOfficeContactAdmin(admin.ModelAdmin):
    """Display panel of WardOfficeContact Model"""
    inlines = [WardOfficeContactInline]
    list_display = ('name', 'ward_no', 'city', 'office_address')

admin.site.register(AdministrativeWard, WardOfficeContactAdmin)

class ElectedRepresentativeInline(admin.TabularInline):
    """Display panel of ElectedRepresentative Model"""
    model = ElectedRepresentative

class ElectedRepresentativeAdmin(admin.ModelAdmin):
    """Display panel of ElectedRepresentativeAdmin Model"""
    list_display = ('name', 'ward_no', 'ward_code',
                    'administrative_ward')
    inlines = [ElectedRepresentativeInline]

admin.site.register(ElectoralWard, ElectedRepresentativeAdmin)

class SlumDetailAdmin(admin.ModelAdmin):
    """Display panel of SlumDetailAdmin Model"""
    list_display = ('name', 'description', 'electoral_ward',
                    'shelter_slum_code')

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
    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.save()

admin.site.register(City, CityAdmin)