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
	ff_data = JSONField(null = True, blank = True)

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

class SlumData(models.Model):
	"""
	Slum level RIM data collection.
	"""
	slum = models.ForeignKey(Slum)
	city = models.ForeignKey(City)
	submission_date = models.DateTimeField()
	created_on = models.DateTimeField(default=datetime.datetime.now)
	modified_on = models.DateTimeField(default=datetime.datetime.now)
	rim_data = JSONField(null=True, blank=True)

	class Meta:
		verbose_name = 'Slum data'
		verbose_name_plural = 'Slum data'

	def __str__(self):
		return str(self.slum)

	def __unicode__(self):
		return str(self.slum)

class QolScoreData(models.Model):
	"""
	Model to save quality of living scores
	"""
	slum = models.ForeignKey(Slum)
	city = models.ForeignKey(City) #city.name
	created_date = models.DateField(default=datetime.datetime.now)# need to change
	modified_date = models.DateField(default=datetime.datetime.now)
	general = models.FloatField(default=None)
	gutter = models.FloatField(default=None)
	water = models.FloatField(default=None)
	waste = models.FloatField(default=None)
	drainage = models.FloatField(default=None)
	road = models.FloatField(default=None)
	str_n_occup = models.FloatField(default=None)
	toilet = models.FloatField(default=None)
	total_score = models.FloatField(default=None)

	def __str__(self):
		return str(self.slum)




