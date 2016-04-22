from django.contrib import admin
from .models import *

admin.site.register(Sponser)
admin.site.register(Sponsor_ProjectMetadata)
admin.site.register(Sponsor_user)

# Register your models here.

class Sponsor_ProjectAdmin(admin.ModelAdmin):
	list_display = ( 
				"Type",
				"Sponsor_id", 
	)
	exclude = ('createdBy','createdOn')
	def save_model(self, request, obj, form, change):
		obj.createdBy = request.user
		obj.save()   

admin.site.register(Sponsor_Project,Sponsor_ProjectAdmin)

