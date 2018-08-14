#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Admin Page for master app"""
from django.contrib import admin
#from django.contrib.gis import admin
from master.models import CityReference, City, \
    AdministrativeWard, ElectoralWard, Slum, WardOfficeContact, ElectedRepresentative, Rapid_Slum_Appraisal, Survey, drainage
from master.forms import CityFrom, AdministrativeWardFrom, ElectoralWardForm, SlumForm

#Common filters for querying model depending on model type
data_filter = {'CityReference': 'city_name__in',
               'City': 'name__city_name__in',
               'AdministrativeWard': 'city__name__city_name__in',
               'ElectoralWard': 'administrative_ward__city__name__city_name__in',
               'Slum': 'electoral_ward__administrative_ward__city__name__city_name__in',
               'WardOfficeContact': 'administrative_ward__city__name__city_name__in',
               'ElectedRepresentative': 'electoral_ward__administrative_ward__city__name__city_name__in'}

class CityListFilter(admin.SimpleListFilter):
    """
    City level filter 
    """
    title = 'Cities'
    parameter_name = 'cities'

    def lookups(self, request, model_admin):
        """
        Creating list filter lookup 
        """
        obj_city = City.objects.all()
        if not request.user.is_superuser:
            group_perm = request.user.groups.values_list('name', flat=True)
            group_perm = map(lambda x: x.split(':')[-1], group_perm)
            obj_city = obj_city.filter(name__city_name__in=group_perm)
        obj_city = obj_city.values_list('name__city_name', 'name__city_name')
        return tuple(obj_city)

    def queryset(self, request, queryset):
        """
        Filter data as per list filter selected. 
        """
        cust_filter = {}
        if self.value() and str(queryset.model.__name__) in data_filter.keys():
            cust_filter = {data_filter[str(queryset.model.__name__)] : [self.value()]}
        return queryset.filter(**cust_filter)

class BaseModelAdmin(admin.ModelAdmin):
    """
    Base class having city level filter and user based access to data.
    """
    list_filter = [CityListFilter]

    def get_queryset(self, request):
        """
         Django admin list filter data as per city level access.
        """
        queryset = super(BaseModelAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return queryset
        cust_filter = {}
        if str(queryset.model.__name__) in data_filter.keys():
            group_perm = request.user.groups.values_list('name', flat=True)
            group_perm = map(lambda x: x.split(':')[-1], group_perm)
            cust_filter = {data_filter[str(queryset.model.__name__)] : group_perm}
        return queryset.filter(**cust_filter)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        This is for forign key field dropdown displayed at type of admin add/edit details.
        """
        group_perm = request.user.groups.values_list('name', flat=True)
        group_perm = map(lambda x:x.split(':')[-1], group_perm)
        if db_field.name == "electoral_ward":
            kwargs["queryset"] = ElectoralWard.objects.filter(administrative_ward__city__name__city_name__in=group_perm)
        if db_field.name == "administrative_ward":
            kwargs["queryset"] = AdministrativeWard.objects.filter(city__name__city_name__in=group_perm)
        if db_field.name in  ["city","name"]:
            kwargs["queryset"] = City.objects.filter(name__city_name__in=group_perm)
        return super(BaseModelAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

#City Reference
class CityReferenceAdmin(BaseModelAdmin):
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

#slum
class SlumDetailAdmin(BaseModelAdmin):
    form = SlumForm
    list_display = ('name', 'electoral_ward', 'administrative_ward', 'city_name','associated_with_SA')
    search_fields = ['name','electoral_ward__name', 'electoral_ward__administrative_ward__name']
    #list_filter = [CityListFilter]
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

#City
class CityAdmin(BaseModelAdmin):
    """Display panel of CityAdmin Model"""
    form = CityFrom
    model = City
    search_fields = ('name',)
    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        obj.save()
admin.site.register(City, CityAdmin)

#Administrative Ward
class WardOfficeContactInline(admin.TabularInline):
    """Display panel of WardOfficeContacts Model"""
    model = WardOfficeContact
    search_fields = ('name',)

class AdministrativeWardAdmin(BaseModelAdmin):
    form = AdministrativeWardFrom
    list_display = ('name', 'ward_no','city', 'office_address')
    inlines = [WardOfficeContactInline]
    search_fields = ('name',)
admin.site.register(AdministrativeWard,AdministrativeWardAdmin)

#Electoral Ward
class ElectedRepresentativeInline(admin.TabularInline):
    """Display panel of ElectedRepresentative Model"""
    model = ElectedRepresentative
    search_fields = ('name',)

class ElectoralWardFormAdmin(BaseModelAdmin):
    form = ElectoralWardForm
    list_display = ('name', 'ward_no', 'ward_code',
                    'administrative_ward', 'city_name')
    search_fields = ('name',)
    inlines = [ElectedRepresentativeInline]

    def administrative_ward(self, obj):
        return obj.administrative_ward.name

    def city_name(self, obj):
        return obj.administrative_ward.city.name.city_name
admin.site.register(ElectoralWard, ElectoralWardFormAdmin)

#Ward office contact
class WardOfficeContactAdmin(BaseModelAdmin):
    list_display = ('name', 'administrative_ward', 'city_name',)
    search_fields = ('name',)

    def administrative_ward(self, obj):
        return obj.administrative_ward.name

    def city_name(self, obj):
        return obj.administrative_ward.city.name.city_name

admin.site.register(WardOfficeContact, WardOfficeContactAdmin)

#Elected Representative
class ElectedRepresentativeAdmin(BaseModelAdmin):
    list_display = ('name','electoral_ward', 'administrative_ward', 'city_name',)
    search_fields = ('name',)

    def electoral_ward(self, obj):
        return obj.electoral_ward.name

    def administrative_ward(self, obj):
        return obj.electoral_ward.administrative_ward.name

    def city_name(self, obj):
        return obj.electoral_ward.administrative_ward.city.name.city_name

admin.site.register(ElectedRepresentative, ElectedRepresentativeAdmin)

admin.site.register(Rapid_Slum_Appraisal)
admin.site.register(drainage)
