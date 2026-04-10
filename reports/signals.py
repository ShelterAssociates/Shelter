from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from reports.models import (
    SponsorProjectReportDetails,
    SponsorProjectMonthlyReportDetails
)

from reports.services.monthly_report_service import (
    create_monthly_reports,
    initialize_monthly_work_progress,
    initialize_beneficiary_values,
    initialize_deliverables
)


# Create monthly reports when project report is created
@receiver(post_save, sender=SponsorProjectReportDetails)
def create_project_monthly_reports(sender, instance, created, **kwargs):

    if not created:
        return

    create_monthly_reports(instance)


# Trigger initialization AFTER locations are attached
@receiver(m2m_changed, sender=SponsorProjectReportDetails.project_locations.through)
def initialize_rows_after_locations(sender, instance, action, **kwargs):

    if action != "post_add":
        return

    monthly_reports = SponsorProjectMonthlyReportDetails.objects.filter(
        project_report=instance
    )

    for report in monthly_reports:

        initialize_monthly_work_progress(report)
        initialize_beneficiary_values(report)
        initialize_deliverables(report)