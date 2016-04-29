from django.contrib import admin
from .models import *

admin.site.register(Sponsor)
admin.site.register(SponsorContact)
admin.site.register(SponsorProjectDetails)

# Register your models here.

class SponsorProjectAdmin(admin.ModelAdmin):
	list_display = ( 
				"type",
				"sponsor", 
	)
	exclude = ('created_by','created_on')
	def save_model(self, request, obj, form, change):
		obj.createdBy = request.user
		obj.save()   

admin.site.register(SponsorProject,SponsorProjectAdmin)

