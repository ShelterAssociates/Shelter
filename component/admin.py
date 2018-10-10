from django.contrib import admin
#from django.contrib.gis import admin
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

class MetadataAdmin(admin.ModelAdmin):
    list_display = ('name', 'section_name', 'type', 'visible')
    search_fields = ['name']
    ordering = ['name', 'section__name', 'type', 'visible']

    def section_name(self, obj):
        return obj.section.name

admin.site.register(Metadata, MetadataAdmin)
admin.site.register(Fact)

class ComponentTypeFilter(admin.SimpleListFilter):
    """
    City level filter 
    """
    title = 'Type'
    parameter_name = 'types'

    def lookups(self, request, model_admin):
        """
        Creating list filter lookup 
        """
        obj_meta = Metadata.objects.filter(type__in=['C']).order_by('name')
        obj_meta = obj_meta.values_list('name', 'name')
        return tuple(obj_meta)

    def queryset(self, request, queryset):
        """
        Filter data as per list filter selected. 
        """
        cust_filter = {}
        if self.value():
            cust_filter = {"metadata__name__in" : [self.value()]}
        return queryset.filter(**cust_filter)

class ComponentAdmin(admin.ModelAdmin):
    list_display = ('slum_name', 'component_name', 'number', 'shape_type')
    search_fields = ['slum__name','metadata__name','housenumber']
    ordering = ['slum__name','metadata__name','housenumber']
    list_filter = [ComponentTypeFilter]

    def number(self, obj):
        return obj.housenumber

    def slum_name(self, obj):
        return obj.slum.name

    def component_name(self, obj):
        return obj.metadata.name

    def shape_type(self, obj):
        return obj.shape.geom_type

admin.site.register(Component, ComponentAdmin)
