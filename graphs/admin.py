from django.contrib import admin
from .models import *
import datetime
from django.contrib.auth.models import User

class HouseholdDataAdmin(admin.ModelAdmin):
	list_filter = ['slum__electoral_ward__administrative_ward__city']
	list_display = ('household_number','ff_data','rhs_data','slum','created_date','submission_date')
	search_fields = ['slum_id__name','household_number']
	ordering = ['slum', 'household_number']
	raw_id_fields = ['slum']
	list_per_page = 10
admin.site.register(HouseholdData, HouseholdDataAdmin)

class FollowupDataAdmin(admin.ModelAdmin):
	list_filter = ['slum__electoral_ward__administrative_ward__city']
	list_display = ('household_number','slum','followup_data','created_date','submission_date','flag_followup_in_rhs')
	search_fields = [ 'household_number', 'slum_id__name']
	ordering = ['slum', 'household_number']
	raw_id_fields = ['slum']
	list_per_page = 10
admin.site.register(FollowupData, FollowupDataAdmin)

class RIMDataAdmin(admin.ModelAdmin):
	list_filter = ['slum__electoral_ward__administrative_ward__city']
	list_display = ('rim_data','slum','created_on','submission_date')
	search_fields = ['slum_id__name']
	ordering = ['slum']
	raw_id_fields = ['slum']
	list_per_page = 5

admin.site.register(SlumData, RIMDataAdmin)

class CovidDataAdmin(admin.ModelAdmin):
	list_filter = ['slum__electoral_ward__administrative_ward__city', 'date_of_survey']
	list_display = ('household_number','family_member_name', 'covid_uuid' ,'slum','date_of_survey','last_modified_date')
	search_fields = ['slum_id__name','household_number']
	ordering = ['slum', 'household_number']
	raw_id_fields = ['slum']
	list_per_page = 10

admin.site.register(CovidData, CovidDataAdmin)


@admin.register(MemberData)
class MemberDataAdmin(admin.ModelAdmin):
	list_filter = ['slum__electoral_ward__administrative_ward__city']
	list_display = ('member_first_name', 'member_uuid' ,'slum','created_date','submission_date')
	search_fields = ['slum_id__name']
	raw_id_fields = ['slum']
	list_per_page = 10

# admin.site.register(MemberData, MemberDataAdmin)

# admin.site.register(GroupData, GroupDataAdmin)
