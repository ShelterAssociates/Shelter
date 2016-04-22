from django.contrib import admin
from Masters.models import *
# Register your models here.

admin.site.register(WardOffice_Contacts)
admin.site.register(ProjectMaster)
admin.site.register(ShaperCode)
admin.site.register(Drawable_Component)
admin.site.register(Sponser)
admin.site.register(RoleMaster)
admin.site.register(Sponsor_ProjectMetadata)
admin.site.register(Filter)
admin.site.register(Sponsor_user)
admin.site.register(FilterMasterMetadata)
admin.site.register(UserRoleMaster)


class SlumDetailAdmin(admin.ModelAdmin):
    list_display = ( 
    	             "Name",
    	             "Description",
    	             "ElectoralWard_id",
    	             "Shelter_slum_code")
admin.site.register(Slum, SlumDetailAdmin)


class SurveyDetailAdmin(admin.ModelAdmin):
    list_display = (
                   "Name", 
	                "Description", 
					"City_id",
					"Survey_type", 	
					"AnalysisThreshold",
					"kobotoolSurvey_id", 
					"kobotoolSurvey_url")
admin.site.register(Survey,SurveyDetailAdmin)



class PlottedShapeAdmin(admin.ModelAdmin):
	list_display = (
					"Slum", 
					"Name",
					"Lat_long", 
					"Drawable_Component_id")
	
	exclude = ('createdBy','createdOn')
	def save_model(self, request, obj, form, change):
		obj.createdBy = request.user
		obj.save()   
admin.site.register(PlottedShape,PlottedShapeAdmin)




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



class Administrative_Ward_Inline(admin.TabularInline):
     model = Administrative_Ward
     
class Administrative_Ward_Admin(admin.ModelAdmin):
	inlines = [Administrative_Ward_Inline]
	list_display = ("Name","Shape","State_code","District_Code","City_code")
	exclude = ('createdBy','createdOn')
	def save_model(self, request, obj, form, change):
         obj.createdBy = request.user
         obj.save()
admin.site.register(City,Administrative_Ward_Admin)



class Electoral_Ward_Inline(admin.TabularInline):
     model = Electoral_Ward

class Electoral_Ward_Admin(admin.ModelAdmin):
	inlines = [Electoral_Ward_Inline]

admin.site.register(Administrative_Ward,Electoral_Ward_Admin)



class Slum_Inline(admin.TabularInline):
     model = Slum

class Slum_Admin(admin.ModelAdmin):
	inlines = [Slum_Inline]

admin.site.register(Electoral_Ward,Slum_Admin)



class Elected_Representative_Inline(admin.TabularInline):
     model = Elected_Representative

class Elected_Representative_Admin(admin.ModelAdmin):
	inlines = [Elected_Representative_Inline]

admin.site.unregister(Electoral_Ward)
admin.site.register(Electoral_Ward,Elected_Representative_Admin)



