from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect

admin.site.register(Sponsor)
admin.site.register(SponsorContact)

class SponsorProjectDetailsAdmin(admin.ModelAdmin):
	list_display = ('sponsor', 'slum', 'project_name', 'household_code')
	raw_id_fields = ['slum']
	def slum(self, obj):
		return obj.slum.name

	def project_name(self, obj):
		return obj.sponsor_project.name

admin.site.register(SponsorProjectDetails, SponsorProjectDetailsAdmin)

class SponsorProjectAdmin(admin.ModelAdmin):
	list_display = ("get_project_type","name", "get_status")
	exclude = ('created_by','created_on')

	def get_project_type(self, obj):
		return obj.get_project_type_display()

	def get_status(self, obj):
		return obj.get_status_display()

	def save_model(self, request, obj, form, change):
		obj.created_by = request.user
		obj.save()
		#super(SponsorProjectAdmin, self).save_model(request, obj, form, change)

admin.site.register(SponsorProject,SponsorProjectAdmin)

class UserAdminCust(UserAdmin):
	def save_model(self, request, obj, form, change):
		super(UserAdminCust, self).save_model(request, obj, form, change)
		#import pdb; pdb.set_trace()
		sponsor = Group.objects.filter(name = 'sponsor').first().id
		group_ids = [int(x) for x in request.POST.getlist('groups')]
		if sponsor in group_ids:
			sponsor, created = Sponsor.objects.get_or_create(user=obj, defaults={'user':obj})

	def response_change(self, request, obj):
		print "Inside change"
		if obj.groups.filter(name="sponsor").exists():
			sponsor = Sponsor.objects.get(user = obj)
            # hardcoded url to be replaced with reverse url
			return HttpResponseRedirect('../../../sponsor/sponsor/' + str(sponsor.id) + '/' )
		else:
			return super(UserAdminCust, self).response_change(request, obj)
admin.site.unregister(User)
admin.site.register(User,UserAdminCust)
