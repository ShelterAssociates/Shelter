from django.contrib import admin
from .models import (
	Deliverable,
	WorkProgressParameter,
	BeneficiaryIndicator,
	SponsorProjectReportDetails,
	SponsorProjectDeliverable,
	SponsorProjectMonthlyReportDetails,
	SponsorProjectMonthlyWorkProgress,
	SponsorProjectMonthlyBeneficiaryValue,
	SponsorProjectMonthlyDeliverableAchievement,
	SponsorProjectMonthlyPhoto,
)

from master.models import Slum




# =================================================
# INLINE CONFIGURATIONS
# =================================================

class SponsorProjectDeliverableInline(admin.TabularInline):
	model = SponsorProjectDeliverable
	extra = 1


class SponsorProjectMonthlyWorkProgressInline(admin.TabularInline):
	model = SponsorProjectMonthlyWorkProgress
	extra = 0
	autocomplete_fields = ["location"]
	readonly_fields = ("location", "parameter")
	can_delete = True

	def get_queryset(self, request):
		qs = super().get_queryset(request)

		# Ensure rows exist for the monthly report
		from reports.services.monthly_report_service import initialize_monthly_work_progress

		for obj in qs:
			initialize_monthly_work_progress(obj.monthly_report)

		return qs

class SponsorProjectMonthlyBeneficiaryValueInline(admin.TabularInline):
	model = SponsorProjectMonthlyBeneficiaryValue
	extra = 1


class SponsorProjectMonthlyDeliverableAchievementInline(admin.TabularInline):
	model = SponsorProjectMonthlyDeliverableAchievement
	extra = 1


class SponsorProjectMonthlyPhotoInline(admin.TabularInline):
	model = SponsorProjectMonthlyPhoto
	extra = 1


# =================================================
# PROJECT LEVEL ADMIN
# =================================================

@admin.register(SponsorProjectReportDetails)
class SponsorProjectReportAdmin(admin.ModelAdmin):

	list_display = (
		"sponsor_project",
		"start_month",
		"end_month",
	)

	list_filter = ("sponsor_project",)

	filter_horizontal = ("project_locations",)

	inlines = [SponsorProjectDeliverableInline]


# =================================================
# MONTHLY LEVEL ADMIN
# =================================================

@admin.register(SponsorProjectMonthlyReportDetails)
class SponsorProjectMonthlyReportAdmin(admin.ModelAdmin):

	list_display = ("month_display", "project_name", "status")

	list_filter = ("project_report", "month", "status")

	date_hierarchy = "month"

	inlines = [
		SponsorProjectMonthlyWorkProgressInline,
		SponsorProjectMonthlyBeneficiaryValueInline,
		SponsorProjectMonthlyDeliverableAchievementInline,
		SponsorProjectMonthlyPhotoInline,
	]


	def month_display(self, obj):
		return obj.month.strftime("%b %Y")
	month_display.short_description = "Month"


	def project_name(self, obj):
		return obj.project_report.sponsor_project
	project_name.short_description = "Project"


# =================================================
# MASTER TABLE ADMINS
# =================================================

@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):

	list_display = ("name", "is_active")

	list_filter = ("is_active",)

	search_fields = ("name",)


@admin.register(WorkProgressParameter)
class WorkProgressParameterAdmin(admin.ModelAdmin):

	list_display = ("name", "unit", "is_active")

	list_filter = ("is_active",)

	search_fields = ("name",)


@admin.register(BeneficiaryIndicator)
class BeneficiaryIndicatorAdmin(admin.ModelAdmin):

	list_display = ("name", "unit", "is_active")

	list_filter = ("is_active",)

	search_fields = ("name",)


# =================================================
# OPTIONAL: DIRECT ACCESS ADMINS
# =================================================

@admin.register(SponsorProjectMonthlyWorkProgress)
class SponsorProjectMonthlyWorkProgressAdmin(admin.ModelAdmin):

	list_display = ("monthly_report", "location", "parameter", "value")

	list_filter = ("parameter", "location")


@admin.register(SponsorProjectMonthlyBeneficiaryValue)
class SponsorProjectMonthlyBeneficiaryValueAdmin(admin.ModelAdmin):

	list_display = ("monthly_report", "indicator", "value")

	list_filter = ("indicator",)


@admin.register(SponsorProjectMonthlyDeliverableAchievement)
class SponsorProjectMonthlyDeliverableAchievementAdmin(admin.ModelAdmin):

	list_display = ("monthly_report", "deliverable", "value")

	list_filter = ("deliverable",)


@admin.register(SponsorProjectMonthlyPhoto)
class SponsorProjectMonthlyPhotoAdmin(admin.ModelAdmin):

	list_display = ("monthly_report", "uploaded_at")