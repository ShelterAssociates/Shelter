from django.contrib import admin

from .models import BulkUpdate


@admin.register(BulkUpdate)
class BulkUpdateAdmin(admin.ModelAdmin):
    list_display = ("original_name", "target_label", "status", "dry_run", "row_count", "requested_by", "created_on")
    list_filter = ("status", "dry_run", "subject_type", "level")
    search_fields = ("original_name", "subject_type", "requested_by__username")
    readonly_fields = tuple(f.name for f in BulkUpdate._meta.fields) + ("target_label",)

    def has_add_permission(self, request):
        return False
