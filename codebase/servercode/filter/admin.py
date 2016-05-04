from django.contrib import admin
from filter.models import *

"""
admin.site.register(Filter)
admin.site.register(FilterMasterMetadata)



# Register your models here.
class FilterMasterAdmin(admin.ModelAdmin):
	list_display = ( 
				"Name",
				"IsDeployed", 
				"VisibleTo")
	exclude = ('createdBy','createdOn')
	def save_model(self, request, obj, form, change):
		obj.createdBy = request.user
		obj.save()   
admin.site.register(FilterMaster,FilterMasterAdmin)
"""


