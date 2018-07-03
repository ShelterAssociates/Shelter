#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Admin Page for master app"""
from django.contrib import admin
#from django.contrib.gis import admin
from master.models import CityReference, City, \
    AdministrativeWard, ElectoralWard, Slum, WardOfficeContact, ElectedRepresentative, Rapid_Slum_Appraisal, Survey, drainage
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

class CityListFilter(admin.SimpleListFilter):
    title = 'Cities'
    parameter_name = 'cities'

    def lookups(self, request, model_admin):
        obj_city = City.objects.values_list('name__city_name','name__city_name')
        print obj_city
        return tuple(obj_city)

    def queryset(self, request,queryset):
        if self.value():
            print self.value()
            return queryset.filter(electoral_ward__administrative_ward__city__name__city_name=self.value())


class SlumDetailAdmin(admin.ModelAdmin):
    form = SlumForm
    list_display = ('name', 'electoral_ward', 'administrative_ward', 'city_name','associated_with_SA')
    search_fields = ['name','electoral_ward__name', 'electoral_ward__administrative_ward__name']
    list_filter = [CityListFilter]
    ordering = ['electoral_ward__name', 'name']

    actions = ['associated_with_SA']

    def associated_with_SA(self, request, queryset):
        for query in queryset:
            query.associated_with_SA = not query.associated_with_SA
            query.save()

    associated_with_SA.short_description = "Associate the selected slum(s)"

    def electoral_ward(self, obj):
        return obj.electoral_ward.name

    def administrative_ward(self, obj):
        return obj.electoral_ward.administrative_ward.name

    def city_name(self, obj):
        return obj.electoral_ward.administrative_ward.city.name.city_name

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

admin.site.register(Rapid_Slum_Appraisal)
admin.site.register(drainage)
