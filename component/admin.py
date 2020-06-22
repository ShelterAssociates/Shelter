from django.contrib import admin
#from django.contrib.gis import admin
from .models import *

class SectionListFilter(admin.SimpleListFilter):
    """
    Section level filter 
    """
    title = 'Section'
    parameter_name = 'section'

    def lookups(self, request, model_admin):
        """
        Creating list filter lookup 
        """
        obj_section = Section.objects.all().order_by('name')
        obj_section = obj_section.values_list('name', 'name')
        return tuple(obj_section)

    def queryset(self, request, queryset):
        """
        Filter data as per list filter selected. 
        """
        cust_filter = {}
        if self.value():
            cust_filter = {'section__name' : self.value()}
        return queryset.filter(**cust_filter)

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
    list_filter = [SectionListFilter]

    def section_name(self, obj):
        return obj.section.name

admin.site.register(Metadata, MetadataAdmin)

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

class LevelListFilter(admin.SimpleListFilter):
   """
    Custom filter for loading slum / city level data accordingly.
   """
   title = 'Level filter'
   parameter_name = 'level'

   def lookups(self, request, model_admin):
       return(
           ('City','City level'),
           ('Slum', 'Slum level')
       )

   def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(content_type__model = self.value().lower())

class ComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'content_type', 'component_name', 'number', 'shape_type')
    search_fields = ['component_city__name__city_name','component_slum__name','metadata__name','housenumber']
    #Above/below contains couple of generic foreign keys component_city and component_slum
    ordering = ['metadata__name','housenumber']
    list_filter = [LevelListFilter, ComponentTypeFilter]

    def number(self, obj):
        return obj.housenumber

    def name(self, obj):
        return obj.content_type.model_class().objects.get(id=obj.object_id).name

    def component_name(self, obj):
        return obj.metadata.name

    def shape_type(self, obj):
        return obj.shape.geom_type

    name.admin_order_field = 'component_slum__name'
    component_name.admin_order_field = 'metadata__name'

admin.site.register(Component, ComponentAdmin)
