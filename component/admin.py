from django.contrib import admin
from django.contrib.gis import admin
from models import *

class MetadataInline(admin.TabularInline):
    """Inline to add metadata while adding sections
    """
    model = Metadata
    fk_name = 'section'
    max_num = 1
    extra = 1
    can_delete = False

class SectionAdmin(admin.ModelAdmin):
    inlines = [MetadataInline]
    search_fields = ['name']

admin.site.register(Section, SectionAdmin)
admin.site.register(Metadata)
admin.site.register(Fact)

class ComponentAdmin(admin.ModelAdmin):
    list_display = ('slum_name', 'component_name', 'number', 'shape_type')
    search_fields = ['slum__name','metadata__name','housenumber']
    ordering = ['slum__name','metadata__name','housenumber']

    def number(self, obj):
        return obj.housenumber

    def slum_name(self, obj):
        return obj.slum.name

    def component_name(self, obj):
        return obj.metadata.name

    def shape_type(self, obj):
        return obj.shape.geom_type

admin.site.register(Component, ComponentAdmin)
