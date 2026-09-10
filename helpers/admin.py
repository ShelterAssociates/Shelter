from django.contrib import admin
from django.utils import timezone
from .models import (
    ExportRequest,
    FormSubmission,
    OTPVerification,
    PhotoTypeItem,
    ReminderTracker,
    SlumPhoto,
    SlumPhotoUpload,
    SponsorPhotoConfig,
)


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("email", "task", "slum", "is_verified", "created_at", "expiry_time")
    list_filter = ("task", "is_verified")
    search_fields = ("email", "task", "slum__name")


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "mobile", "task", "slum", "otp_verified", "created_at")
    list_filter = ("task", "otp_verified")
    search_fields = ("name", "email", "mobile", "slum__name")


@admin.register(ReminderTracker)
class ReminderTrackerAdmin(admin.ModelAdmin):
    list_display = (
        "reminder_type",
        "month",
        "year",
        "email",
        "status",
        "reminder_sent_count",
    )
    list_filter = ("status", "reminder_type", "month", "year")
    search_fields = ("email", "reminder_type")


@admin.register(PhotoTypeItem)
class PhotoTypeItemAdmin(admin.ModelAdmin):
    list_display = ["full_path_display", "parent", "is_visible", "order"]
    list_editable = ["is_visible", "order"]
    list_filter = ["is_visible"]
    search_fields = ["name", "parent__name"]

    def full_path_display(self, obj):
        return obj.full_path()

    full_path_display.short_description = "Photo type path"


@admin.register(SponsorPhotoConfig)
class SponsorPhotoConfigAdmin(admin.ModelAdmin):
    list_display = (
        "sponsor",
        "name",
        "is_visible_in_photo_upload",
    )
    list_editable = ("is_visible_in_photo_upload",)
    search_fields = (
        "sponsor__organization_name",
        "name",
    )

    def sponsor_organization_name(self, obj):
        if obj.sponsor and obj.sponsor.organization_name:
            return obj.sponsor.organization_name
        return ""

    sponsor_organization_name.short_description = "Sponsor"


class SlumPhotoInline(admin.TabularInline):
    model = SlumPhoto
    extra = 0
    readonly_fields = (
        "file_name",
        "web_view_link",
        "web_content_link",
        "drive_file_id",
        "size_bytes",
        "content_type",
    )


@admin.register(SlumPhotoUpload)
class SlumPhotoUploadAdmin(admin.ModelAdmin):
    list_display = (
        "slum",
        "project_type",
        "photo_date",
        "is_city_level",
        "is_other_upload",
        "photo_type_item_display",
        "sponsor_config",
        "uploaded_by",
        "uploaded_at",
    )
    list_filter = ("sponsor_config", "uploaded_at")
    search_fields = (
        "slum__name",
        "photo_type_item_name",
        "project_type_other",
        "photo_comment",
    )
    inlines = (SlumPhotoInline,)

    def photo_type_item_display(self, obj):
        if obj.photo_type_path:
            return obj.photo_type_path
        if obj.photo_type_item:
            return obj.photo_type_item.full_path()
        return obj.photo_type_item_name

    photo_type_item_display.short_description = "Photo type"

@admin.register(ExportRequest)
class ExportRequestAdmin(admin.ModelAdmin):
    """The one place to see every generated download, of any kind.

    Categorised by export_type so photo, RIM and GIS requests sit in one list
    and can be filtered apart.
    """

    list_display = (
        "id",
        "export_type",
        "status",
        "scope",
        "requested_by",
        "email",
        "item_count",
        "size_display",
        "failure_count",
        "created_on",
        "finished_on",
    )
    list_filter = ("export_type", "status", "created_on")
    search_fields = ("email", "scope", "error")
    date_hierarchy = "created_on"
    readonly_fields = (
        "export_type",
        "requested_by",
        "email",
        "scope",
        "slum",
        "params",
        "item_count",
        "bytes_total",
        "file_path",
        "failures",
        "error",
        "created_on",
        "started_on",
        "finished_on",
    )
    actions = ("rerun_exports",)

    def size_display(self, obj):
        return obj.size_display

    size_display.short_description = "Size"

    def failure_count(self, obj):
        return obj.failure_count

    failure_count.short_description = "Failed photos"

    def rerun_exports(self, request, queryset):
        """Re-queue failed photo exports.

        This is the recovery path for a disk-space failure: the developer is
        emailed, frees space, then re-runs from here. The next cron tick picks
        it up and emails the original requester on success.
        """
        eligible = queryset.filter(export_type="photo", status="failed")
        updated = eligible.update(
            status="queued",
            error=None,
            started_on=None,
            finished_on=None,
            item_count=0,
            bytes_total=0,
            file_path=None,
        )
        skipped = queryset.count() - updated
        message = "Re-queued {} photo export(s).".format(updated)
        if skipped:
            message += (
                " Skipped {} row(s): only failed photo exports can be re-run "
                "(RIM and GIS exports run in their own threads).".format(skipped)
            )
        self.message_user(request, message)

    rerun_exports.short_description = "Re-run selected exports"

    def has_add_permission(self, request):
        # Rows are created by the export flows, never by hand.
        return False
