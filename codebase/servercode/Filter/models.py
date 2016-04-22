from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
import datetime



CHOICES_ALL = (('1', 'All'),
					  ('1', 'Individual'),
					  ('2', 'User Type'))

class Filter_Master(models.Model):
	Name = models.CharField(max_length=512)
	IsDeployed = models.CharField(max_length=1)
	VisibleTo = models.IntegerField(choices=CHOICES_ALL)
	createdBy = models.ForeignKey(User)
	createdOn= models.DateTimeField(default= datetime.datetime.now())


class Filter(models.Model):
	query = models.CharField(max_length=4096)
	Filter_Master_id = models.ForeignKey(Filter_Master)


class FilterMasterMetadata(models.Model):
	user_id = models.ForeignKey(User,related_name="User")
	user_type = models.ForeignKey(Group,related_name="Group")
	filter_id = models.ForeignKey(Filter_Master,related_name="Filter_Master")