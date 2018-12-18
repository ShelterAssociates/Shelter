from django.db import models
from django.contrib.auth.models import User
from master.models import City, Slum
from jsonfield import JSONField
import datetime
from datetime import date



class HouseholdData(models.Model):

	household_number = models.CharField(max_length=5)
	slum = models.ForeignKey(Slum)
	city = models.ForeignKey(City)
	submission_date = models.DateTimeField()
	created_date = models.DateTimeField(default=datetime.datetime.now)
	rhs_data = JSONField(null=True, blank=True)

	class Meta:
		unique_together = ("slum", "household_number")
		verbose_name = 'Household data'
		verbose_name_plural = 'Household data'

	def __str__(self):
		return str(self.household_number) + ","+ str(self.slum)
	def __unicode__(self):
		return str(self.household_number) + "," + str(self.slum)

class FollowupData(models.Model):

	household_number = models.CharField(max_length=5, default = '')
	slum = models.ForeignKey(Slum, default = '')
	city = models.ForeignKey(City, default = '')
	submission_date = models.DateTimeField()
	created_date = models.DateTimeField(default=datetime.datetime.now)
	followup_data = JSONField(null=True, blank=True)
	flag_followup_in_rhs = models.BooleanField(default=False)

	class Meta:
		verbose_name = 'Followup data'
		verbose_name_plural = 'Followup data'

	def __str__(self):
		return str(self.household_number) + ","+ str(self.slum)

   	def __unicode__(self):
		return str(self.household_number) + ","+ str(self.slum)
