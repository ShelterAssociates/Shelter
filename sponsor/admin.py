from django.contrib import admin
from .models import *
from mastersheet.models import ToiletConstruction
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse

class SponsorAdmin(admin.ModelAdmin):
	list_display = ('organization_name', 'address', 'website_link', 'intro_date', 'logo')
	search_fields = ['organization_name', 'address', 'website_link', 'intro_date']
	ordering = ['organization_name', 'address']

admin.site.register(Sponsor, SponsorAdmin)
#admin.site.register(SponsorContact)
class SponsorProjectDetailsSubFieldsInline(admin.TabularInline):
	model = SponsorProjectDetailsSubFields
	min_num = 1
	extra = 0

class SponsorProjectDetailsAdmin(admin.ModelAdmin):
	list_display = ('sponsor', 'slum', 'sponsor_project', 'household_code')
	#readonly_fields = ['household_code']
	raw_id_fields = ['slum', 'sponsor_project']
	search_fields = ['slum__name', 'sponsor__organization_name', 'sponsor_project__name']
	ordering = ['sponsor', 'slum', 'sponsor_project']
	list_filter = ['sponsor_project__sponsor']
	inlines = [ SponsorProjectDetailsSubFieldsInline ]
	global message_dict # This message_dict we are creating to save custom messages.
	message_dict = {}

	class Media:
		js = ['js/collapse_household_code.js']

	def slum(self, obj):
		return obj.slum.name

	def sponsor_project(self, obj):
		return obj.sponsor_project.name
	
	'''Method for checking data impurities when a user save sponsor project details entry using admin.'''
	@receiver(pre_save, sender=SponsorProjectDetailsSubFields)
	def check_for_duplicates(sender, instance, **kwargs):
		household_codes = instance.household_code
		unique_hh_codes = list(set(household_codes))

		if len(unique_hh_codes) != len(household_codes):
			message_dict['Message'] = "There are duplicate households present in your data !!"
		else:
			if 'Message' in message_dict:
				del message_dict['Message']
			hh_codes = []
			change_data = household_codes
			if instance.id: # We are calculating this to find out change household numbers.
				_ , sp_change =  SponsorProjectDetailsSubFields.objects.filter(id = instance.id).values_list('sponsor_project_details', 'household_code')[0]
				hh_change = set(change_data).difference(set(sp_change))
			
			sp_project_details_code = SponsorProjectDetails.objects.filter(slum_id__name = instance).exclude(sponsor_id = 10).values_list('id', flat = True)
			sub_fields = SponsorProjectDetailsSubFields.objects.filter(sponsor_project_details__in = sp_project_details_code)

			for i in sub_fields:
				if instance.id is None:
					diff = set(change_data).difference(i.household_code)
					if len(diff) != len(change_data):
						common_hhs = set(change_data).difference(i.household_code)
						message_dict['Message'] = "These household no's. already available in Sponsor data. Kindly check !!{}".format(common_hhs)
				else:
					if i.id != instance.id:
						diff = set(change_data).intersection(i.household_code)
						if len(diff) > 0:
							print(hh_change, i.household_code, diff)
							hh_codes.extend(list(diff))
			if len(hh_codes) > 0:
				message_dict['Message'] = "These household no's. already available in Sponsor data. Kindly check !! {}".format(hh_codes)
			else:
				''' Checking The updated household Codes is present in the Toilet construction table.'''
				Toilet_data = ToiletConstruction.objects.filter(slum_id__name = instance, household_number__in = change_data).values_list('household_number', flat = True)
				if Toilet_data.count() > 0:
					if Toilet_data.count() != len(change_data):
						hh_codes = [i for i in change_data if str(i) not in Toilet_data]
						message_dict['Message'] = "The Sanitation data is not available for these households. Kindly check !! {}".format(hh_codes)
				else:
					message_dict['Message'] = "The Sanitation data is not available for these households. Kindly check !! {}".format(change_data)
	
	''' These methods is for overwriting the django's built-in message module as per our requirements. '''
	def response_add(self, request, obj, post_url_continue=None):
		if message_dict:
			messages.warning(request, 'Data is not formatted correctly.')
			return HttpResponseRedirect(reverse('admin:sponsor_sponsorprojectdetails_changelist'))
		else:
			return super().response_add(request, obj, post_url_continue)

	def response_change(self, request, obj):
		if message_dict:
			messages.warning(request, message_dict['Message'])
			return HttpResponseRedirect(reverse('admin:sponsor_sponsorprojectdetails_change', args=[obj.pk]))
		else:
			return super().response_change(request, obj)

	# def quarter(self, obj):
	#  	return obj.get_quarter_display()
    #
	# def status(self, obj):
	# 	return obj.get_status_display()
    #
	# def get_search_results(self, request, queryset, search_term):
	# 	'''
	# 	:param request:
	# 	:param queryset:
	# 	:param search_term:
	# 	:return: queryset
	#
	# 	 Function for adding custom filters for choice field options
	# 	'''
	# 	queryset, use_distinct = super(SponsorProjectDetailsAdmin, self).get_search_results(request, queryset, search_term)
    #
	# 	quarter_options = filter(lambda x: search_term.lower() in x[1].lower(), QUARTER_CHOICES)
	# 	quarter_options = map(lambda x: x[0], quarter_options)
	# 	status_options = filter(lambda x: search_term.lower() in x[1].lower(), SPONSORSTATUS_CHOICES)
	# 	status_options = map(lambda x: x[0], status_options)
	# 	queryset |= self.model.objects.filter(quarter__in=quarter_options)
	# 	queryset |= self.model.objects.filter(status__in=status_options)
	# 	return queryset, use_distinct

