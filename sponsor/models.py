from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from datetime import datetime
from master.models import Slum
from jsonfield import JSONField

LOGO_PATH = 'sponsor_logo/'
PROJECT_PATH = 'sponsor_project/'
class Sponsor(models.Model):
	organization_name = models.CharField(max_length=1024)
	address = models.CharField(max_length=2048)
	website_link = models.CharField(max_length = 2048, null=True, blank=True)
	intro_date = models.DateTimeField(default=datetime.now)
	other_info = models.TextField(null=True, blank=True)
	logo = models.ImageField(upload_to=LOGO_PATH, null=True, blank=True)
	user = models.ForeignKey(User, limit_choices_to={'groups__name': "sponsor"})

	class Meta:
	 	verbose_name = 'Sponsor'
	 	verbose_name_plural = 'Sponsors'

	def __unicode__(self):
		"""Returns string representation of object"""
		return self.organization_name

TYPE_CHOICES = (('1', 'Intervention'),
					  ('2', 'Collection'))

PROJECTSTATUS_CHOICES = ( ('1','Planned'),
							('2','Activated'),
							('3','Closed')
	)

class SponsorProject(models.Model):
	name = models.CharField(max_length=512)
	project_type =  models.CharField(choices=TYPE_CHOICES, max_length=2)
	funds_sponsored = models.DecimalField(max_digits=10, decimal_places=2)
	additional_info = models.TextField(null=True, blank=True)
	start_date = models.DateTimeField(null=True, blank=True)
	end_date = models.DateTimeField(null=True, blank=True)
	funds_utilised = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	status = models.CharField(choices = PROJECTSTATUS_CHOICES, max_length=2)
	created_by = models.ForeignKey(User)
	created_on= models.DateTimeField(default= datetime.now)
	sponsor = models.ForeignKey(Sponsor, null=True, blank=True)
	#project_details = models.ManyToManyField(Sponsor, through='SponsorProjectDetails')

	def __unicode__(self):
		return self.name

	class Meta:
	 	verbose_name = 'Sponsor Project'
	 	verbose_name_plural = 'Sponsor Projects'


class ProjectDocuments(models.Model):
	sponsor_project = models.ForeignKey(SponsorProject)
	document = models.FileField(upload_to=PROJECT_PATH)

	def __unicode__(self):
		return self.document.url

	class Meta:
		verbose_name = 'Project Document'
		verbose_name_plural = 'Project Documents'

class ProjectImages(models.Model):
	sponsor_project = models.ForeignKey(SponsorProject)
	image = models.ImageField(upload_to=PROJECT_PATH)

	def __unicode__(self):
		return self.image.url

	class Meta:
		verbose_name = 'Project Image'
		verbose_name_plural = 'Project Images'


QUARTER_CHOICES = (('1', 'First'),
				   ('2', 'Second'),
				   ('3', 'Third'),
				   ('4','Fourth'))

SPONSORSTATUS_CHOICES = (('1','Initiated'),
				  		 ('2', 'In-progress'),
				  		 ('3', 'Completed'))

class SponsorProjectDetails(models.Model):
	sponsor = models.ForeignKey(Sponsor)
	sponsor_project = models.ForeignKey(SponsorProject)
	slum = models.ForeignKey(Slum)
	household_code = JSONField(null=True, blank=True)
	quarter = models.CharField(choices=QUARTER_CHOICES, max_length=2, null=True, blank=True)
	status = models.CharField(choices=SPONSORSTATUS_CHOICES, max_length=2, null=True, blank=True)
	count = models.IntegerField(null=True, blank=True)

	class Meta:
	 	verbose_name = 'Sponsor Project Detail'
	 	verbose_name_plural = 'Sponsor Project Details'

	def __unicode__(self):
		"""Returns string representation of object"""
		return self.slum.name

class SponsorProjectMOU(models.Model):
	sponsor_project = models.ForeignKey(SponsorProject)
	quarter = models.CharField(choices=QUARTER_CHOICES, max_length=2)
	fund_released = models.DecimalField(max_digits=10, decimal_places=2)
	release_date = models.DateTimeField(default=datetime.now)

	class Meta:
		verbose_name = "Sponsor project MOU"
		verbose_name_plural = "Sponsor project MOU"

	def __unicode__(self):
		return self.sponsor.organization_name + ' ' + self.sponsor_project.name + ' ' + self.quarter

STATUS_CHOICES = (('0','InActive'),
	              ('1','Active'))

class SponsorContact(models.Model):
	sponsor = models.ForeignKey(Sponsor)
	name = models.CharField(max_length=512)
	email_id = models.CharField(max_length=512)
	contact_no = models.CharField(max_length=256, null=True, blank=True)
	status = models.CharField(choices=STATUS_CHOICES, max_length=2)

	class Meta:
	 	verbose_name = 'Sponsor Contact'
	 	verbose_name_plural = 'Sponsor Contacts'

	def __unicode__(self):
		"""Returns string representation of object"""
		return self.name
