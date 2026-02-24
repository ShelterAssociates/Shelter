from django.db import models
from django.core.exceptions import ValidationError
from sponsor.models import SponsorProject
from master.models import Slum
import uuid

def sponsor_project_photo_upload_path(instance, filename):
	"""
	Upload path structure:
	sponsor_projects/<sponsor_project_id>/<YYYY-MM>/<unique_filename>
	"""

	# generate safe unique filename
	ext = filename.split('.')[-1]
	filename = f"{uuid.uuid4()}.{ext}"

	project = instance.monthly_report.project_report.sponsor_project
	month = instance.monthly_report.month.strftime("%Y-%m")

	return f"sponsor_projects/{project.id}/{month}/{filename}"

# =================================================
# MASTER TABLES
# These define reusable indicators and deliverables.
# No transactional data should be stored here.
# =================================================


class Deliverable(models.Model):
	"""
	Master table for project deliverables.
	Examples:
	- Spatial Mapping
	- One Home One Toilet
	- Menstrual Hygiene Management
	- Community Mobilization

	This table defines WHAT can be delivered.
	Actual targets and achievements are stored elsewhere.
	"""

	name = models.CharField(max_length=255, unique=True)
	description = models.TextField(blank=True, null=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		verbose_name = "Deliverable"
		verbose_name_plural = "08. Deliverables"


	def __str__(self):
		return self.name


class WorkProgressParameter(models.Model):
	"""
	Master table for monthly work progress parameters.

	These represent operational activities tracked every month.
	Examples:
	- Total Agreements
	- Toilets Completed
	- Toilets Under Construction
	- Mobilization Activities Conducted

	These parameters are NOT fixed to a project or month.
	They are selected dynamically per month.
	"""

	name = models.CharField(max_length=255, unique=True)
	description = models.TextField(blank=True, null=True)
	unit = models.CharField(max_length=50, blank=True, null=True)
	is_active = models.BooleanField(default=True)
	
	class Meta:
		verbose_name = "Work progress parameter"
		verbose_name_plural = "09. Work progress parameters"
		
	def __str__(self):
		return self.name


class BeneficiaryIndicator(models.Model):
	"""
	Master table for beneficiary indicators.

	These represent who benefited from the project.
	Examples:
	- Total Households Benefited
	- Total Individuals Benefited
	- Female Beneficiaries
	- Disabled Beneficiaries

	Indicators are flexible and can change over time
	without changing the database schema.
	"""

	name = models.CharField(max_length=255, unique=True)
	description = models.TextField(blank=True, null=True)
	unit = models.CharField(max_length=50, blank=True, null=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		verbose_name = "Beneficiary indicator"
		verbose_name_plural = "10. Beneficiary indicators"

	def __str__(self):
		return self.name


# =================================================
# PROJECT LEVEL
# These models define project configuration.
# Data here changes rarely.
# =================================================


class SponsorProjectReportDetails(models.Model):
	"""
	Project-level reporting configuration.

	This represents ONE sponsor project and defines:
	- Which slums are covered
	- Project duration (month-wise)
	- Which deliverables are part of the project

	No monthly data should be stored here.
	"""

	sponsor_project = models.ForeignKey(
		SponsorProject,
		on_delete=models.CASCADE,
		related_name="project_reports"
	)

	project_locations = models.ManyToManyField(
		Slum,
		related_name="sponsor_project_reports"
	)

	# Stored as DateField but ALWAYS normalized to first day of month
	start_month = models.DateField()
	end_month = models.DateField()

	# Deliverables selected for this project with targets
	deliverables = models.ManyToManyField(
		Deliverable,
		through="SponsorProjectDeliverable",
		related_name="project_reports"
	)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Sponsor project report"
		verbose_name_plural = "01. Sponsor project reports"
		
	def clean(self):
		"""
		Ensures:
		- Only month/year is meaningful
		- Start month is before end month
		"""
		if self.start_month and self.start_month.day != 1:
			self.start_month = self.start_month.replace(day=1)
		if self.end_month and self.end_month.day != 1:
			self.end_month = self.end_month.replace(day=1)
		if self.start_month and self.end_month and self.start_month > self.end_month:
			raise ValidationError("Start month cannot be after end month")

	def __str__(self):
		return f"{self.sponsor_project} ({self.start_month.strftime('%m/%Y')} - {self.end_month.strftime('%m/%Y')})"


class SponsorProjectDeliverable(models.Model):
	"""
	Intermediate table linking a project to its deliverables.

	Stores:
	- Deliverable target value
	- Unit of measurement

	Example:
	- Deliverable: Toilets Completed
	- Target: 500
	- Unit: Toilets
	"""

	project_report = models.ForeignKey(
		SponsorProjectReportDetails,
		on_delete=models.CASCADE,
		related_name="project_deliverables"
	)

	deliverable = models.ForeignKey(
		Deliverable,
		on_delete=models.CASCADE
	)

	target_value = models.PositiveIntegerField(blank=True, null=True)
	unit = models.CharField(max_length=100, blank=True, null=True)

	class Meta:
		unique_together = ("project_report", "deliverable")
		verbose_name = "Project deliverable"
		verbose_name_plural = "02. Project deliverables"


	def __str__(self):
		return f"{self.project_report} | {self.deliverable.name}"


# =================================================
# MONTHLY LEVEL
# These models store transactional reporting data.
# This is the MOST important section.
# =================================================


class SponsorProjectMonthlyReportDetails(models.Model):
	"""
	Monthly report header.

	One record per:
	- Project
	- Month

	Acts as the anchor for:
	- Work progress
	- Beneficiary data
	- Deliverable achievements
	- Photos
	"""

	project_report = models.ForeignKey(
		SponsorProjectReportDetails,
		on_delete=models.CASCADE,
		related_name="monthly_reports"
	)

	# Always stored as first day of the month
	month = models.DateField()

	# Many-to-many for easy access to parameters,
	# actual values stored in through table
	work_parameters = models.ManyToManyField(
		WorkProgressParameter,
		through="SponsorProjectMonthlyWorkProgress",
		related_name="monthly_reports"
	)

	remarks = models.TextField(blank=True, null=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)


	class Meta:
		unique_together = ("project_report", "month")
		indexes = [models.Index(fields=["project_report", "month"])]
		verbose_name = "Monthly report"
		verbose_name_plural = "03. Monthly reports"
		

	def clean(self):
		"""
		Normalize month to first day to avoid duplicates like:
		2024-01-01 and 2024-01-15
		"""
		if self.month and self.month.day != 1:
			self.month = self.month.replace(day=1)

	def __str__(self):
		return f"{self.project_report} - {self.month.strftime('%m/%Y')}"



# =================================================
# 4️⃣ MONTHLY TRANSACTIONAL TABLES
# =================================================

class SponsorProjectMonthlyWorkProgress(models.Model):
	"""
	Stores location-wise monthly work progress values.

	Each row represents:
	- One month
	- One location
	- One parameter
	"""

	monthly_report = models.ForeignKey(
		SponsorProjectMonthlyReportDetails,
		on_delete=models.CASCADE,
		related_name="work_progress"
	)

	location = models.ForeignKey(
		Slum,
		on_delete=models.CASCADE,
		related_name="monthly_work_progress"
	)

	parameter = models.ForeignKey(
		WorkProgressParameter,
		on_delete=models.CASCADE
	)

	value = models.PositiveIntegerField(default=0)

	class Meta:
		unique_together = ("monthly_report", "location", "parameter")
		indexes = [
			models.Index(fields=["monthly_report", "location"]),
			models.Index(fields=["parameter"]),
		]
		verbose_name = "Monthly work progress"
		verbose_name_plural = "04. Monthly work progress"

	def __str__(self):
		return f"{self.monthly_report} | {self.location} | {self.parameter.name}"

class SponsorProjectMonthlyBeneficiaryValue(models.Model):
	"""
	Stores month-wise beneficiary statistics.

	Flexible design allows:
	- New beneficiary types
	- Donor-specific reporting
	- No schema change

	Example:
	Month: Feb 2024
	Indicator: Female Beneficiaries
	Value: 340
	"""

	monthly_report = models.ForeignKey(
		SponsorProjectMonthlyReportDetails,
		on_delete=models.CASCADE,
		related_name="beneficiary_values"
	)

	indicator = models.ForeignKey(
		BeneficiaryIndicator,
		on_delete=models.CASCADE
	)

	value = models.PositiveIntegerField(default=0)

	class Meta:
		unique_together = ("monthly_report", "indicator")
		indexes = [
			models.Index(fields=["monthly_report"]),
			models.Index(fields=["indicator"]),
		]
		verbose_name = "Monthly beneficiary value"
		verbose_name_plural = "05. Monthly beneficiary values"

	def __str__(self):
		return f"{self.monthly_report} | {self.indicator.name}"


class SponsorProjectMonthlyDeliverableAchievement(models.Model):
	"""
	Stores month-wise deliverable achievements.

	This is the ONLY place where achievement numbers are entered.
	Project-level achievement is always calculated by summing this table.

	Example:
	Month: Mar 2024
	Deliverable: Toilets Completed
	Value: 40
	"""

	monthly_report = models.ForeignKey(
		SponsorProjectMonthlyReportDetails,
		on_delete=models.CASCADE,
		related_name="deliverable_achievements"
	)

	deliverable = models.ForeignKey(
		Deliverable,
		on_delete=models.CASCADE
	)

	value = models.PositiveIntegerField(default=0)

	class Meta:
		unique_together = ("monthly_report", "deliverable")
		indexes = [
			models.Index(fields=["monthly_report"]),
			models.Index(fields=["deliverable"]),
		]
		verbose_name = "Monthly deliverable achievement"
		verbose_name_plural = "06. Monthly deliverable achievements"

	def __str__(self):
		return f"{self.monthly_report} | {self.deliverable.name}"


class SponsorProjectMonthlyPhoto(models.Model):
	"""
	Stores photographic evidence for monthly reports.

	Images are stored:
	sponsor_projects/<project>/<YYYY-MM>/<image>
	"""

	monthly_report = models.ForeignKey(
		SponsorProjectMonthlyReportDetails,
		on_delete=models.CASCADE,
		related_name="photos"
	)

	image = models.ImageField(upload_to=sponsor_project_photo_upload_path)

	caption = models.CharField(max_length=255, blank=True, null=True)

	uploaded_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Monthly photo"
		verbose_name_plural = "07. Monthly photos"
		
	def __str__(self):
		return f"Photo | {self.monthly_report}"

