from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
import datetime
from Masters.models import Slum

class Sponser(models.Model):
	organization = models.CharField(max_length=200)
	address = models.CharField(max_length=2048)
	Phonenumber = models.CharField(max_length=50)
	description = models.CharField(max_length=2048)
	image = models.CharField(max_length=2048)



Type_CHOICES = (('0', 'Intervention'),
					  ('1', 'Collection'))


class Sponsor_Project(models.Model):
	Name = models.CharField(max_length=512)
	Type =  models.IntegerField(choices=Type_CHOICES)
	Sponsor_id = models.ForeignKey(Sponser)
	createdBy = models.ForeignKey(User)
	createdOn= models.DateTimeField(default= datetime.datetime.now())
	def __unicode__(self):
		return self.Name


class Sponsor_ProjectMetadata(models.Model):
	household_code = models.IntegerField()
	slum_id = models.ForeignKey(Slum)
	Sponsor_Project_id = models.ForeignKey(Sponsor_Project)


class Sponsor_user(models.Model):
	Sponsor_id = models.ForeignKey(Sponser)
	auth_user_id = models.ForeignKey(User)



