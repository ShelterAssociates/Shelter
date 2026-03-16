from datetime import date

from reports.models import (
	SponsorProjectMonthlyReportDetails,
	SponsorProjectMonthlyWorkProgress,
	SponsorProjectMonthlyBeneficiaryValue,
	SponsorProjectMonthlyDeliverableAchievement,
	WorkProgressParameter,
	BeneficiaryIndicator
)
from django.core.cache import cache
from django.http import JsonResponse

# Helper function to format location names in monthly reports

locations = {
	"Ganesh Nagar/ Pareira Nagar/Shastri Nagar" : "Shastri Nagar",
	"Waghhari Colony / Gholai Nagar" : "Gholai Nagar",
}

def format_location(name):
	return locations.get(name, name)

# =================================================
# MONTHLY REPORT DETAILS VIEW
# =================================================

def monthly_report_details(request, report_id):

	report = SponsorProjectMonthlyReportDetails.objects.select_related(
		"project_report",
		"project_report__sponsor_project",
		"project_report__sponsor_project__sponsor"
	).prefetch_related(
		"project_report__project_locations",
		"project_report__project_deliverables__deliverable",
		"work_progress__location",
		"work_progress__parameter",
		"beneficiary_values__indicator",
		"deliverable_achievements__deliverable",
		"photos"
	).get(id=report_id)

	if report.status == "draft":
		return JsonResponse({
			"status": "draft",
			"message": "Please fill the data in monthly progress report and mark it completed."
		})

	project = report.project_report

	data = {
		"project": {
			"id": project.id,
			"name": str(project.sponsor_project),
			"sponsor_name": project.sponsor_project.sponsor.organization_name if project.sponsor_project.sponsor else None,
			"start_month": project.start_month.strftime("%b %Y") if project.start_month else None,
			"end_month": project.end_month.strftime("%b %Y") if project.end_month else None
		},
		"month": report.month.strftime("%b %Y") if report.month else None,
		"locations": [
			format_location(loc.name)
			for loc in project.project_locations.all()
		],
		"remarks": report.remarks
	}

	work_progress = {}

	for row in report.work_progress.all():
		loc = format_location(row.location.name)

		if loc not in work_progress:
			work_progress[loc] = []

		work_progress[loc].append({
			"parameter": row.parameter.name,
			"value": row.value
		})

	data["work_progress"] = [
		{"location": loc, "parameters": params}
		for loc, params in work_progress.items()
	]

	data["beneficiary_values"] = [
		{
			"indicator": row.indicator.name,
			"value": row.value,
			"icon": request.build_absolute_uri(row.indicator.icon.url) if row.indicator.icon else None
		}
		for row in report.beneficiary_values.all()
	]

	target_map = {
		d.deliverable_id: d
		for d in project.project_deliverables.all()
	}

	data["deliverables"] = []

	for r in report.deliverable_achievements.all():
		

		target_obj = target_map.get(r.deliverable_id)

		target_value = target_obj.target_value if target_obj else None
		unit = target_obj.unit if target_obj else None

		percent = round((r.value / target_value) * 100) if target_value else 0

		data["deliverables"].append({
			"deliverable": r.deliverable.name,
			"abbr": r.deliverable.abbrevation,
			"value": r.value,
			"target": target_value,
			"unit": unit,
			"icon": request.build_absolute_uri(r.deliverable.icon.url) if r.deliverable.icon else None,
			"percent": percent
		})

	data["photos"] = [
		{
			"image": request.build_absolute_uri(p.image.url) if p.image else None,
			"caption": p.caption
		}
		for p in report.photos.all()
	]

	return data

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
