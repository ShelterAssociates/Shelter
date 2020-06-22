from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect

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

	class Media:
		js = ['js/collapse_household_code.js']

	def slum(self, obj):
		return obj.slum.name

	def sponsor_project(self, obj):
		return obj.sponsor_project.name

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
