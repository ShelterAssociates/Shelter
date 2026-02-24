from django.db.models.signals import post_save
from django.dispatch import receiver
from reports.models import SponsorProjectMonthlyReportDetails
from reports.services.monthly_report_service import (
	initialize_monthly_work_progress
)

@receiver(post_save, sender=SponsorProjectMonthlyReportDetails)
def create_monthly_work_progress(sender, instance, created, **kwargs):
	if created:
		initialize_monthly_work_progress(instance)