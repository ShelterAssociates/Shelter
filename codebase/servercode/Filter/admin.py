from django.contrib import admin
from .models import *

admin.site.register(Filter)
admin.site.register(FilterMasterMetadata)



# Register your models here.
class Filter_MasterAdmin(admin.ModelAdmin):
	list_display = ( 
				"Name",
				"IsDeployed", 
				"VisibleTo")
	exclude = ('createdBy','createdOn')
	def save_model(self, request, obj, form, change):
		obj.createdBy = request.user
		obj.save()   
admin.site.register(Filter_Master,Filter_MasterAdmin)
