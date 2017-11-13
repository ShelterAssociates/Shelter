from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from datetime import datetime
from master.models import Slum
from jsonfield import JSONField
from .birt_ff_report import *
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver

LOGO_PATH = 'sponsor_logo/'
PROJECT_PATH = 'sponsor_project/'
ZIP_PATH = 'FFReport'
class Sponsor(models.Model):
	organization_name = models.CharField(max_length=1024)
	address = models.CharField(max_length=2048)
	website_link = models.CharField(max_length = 2048, null=True, blank=True)
	intro_date = models.DateField(default=datetime.now)
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
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)
	funds_utilised = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	status = models.CharField(choices = PROJECTSTATUS_CHOICES, max_length=2)
	created_by = models.ForeignKey(User)
	created_on= models.DateField(default= datetime.now)
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

	def givename(self):
		return os.path.basename(self.document.name)

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


def zip_path(instance, filename):
	return os.path.join(ZIP_PATH, instance.sponsor_project.sponsor.organization_name, filename)

class SponsorProjectDetails(models.Model):
	sponsor = models.ForeignKey(Sponsor)
	sponsor_project = models.ForeignKey(SponsorProject)
	slum = models.ForeignKey(Slum)
	household_code = JSONField(null=True, blank=True)

	class Meta:
		unique_together = ("sponsor_project", "slum")
	 	verbose_name = 'Sponsor Project Detail'
	 	verbose_name_plural = 'Sponsor Project Details'

	def __unicode__(self):
		"""Returns string representation of object"""
		return self.slum.name

class SponsorProjectDetailsSubFields(models.Model):
	sponsor_project_details = models.ForeignKey(SponsorProjectDetails)
	household_code = JSONField(null=True, blank=True)
	quarter = models.CharField(choices=QUARTER_CHOICES, max_length=2)
	status = models.CharField(choices=SPONSORSTATUS_CHOICES, max_length=2)
	count = models.IntegerField(null=True, blank=True)
	zip_file = models.FileField(upload_to=zip_path, null=True, blank=True)
	zip_created_on = models.DateField(null=True, blank=True)

	class Meta:
	 	verbose_name = 'Sponsor Project Detail Sub Field'
	 	verbose_name_plural = 'Sponsor Project Detail Sub Fields'

	def __unicode__(self):
		"""Returns string representation of object"""
		return self.sponsor_project_details.slum.name

	def save(self):
		"""Override the save method. When the status of the project details changes
			to completed, it will give a call to create the family factsheet report zip file"""
		flag = False
		if self.status == SPONSORSTATUS_CHOICES[2][0]:
			flag = True
			if self.pk and self.status == SponsorProjectDetailsSubFields.objects.get(pk = self.pk).status:
				flag = False

		super(SponsorProjectDetailsSubFields, self).save()
		if flag:
			obj_FFReport = FFReport(self)
			obj_FFReport.generate()

@receiver(pre_save, sender=SponsorProjectDetailsSubFields)
def update_zipfile(sender, instance, **kwargs):
	""" Delete zip file on pre_save. This is needed in case of updation of 
	    zip file, where the older file should be deleted from the location"""
	if instance.pk:
		details = SponsorProjectDetailsSubFields.objects.get(pk=instance.pk)
		if details.zip_file and details.zip_file.url != instance.zip_file.url:
			storage, path = details.zip_file.storage, details.zip_file.path
			storage.delete(path)

@receiver(pre_delete, sender=SponsorProjectDetailsSubFields)
def delete_file(sender, instance, *args, **kwargs):
	""" Deletes thumbnail files on `pre_delete` """
	if instance.zip_file:
		if os.path.isfile(instance.zip_file.path):
			os.remove(instance.zip_file.path)

class SponsorProjectMOU(models.Model):
	sponsor_project = models.ForeignKey(SponsorProject)
	quarter = models.CharField(choices=QUARTER_CHOICES, max_length=2)
	fund_released = models.DecimalField(max_digits=10, decimal_places=2)
	release_date = models.DateField(default=datetime.now)

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
