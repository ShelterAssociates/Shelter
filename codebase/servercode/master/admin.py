from django.contrib import admin
from models import *
# Register your models here.

admin.site.register(WardOfficeContact)
#admin.site.register(ProjectMaster)
#admin.site.register(ShapeCode)
#admin.site.register(DrawableComponent)
#admin.site.register(RoleMaster)
admin.site.register(ElectedRepresentative)
#admin.site.register(UserRoleMaster)

class CityReferenceAdmin(admin.ModelAdmin):
    list_display = (
    "city_name",
    "city_code",
    "district_name",
    "district_code",
    "state_name",
    "state_code"
 )
admin.site.register(CityReference,CityReferenceAdmin)

class WardOfficeContactInline(admin.TabularInline):
     model = WardOfficeContact

class WardOfficeContactAdmin(admin.ModelAdmin):
	inlines = [WardOfficeContactInline]
	list_display = ( 
    	             "name",
    	             "ward_no",
    	             "city",
    	             "office_address")
admin.site.register(AdministrativeWard, WardOfficeContactAdmin)


class ElectedRepresentativeInline(admin.TabularInline):
     model = ElectedRepresentative

class ElectedRepresentativeAdmin(admin.ModelAdmin):
	list_display = ( 
    	             "name",
    	             "ward_no",
    	             "ward_code",
    	             "administrative_ward")
	inlines = [ElectedRepresentativeInline]

admin.site.register(ElectoralWard, ElectedRepresentativeAdmin)



class SlumDetailAdmin(admin.ModelAdmin):
    list_display = ( 
    	             "name",
    	             "description",
    	             "electoral_ward",
    	             "shelter_slum_code")
admin.site.register(Slum, SlumDetailAdmin)


# class SurveyDetailAdmin(admin.ModelAdmin):
#     list_display = (
#                    "name", 
# 	                "description", 
# 					"city",
# 					"survey_type", 	
# 					"analysis_threshold",
# 					"kobotool_survey_id", 
# 					"kobotool_survey_url")
# admin.site.register(Survey,SurveyDetailAdmin)



class PlottedShapeAdmin(admin.ModelAdmin):
	list_display = (
					"slum", 
					"name",
					"lat_long", 
					"drawable_component")
	
	exclude = ('created_by','created_on')
	def save_model(self, request, obj, form, change):
		obj.createdBy = request.user
		obj.save()   
#admin.site.register(PlottedShape,PlottedShapeAdmin)

     
class CityAdmin(admin.ModelAdmin):
	list_display = ("name","shape","state_code","district_code","city_code")
	exclude = ('created_by','created_on')
	def save_model(self, request, obj, form, change):
         obj.created_by = request.user
         obj.save()

admin.site.register(City, CityAdmin)

