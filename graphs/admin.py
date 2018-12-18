from django.contrib import admin
from .models import *
import datetime
from django.contrib.auth.models import User

class HouseholdDataAdmin(admin.ModelAdmin):
	list_display = ('household_number','slum','created_date','submission_date')
	search_fields = ['slum', 'household_number', 'city','created_date', 'submission_date']
	ordering = ['slum', 'household_number']
	raw_id_fields = ['slum']
admin.site.register(HouseholdData, HouseholdDataAdmin)

class FollowupDataAdmin(admin.ModelAdmin):
	list_display = ('household_number','slum','created_date','submission_date','flag_followup_in_rhs')
	search_fields = [ 'household_number', 'slum', 'city','created_date', 'submission_date']
	ordering = ['slum', 'household_number']
	raw_id_fields = ['slum']
admin.site.register(FollowupData, FollowupDataAdmin)
