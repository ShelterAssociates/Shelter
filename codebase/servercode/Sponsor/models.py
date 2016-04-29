from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from datetime import datetime
from Masters.models import Slum

class Sponsor(models.Model):
	organization = models.CharField(max_length=200)
	address = models.CharField(max_length=2048)
	website = models.CharField(max_length = 2048)
	intro_date = models.DateTimeField(default=datetime.now())
	other_info = models.CharField(max_length=2048)
	image = models.CharField(max_length=2048)

	class Meta: 
	 	verbose_name = 'Sponsor' 
	 	verbose_name_plural = 'Sponsors'  


TYPE_CHOICES = (('0', 'Intervention'),
					  ('1', 'Collection'))

PROJECTSTATUS_CHOICES = ( ('0','Planned'),
							('1','Activated'),
							('2','Closed')
	)
class SponsorProject(models.Model):
	sponsor = models.ForeignKey(Sponsor)
	name = models.CharField(max_length=512)
	type =  models.IntegerField(choices=TYPE_CHOICES)
	funds_sponsored = models.DecimalField(max_digits=10, decimal_places=2)
	additional_info = models.CharField(max_length=2048)
	start_date = models.DateTimeField()
	end_date = models.DateTimeField()
	funds_utilised = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.CharField(choices = PROJECTSTATUS_CHOICES, max_length=2)
	created_by = models.ForeignKey(User)
	created_on= models.DateTimeField(default= datetime.now())

	def __unicode__(self):
		return self.name

	class Meta: 
	 	verbose_name = 'Sponsor Project' 
	 	verbose_name_plural = 'Sponsor Projects'  

class SponsorProjectDetails(models.Model):
	household_code = models.IntegerField()
	slum = models.ForeignKey(Slum)
	sponsor_project = models.ForeignKey(SponsorProject)

	class Meta: 
	 	verbose_name = 'Sponsor Project Detail' 
	 	verbose_name_plural = 'Sponsor Project Details'  

STATUS_CHOICES = (('0','InActive'),
	('1','Active')
	)

class SponsorContact(models.Model):
	sponsor = models.ForeignKey(Sponsor)
	name = models.CharField(max_length=512)
	email_id = models.CharField(max_length=512)
	contact_no = models.CharField(max_length=256)
	status = models.CharField(choices=STATUS_CHOICES, max_length=2)

	class Meta: 
	 	verbose_name = 'Sponsor Contact' 
	 	verbose_name_plural = 'Sponsor Contacts'  
