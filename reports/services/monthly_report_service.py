from datetime import date

from reports.models import (
	SponsorProjectMonthlyReportDetails,
	SponsorProjectMonthlyWorkProgress,
	SponsorProjectMonthlyBeneficiaryValue,
	SponsorProjectMonthlyDeliverableAchievement,
	WorkProgressParameter,
	BeneficiaryIndicator
)


# =================================================
# CREATE MONTHLY REPORTS FOR PROJECT DURATION
# =================================================

def create_monthly_reports(project_report):

	start = project_report.start_month
	end = project_report.end_month

	current = start

	reports = []

	while current <= end:

		report, created = SponsorProjectMonthlyReportDetails.objects.get_or_create(
			project_report=project_report,
			month=current
		)

		reports.append(report)

		# move to next month
		if current.month == 12:
			current = date(current.year + 1, 1, 1)
		else:
			current = date(current.year, current.month + 1, 1)

	return reports


# =================================================
# WORK PROGRESS INITIALIZATION
# =================================================

def initialize_monthly_work_progress(monthly_report):

	locations = monthly_report.project_report.project_locations.all()

	parameters = WorkProgressParameter.objects.filter(is_active=True)

	rows = []

	for location in locations:
		for parameter in parameters:

			rows.append(
				SponsorProjectMonthlyWorkProgress(
					monthly_report=monthly_report,
					location=location,
					parameter=parameter,
					value=0
				)
			)

	SponsorProjectMonthlyWorkProgress.objects.bulk_create(rows, ignore_conflicts=True)


# =================================================
# BENEFICIARY VALUES INITIALIZATION
# =================================================

def initialize_beneficiary_values(monthly_report):

	indicators = BeneficiaryIndicator.objects.filter(is_active=True)

	rows = []

	for indicator in indicators:

		rows.append(
			SponsorProjectMonthlyBeneficiaryValue(
				monthly_report=monthly_report,
				indicator=indicator,
				value=0
			)
		)

	SponsorProjectMonthlyBeneficiaryValue.objects.bulk_create(rows, ignore_conflicts=True)


# =================================================
# DELIVERABLE ACHIEVEMENTS INITIALIZATION
# =================================================

def initialize_deliverables(monthly_report):

	deliverables = monthly_report.project_report.project_deliverables.all()

	rows = []

	for d in deliverables:

		rows.append(
			SponsorProjectMonthlyDeliverableAchievement(
				monthly_report=monthly_report,
				deliverable=d.deliverable,
				value=0
			)
		)

	SponsorProjectMonthlyDeliverableAchievement.objects.bulk_create(rows, ignore_conflicts=True)