admin.site.register(SponsorProjectDetails, SponsorProjectDetailsAdmin)

class ProjectDetailsInline(admin.TabularInline):
	model = SponsorProjectDetails

class ProjectDocumentsInline(admin.TabularInline):
	model = ProjectDocuments

class ProjectImagesInline(admin.TabularInline):
	model = ProjectImages

class SponsorProjectAdmin(admin.ModelAdmin):
	list_display = ("name","sponsor", "project_type", "funds_sponsored", "start_date", "status")
	exclude = ('created_by','created_on')
	search_fields = ['name', 'sponsor__organization_name', 'funds_sponsored', 'start_date']
	ordering = ['name', 'sponsor', 'project_type']
	inlines = [ProjectDocumentsInline, ProjectImagesInline]

	def project_type(self, obj):
		return obj.get_project_type_display()

	def status(self, obj):
		return obj.get_status_display()

	def get_search_results(self, request, queryset, search_term):
		'''
		:param request: 
		:param queryset: 
		:param search_term: 
		:return: queryset 

		 Function for adding custom filters for choice field options
		'''
		queryset, use_distinct = super(SponsorProjectAdmin, self).get_search_results(request, queryset,
																							search_term)

		type_options = filter(lambda x: search_term.lower() in x[1].lower(), TYPE_CHOICES)
		type_options = map(lambda x: x[0], type_options)
		status_options = filter(lambda x: search_term.lower() in x[1].lower(), PROJECTSTATUS_CHOICES)
		status_options = map(lambda x: x[0], status_options)
		queryset |= self.model.objects.filter(project_type__in=type_options)
		queryset |= self.model.objects.filter(status__in=status_options)
		return queryset, use_distinct

	def save_model(self, request, obj, form, change):
		obj.created_by = request.user
		obj.save()
		#super(SponsorProjectAdmin, self).save_model(request, obj, form, change)

admin.site.register(SponsorProject,SponsorProjectAdmin)

class SponsorProjectMOUAdmin(admin.ModelAdmin):
	list_display = ('sponsor_project', 'quarter', 'fund_released', 'release_date')
	search_fields = ['sponsor_project__name']
	ordering = ['sponsor_project__name', 'quarter']
	raw_id_fields = ['sponsor_project']

	def quarter(self, obj):
		return obj.get_quarter_display()

	def get_search_results(self, request, queryset, search_term):
		'''
		:param request: 
		:param queryset: 
		:param search_term: 
		:return: queryset 

		 Function for adding custom filters for choice field options
		'''
		queryset, use_distinct = super(SponsorProjectMOUAdmin, self).get_search_results(request, queryset,
																							search_term)

		quarter_options = filter(lambda x: search_term.lower() in x[1].lower(), QUARTER_CHOICES)
		quarter_options = map(lambda x: x[0], quarter_options)
		queryset |= self.model.objects.filter(quarter__in=quarter_options)
		return queryset, use_distinct

admin.site.register(SponsorProjectMOU, SponsorProjectMOUAdmin)

class UserAdminCust(UserAdmin):
	def save_model(self, request, obj, form, change):
		super(UserAdminCust, self).save_model(request, obj, form, change)
		#import pdb; pdb.set_trace()
		sponsor = Group.objects.filter(name = 'sponsor').first().id
		group_ids = [int(x) for x in request.POST.getlist('groups')]
		if sponsor in group_ids:
			sponsor, created = Sponsor.objects.get_or_create(user=obj, defaults={'user':obj})

	def response_change(self, request, obj):
		if obj.groups.filter(name="sponsor").exists():
			sponsor = Sponsor.objects.get(user = obj)
            # hardcoded url to be replaced with reverse url
			return HttpResponseRedirect('../../../sponsor/sponsor/' + str(sponsor.id) + '/' )
		else:
			return super(UserAdminCust, self).response_change(request, obj)
admin.site.unregister(User)
admin.site.register(User,UserAdminCust)
