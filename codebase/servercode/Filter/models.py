from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
import datetime



CHOICES_ALL = (('1', 'All'),
					  ('1', 'Individual'),
					  ('2', 'User Type'))

class FilterMaster(models.Model):
	name = models.CharField(max_length=512)
	is_deployed = models.CharField(max_length=1)
	visible_to = models.IntegerField(choices=CHOICES_ALL)
	created_by = models.ForeignKey(User)
	created_on= models.DateTimeField(default= datetime.datetime.now())
	class Meta: 
	 	verbose_name = 'Filter Detial' 
	 	verbose_name_plural = 'Filter Details'  


class Filter(models.Model):
	query = models.CharField(max_length=4096)
	filter_master = models.ForeignKey(FilterMaster)
	class Meta: 
	 	verbose_name = 'Filter'
	 	verbose_name_plural = 'Filters'  


class FilterMasterMetadata(models.Model):
	user_id = models.ForeignKey(User,related_name="User")
	user_type = models.ForeignKey(Group,related_name="Group")
	filter_id = models.ForeignKey(FilterMaster,related_name="Filter_Master")
	class Meta: 
	 	verbose_name = 'Filter Access'
	 	verbose_name_plural = 'Filter Access'  
