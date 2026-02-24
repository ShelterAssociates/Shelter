from sponsor.models import (
	SponsorProjectMonthlyWorkProgress,
	WorkProgressParameter
)

def initialize_monthly_work_progress(monthly_report):
	locations = monthly_report.project_report.project_locations.all()
	parameters = WorkProgressParameter.objects.filter(is_active=True)

	for location in locations:
		for parameter in parameters:
			SponsorProjectMonthlyWorkProgress.objects.get_or_create(
				monthly_report=monthly_report,
				location=location,
				parameter=parameter
			)