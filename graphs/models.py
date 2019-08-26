from django.db import models
from django.contrib.auth.models import User
from master.models import City, Slum
from jsonfield import JSONField
import datetime
from django.utils import timezone

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

class QOLScoreData(models.Model):
	"""
	Model to save quality of living scores
	"""
	slum = models.ForeignKey(Slum)
	city = models.ForeignKey(City)
	created_date = models.DateTimeField(default=datetime.datetime.now)
	modified_date = models.DateTimeField(default=datetime.datetime.now)
	general = models.FloatField(default=None, blank=True, null=True)
	gutter = models.FloatField(default=None,blank=True, null=True)
	water = models.FloatField(default=None,blank=True, null=True)
	waste = models.FloatField(default=None,blank=True, null=True)
	drainage = models.FloatField(default=None,blank=True, null=True)
	road = models.FloatField(default=None,blank=True, null=True)
	str_n_occup = models.FloatField(default=None,blank=True, null=True)
	toilet = models.FloatField(default=None,blank=True, null=True)
	total_score = models.FloatField(default=None,blank=True, null=True)
	general_percentile = models.FloatField(default=None, blank=True, null=True)
	gutter_percentile = models.FloatField(default=None, blank=True, null=True)
	water_percentile = models.FloatField(default=None, blank=True, null=True)
	waste_percentile = models.FloatField(default=None, blank=True, null=True)
	drainage_percentile = models.FloatField(default=None, blank=True, null=True)
	road_percentile = models.FloatField(default=None, blank=True, null=True)
	str_n_ocup_percentile = models.FloatField(default=None, blank=True, null=True)
	toilet_percentile = models.FloatField(default=None, blank=True, null=True)
	totalscore_percentile = models.FloatField(default=None, blank=True, null=True)

	# def save(QOLScoreData, *args, **kwargs):
	# 	''' On save, update timestamps '''
	# 	if not QOLScoreData.slum_id:
	# 		QOLScoreData.created = timezone.now()
	# 	QOLScoreData.modified = timezone.now()
	# 	return super(User, QOLScoreData).save(*args,**kwargs)

	def __str__(self):
		return str(self.slum)

class DashboardData(models.Model):
   """
   Dashboard card data
   """
   slum = models.ForeignKey(Slum)
   city = models.ForeignKey(City)
   created_on = models.DateTimeField(default=datetime.datetime.now)
   modified_on = models.DateTimeField(default=datetime.datetime.now)
   household_count = models.IntegerField()
   houehold_member_count = models.IntegerField()
   member_size = models.IntegerField()
   tenement_density = models.IntegerField()

   class Meta:
	   unique_together = ('id', 'slum')
	   verbose_name = 'Dashboard data'
	   verbose_name_plural = 'Dashboard data'

   def __str__(self):
	   return str(self.slum)

   def __unicode__(self):
	   return str(self.slum)
