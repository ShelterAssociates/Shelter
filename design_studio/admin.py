from django.contrib import admin

from design_studio.models import DesignActivity, DesignAsset, DesignBatch, DesignFont, DesignTemplate


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DesignTemplate)
class DesignTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "plate_type", "output_kind", "version", "dpi", "is_default", "is_active", "updated_on")
    list_filter = ("plate_type", "output_kind", "is_default", "is_active")
    search_fields = ("name",)
    readonly_fields = ("parent", "version", "preset_key", "created_by", "created_on", "updated_on")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DesignAsset)
class DesignAssetAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "recolourable", "is_default", "created_on")
    list_filter = ("kind", "is_default")


@admin.register(DesignFont)
class DesignFontAdmin(admin.ModelAdmin):
    list_display = ("name", "variation", "created_on")


@admin.register(DesignBatch)
class DesignBatchAdmin(ReadOnlyAdmin):
    list_display = ("pk", "plate_type", "slum_name", "original_name", "status", "row_count", "made_count", "skipped_count",
                    "requested_by", "created_on", "finished_on")
    list_filter = ("status", "plate_type", "source")
    search_fields = ("original_name", "slum_name", "city_name", "requested_by__username")
    exclude = ("file_path",)


@admin.register(DesignActivity)
class DesignActivityAdmin(ReadOnlyAdmin):
    list_display = ("created_on", "user", "action", "batch", "template", "detail", "ip")
    list_filter = ("action", "created_on")
    search_fields = ("user__username", "detail")
    date_hierarchy = "created_on"
