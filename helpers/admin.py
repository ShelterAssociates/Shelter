from django.contrib import admin
from .models import FormSubmission, OTPVerification, PhotoTypeItem, ReminderTracker, SlumPhoto, SlumPhotoUpload, SponsorProjectPhotoConfig

# Register your models here.


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
	list_display = ("email", "task", "is_verified", "created_at", "expiry_time")
	list_filter = ("task", "is_verified")
	search_fields = ("email", "task")


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
	list_display = ("name", "email", "mobile", "task", "otp_verified", "created_at")
	list_filter = ("task", "otp_verified")
	search_fields = ("name", "email", "mobile")


@admin.register(ReminderTracker)
class ReminderTrackerAdmin(admin.ModelAdmin):
	list_display = ("reminder_type", "month", "year", "email", "status", "reminder_sent_count")
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


@admin.register(SponsorProjectPhotoConfig)
class SponsorProjectPhotoConfigAdmin(admin.ModelAdmin):
	list_display = ("sponsor_project", "sponsor_organization_name", "is_visible_in_photo_upload")
	list_editable = ("is_visible_in_photo_upload",)
	search_fields = ("sponsor_project__name", "sponsor_project__sponsor__organization_name")

	def sponsor_organization_name(self, obj):
		if obj.sponsor_project and obj.sponsor_project.sponsor:
			return obj.sponsor_project.sponsor.organization_name
		return ""

	sponsor_organization_name.short_description = "Sponsor"


class SlumPhotoInline(admin.TabularInline):
	model = SlumPhoto
	extra = 0
	readonly_fields = ("file_name", "web_view_link", "web_content_link", "drive_file_id", "size_bytes", "content_type")


@admin.register(SlumPhotoUpload)
class SlumPhotoUploadAdmin(admin.ModelAdmin):
	list_display = ("slum", "photo_type_item_display", "sponsor_project", "uploaded_by", "uploaded_at")
	list_filter = ("sponsor_project", "uploaded_at")
	search_fields = ("slum__name", "photo_type_item_name")
	inlines = (SlumPhotoInline,)

	def photo_type_item_display(self, obj):
		if obj.photo_type_path:
			return obj.photo_type_path
		if obj.photo_type_item:
			return obj.photo_type_item.full_path()
		return obj.photo_type_item_name

	photo_type_item_display.short_description = "Photo type"
