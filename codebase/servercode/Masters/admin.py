from django.contrib import admin
from Masters.models import *
# Register your models here.

admin.site.register(Slum)
admin.site.register(WardOffice_Contacts)
admin.site.register(ProjectMaster)
admin.site.register(ShaperCode)
admin.site.register(Drawable_Component)
admin.site.register(PlottedShape)


class Administrative_Ward_Inline(admin.TabularInline):
     model = Administrative_Ward

class Administrative_Ward_Admin(admin.ModelAdmin):
	inlines = [Administrative_Ward_Inline]

admin.site.register(City,Administrative_Ward_Admin)

class Electrol_Ward_Inline(admin.TabularInline):
     model = Electrol_Ward

class Electrol_Ward_Admin(admin.ModelAdmin):
	inlines = [Electrol_Ward_Inline]

admin.site.register(Administrative_Ward,Electrol_Ward_Admin)

class Slum_Inline(admin.TabularInline):
     model = Slum

class Slum_Admin(admin.ModelAdmin):
	inlines = [Slum_Inline]

admin.site.register(Electrol_Ward,Slum_Admin)

class Elected_Representative_Inline(admin.TabularInline):
     model = Elected_Representative

class Elected_Representative_Admin(admin.ModelAdmin):
	inlines = [Elected_Representative_Inline]

admin.site.unregister(Electrol_Ward)
admin.site.register(Electrol_Ward,Elected_Representative_Admin)

