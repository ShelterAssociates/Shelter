#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Admin Page for master app"""
from django.contrib import admin
#from django.contrib.gis import admin
from master.models import CityReference, City, \
    AdministrativeWard, ElectoralWard, Slum, WardOfficeContact, ElectedRepresentative, Rapid_Slum_Appraisal, Survey, drainage
from master.forms import CityFrom, AdministrativeWardFrom, ElectoralWardForm, SlumForm
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.core.urlresolvers import reverse
from django.conf.urls import include, url
from django.http import HttpResponse
import json
from kmllevelparser import KMLLevelParser

#Common filters for querying model depending on model type
data_filter = {'CityReference': 'city_name__in',
               'City': 'name__city_name__in',
               'AdministrativeWard': 'city__name__city_name__in',
               'ElectoralWard': 'administrative_ward__city__name__city_name__in',
               'Slum': 'electoral_ward__administrative_ward__city__name__city_name__in',
               'WardOfficeContact': 'administrative_ward__city__name__city_name__in',
               'ElectedRepresentative': 'electoral_ward__administrative_ward__city__name__city_name__in'}

class UploadKMLBase(admin.ModelAdmin):

    class Media:
        js = ['js/admin_upload_kml.js']

    def get_urls(self):
        urls = super(UploadKMLBase, self).get_urls()
        custom_urls = [
            url(
                r'^(?P<city_id>.+)/City/$',
                self.admin_site.admin_view(self.process_city),
                name='city-kml-upload',
            ),
            url(
                r'^(?P<city_id>.+)/AdministrativeWard/$',
                self.admin_site.admin_view(self.process_administrativeward),
                name='adminward-kml-upload',
            ),
            url(
                r'^(?P<city_id>.+)/ElectoralWard/$',
                self.admin_site.admin_view(self.process_electoralward),
                name='electoralward-kml-upload',
            ),
            url(
                r'^(?P<city_id>.+)/Slum/$',
                self.admin_site.admin_view(self.process_slum),
                name='slum-kml-upload',
            ),
        ]
        return custom_urls + urls

    def kml_upload_actions(self, obj):
        return format_html(
            '<button type="button" class="btn btn-success btn-sm"  data-target="#kmlModal" href="{}">City</button>&nbsp;&nbsp;'
            '<button type="button" class="btn btn-success btn-sm"  data-target="#kmlModal" href="{}">Administrative Ward</button>&nbsp;&nbsp;'
            '<button type="button" class="btn btn-success btn-sm"  data-target="#kmlModal" href="{}">Electoral Ward</button>&nbsp;&nbsp;'
            '<button type="button" class="btn btn-success btn-sm"  data-target="#kmlModal" href="{}">Slum</button>',
            reverse('admin:city-kml-upload', args=[obj.pk]),
            reverse('admin:adminward-kml-upload', args=[obj.pk]),
            reverse('admin:electoralward-kml-upload', args=[obj.pk]),
            reverse('admin:slum-kml-upload', args=[obj.pk])
        )

    def process_city(self, request, city_id, *args, **kwargs):
        return self.process_action(request,city_id, "City")

    def process_administrativeward(self, request, city_id, *args, **kwargs):
        return  self.process_action(request, city_id, "AdministrativeWard")

    def process_electoralward(self, request, city_id, *args, **kwargs):
        return self.process_action( request, city_id, "ElectoralWard")

    def process_slum(self, request, city_id, *args, **kwargs):
        return self.process_action(request, city_id, "Slum")

    def process_action(self, request, city_id, action_title):
        response = {"status":True, 'message':""}
        if request.method == "POST":
            docFile = request.FILES['file'].read()
            chk_delete = request.POST['chk_delete']
            try:
                kml_level_parser = KMLLevelParser(docFile, city_id, chk_delete, action_title)
                cnt = kml_level_parser.parse_kml()

                if cnt['created'] > 0:
                    response['message'] = "Created "+str(cnt['created']) + " " + action_title
                if cnt['updated'] > 0:
                    response['message'] += "\nUpdated " +str(cnt['updated']) + " " + action_title
                if response['message'] == "":
                    response['message']= "Nothing parsed"
            except Exception as e:
                response['status'] = False
                response['message'] = str(e)
        return HttpResponse(json.dumps(response), content_type='application/json')

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
        if request.user.is_superuser:
            group_perm = Group.objects.all().values_list('name', flat=True)
        group_perm = map(lambda x:x.split(':')[-1], group_perm)
        if db_field.name == "electoral_ward":
            kwargs["queryset"] = ElectoralWard.objects.filter(administrative_ward__city__name__city_name__in=group_perm)
        if db_field.name == "administrative_ward":
            kwargs["queryset"] = AdministrativeWard.objects.filter(city__name__city_name__in=group_perm)
        if db_field.name in  ["city"]:
            kwargs["queryset"] = City.objects.filter(name__city_name__in=group_perm)
        if db_field.name in ['name']:
            kwargs["queryset"] = CityReference.objects.filter(city_name__in=group_perm)
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
    list_display = ('name', 'electoral_ward', 'administrative_ward', 'city_name','shelter_slum_code', 'associated_with_SA','status','odf_status')
    search_fields = ['name','electoral_ward__name', 'electoral_ward__administrative_ward__name','shelter_slum_code']
    #list_filter = [CityListFilter]
    ordering = ['electoral_ward__name', 'name']
    actions = ['associated_with_SA', 'status_of_slum','ODF','ODF_plus','ODF_plusplus']

    def ODF(self,request,queryset):
        for query in queryset:
            query.odf_status = 'ODF'
            query.save()
    ODF.short_description = "Change status of slum(s) to ODF"

    def ODF_plus(self,request,queryset):
        for query in queryset:
            query.odf_status = 'ODF+'
            query.save()
    ODF_plus.short_description = "Change status of slum(s) to ODF+"

    def ODF_plusplus(self,request,queryset):
        for query in queryset:
            query.odf_status = 'ODF++'
            query.save()
    ODF_plusplus.short_description = "Change status of slum(s) to ODF++"

    def associated_with_SA(self, request, queryset):
        for query in queryset:
            query.associated_with_SA = not query.associated_with_SA
            query.save()
    associated_with_SA.short_description = "Associate the selected slum(s)"

    def status_of_slum(self, request, queryset):
        for query in queryset:
            query.status = not query.status
            query.save()
    status_of_slum.short_description = "Change status(Active/Inactive) of slum(s)"

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
class CityAdmin(BaseModelAdmin, UploadKMLBase):
    """Display panel of CityAdmin Model"""
    form = CityFrom
    list_display = ('name','kml_upload_actions')
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
        try:
            return obj.administrative_ward.city.name.city_name
        except:
            return ''

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
