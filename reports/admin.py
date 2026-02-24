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


# =================================================
# INLINE CONFIGURATIONS
# =================================================

class SponsorProjectDeliverableInline(admin.TabularInline):
	"""
	Allows adding deliverables and targets
	directly inside the project report page.
	"""
	model = SponsorProjectDeliverable
	extra = 1


class SponsorProjectMonthlyWorkProgressInline(admin.TabularInline):
	"""
	Allows entering monthly work progress values
	as dynamic rows.
	"""
	model = SponsorProjectMonthlyWorkProgress
	extra = 1


class SponsorProjectMonthlyBeneficiaryValueInline(admin.TabularInline):
	"""
	Allows entering beneficiary indicators and values
	per month.
	"""
	model = SponsorProjectMonthlyBeneficiaryValue
	extra = 1


class SponsorProjectMonthlyDeliverableAchievementInline(admin.TabularInline):
	"""
	Allows entering monthly deliverable achievements.
	"""
	model = SponsorProjectMonthlyDeliverableAchievement
	extra = 1


class SponsorProjectMonthlyPhotoInline(admin.TabularInline):
	"""
	Allows uploading multiple photos per monthly report.
	"""
	model = SponsorProjectMonthlyPhoto
	extra = 1


# =================================================
# PROJECT LEVEL ADMIN
# =================================================

@admin.register(SponsorProjectReportDetails)
class SponsorProjectReportAdmin(admin.ModelAdmin):
	"""
	Admin for sponsor project reporting setup.
	"""
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
	"""
	Admin for month-wise reporting.
	This is where most data entry happens.
	"""
	list_display = ("project_report", "month")
	list_filter = ("project_report", "month")
	date_hierarchy = "month"

	inlines = [
		SponsorProjectMonthlyWorkProgressInline,
		SponsorProjectMonthlyBeneficiaryValueInline,
		SponsorProjectMonthlyDeliverableAchievementInline,
		SponsorProjectMonthlyPhotoInline,
	]


# =================================================
# MASTER TABLE ADMINS
# =================================================

@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
	"""
	Admin for deliverable master.
	"""
	list_display = ("name", "is_active")
	list_filter = ("is_active",)
	search_fields = ("name",)


@admin.register(WorkProgressParameter)
class WorkProgressParameterAdmin(admin.ModelAdmin):
	"""
	Admin for work progress parameters.
	"""
	list_display = ("name", "unit", "is_active")
	list_filter = ("is_active",)
	search_fields = ("name",)


@admin.register(BeneficiaryIndicator)
class BeneficiaryIndicatorAdmin(admin.ModelAdmin):
	"""
	Admin for beneficiary indicators.
	"""
	list_display = ("name", "unit", "is_active")
	list_filter = ("is_active",)
	search_fields = ("name",)


# =================================================
# OPTIONAL: READ-ONLY ADMIN FOR TRANSACTION TABLES
# (Enable only if you want direct access)
# =================================================

@admin.register(SponsorProjectMonthlyWorkProgress)
class SponsorProjectMonthlyWorkProgressAdmin(admin.ModelAdmin):
	list_display = ("monthly_report", "parameter", "value")
	list_filter = ("parameter",)


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
