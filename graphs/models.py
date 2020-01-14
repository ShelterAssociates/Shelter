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
	kobo_id = models.IntegerField(null=True, blank=True)

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

	def __str__(self):
		return str(self.slum)

class SlumCTBdataSplit(models.Model):
    """
    Model for Slum rim-CTB data
    """
    id = models.AutoField(primary_key=True)
    slum = models.ForeignKey(Slum)
    city = models.ForeignKey(City)
    ctb_id = models.IntegerField(null=True)
    electricity_in_ctb = models.TextField(blank=True, null=True)
    sewage_disposal_system = models.TextField(blank=True, null=True)
    ctb_available_at_night = models.TextField(blank=True, null=True)
    cleanliness_of_the_ctb = models.TextField(blank=True, null=True)
    ctb_cleaning_frequency = models.TextField(blank=True,null=True)
    water_availability = models.TextField(blank=True, null=True)
    water_supply_type = models.TextField(blank=True, null=True)
    ctb_structure_condition= models.TextField(blank=True,null=True)
    doors_in_good_condtn = models.TextField(blank=True, null=True)
    seats_in_good_condtn = models.TextField(blank=True, null=True)
    ctb_tank_capacity= models.TextField(blank=True, null=True)
    cost_of_ctb_use= models.TextField(blank=True,null=True)
    ctb_caretaker = models.TextField(blank=True,null=True)
    ctb_for_child =models.TextField(blank=True,null=True)
    cond_of_ctb_for_child=models.TextField(blank=True,null=True)

    def __str__(self):
        return str(self.slum)

class SlumDataSplit(models.Model):
	'''
	Slum RIM data,section wise
	'''
	slum = models.ForeignKey(Slum)
	city = models.ForeignKey(City)
	#General section
	land_status = models.TextField(blank=True, null=True)
	land_ownership = models.TextField(blank=True, null=True)
	land_topography = models.TextField(blank=True, null=True)
	#Water
	availability_of_water = models.TextField(blank=True,null=True)
	quality_of_water = models.TextField(blank=True, null=True)
	coverage_of_water = models.TextField(blank=True, null=True)
	alternative_source_of_water = models.TextField(blank=True, null=True)
	#Waste
	community_dump_sites = models.TextField(blank=True, null=True)
	dump_in_drains = models.TextField(blank=True, null=True)
	number_of_waste_container = models.TextField(blank=True, null=True)
	waste_coverage_by_mla_tempo =models.TextField(blank=True, null=True)
	waste_coverage_door_to_door =models.TextField(blank=True, null=True)
	waste_coverage_by_ghantagadi =models.TextField(blank=True, null=True)
	waste_coverage_by_ulb_van=models.TextField(blank=True, null=True)
	waste_coll_freq_by_mla_tempo =models.TextField(blank=True, null=True)
	waste_coll_freq_door_to_door =models.TextField(blank=True, null=True)
	waste_coll_freq_by_ghantagadi =models.TextField(blank=True, null=True)
	waste_coll_freq_by_ulb_van=models.TextField(blank=True, null=True)
	waste_coll_freq_by_garbage_bin = models.TextField(blank=True,null=True)
	#Road
	is_the_settlement_below_or_above = models.TextField(blank=True, null=True)
	are_the_huts_below_or_above = models.TextField(blank=True, null=True)
	point_of_vehicular_access = models.TextField(blank=True, null=True)
	#Drain n Gutter
	do_the_drains_get_blocked = models.TextField(blank=True, null=True)
	is_the_drainage_gradient_adequ = models.TextField(blank=True, null=True)
	do_gutters_flood = models.TextField(blank=True, null=True)
	is_gutter_gradient_adequate = models.TextField(blank=True, null=True)

	class Meta:
		unique_together = ('id', 'slum')

	def __str__(self):
		return str(self.slum)

	def __unicode__(self):
		return str(self.slum)

class DashboardData(models.Model):
   """
   Dashboard card data
   """
   slum = models.ForeignKey(Slum)
   city = models.ForeignKey(City)
   created_on = models.DateTimeField(default=datetime.datetime.now)
   modified_on = models.DateTimeField(default=datetime.datetime.now)
   household_count = models.FloatField(blank= True,null=True)
   occupied_household_count = models.IntegerField(blank=True,null=True)
   # Genreal section columns
   gen_avg_household_size = models.FloatField(blank= True,null=True)
   gen_tenement_density = models.FloatField(blank= True,null=True) # get_slum_area_size_in_hectors
   household_owners_count = models.FloatField(blank=True,null=True)
   get_shops_count = models.IntegerField(blank=True,null=True)
		   # gen_sex_ration = models.IntegerField(blank= True,null=True)
		   # gen_odf_status = models.IntegerField(blank= True,null=True)
   # Waste section columns
   waste_no_collection_facility_percentile = models.FloatField(blank=True, null=True) # repalce this field to garbage_bin_facility
   waste_door_to_door_collection_facility_percentile = models.FloatField(blank=True, null=True)
   waste_dump_in_open_percent= models.FloatField(blank=True, null=True)
   # water section columns
   water_individual_connection_percentile = models.FloatField(blank=True,null=True)
   water_shared_service_percentile  = models.FloatField(blank=True, null= True)
   waterstandpost_percentile = models.FloatField(blank=True, null= True)
   # Road
   pucca_road = models.FloatField(blank= True,null=True)
   kutcha_road = models.FloatField(blank= True,null=True)
   road_with_no_vehicle_access = models.FloatField(blank= True,null=True)
   pucca_road_coverage = models.FloatField(blank= True,null=True)
   kutcha_road_coverage = models.FloatField(blank= True,null=True)
   total_road_area = models.FloatField(blank=True,null=True)
   # Drainage
   drains_coverage =models.FloatField(blank= True,null=True)
   # Toilet
   toilet_seat_to_person_ratio = models.FloatField(blank= True,null=True) # total_toilet_seats
   fun_male_seats = models.IntegerField(blank= True,null=True)#toilet seats in use (male)
   fun_fmale_seats = models.IntegerField(blank= True,null=True)#toilet seats in use (female)
   toilet_men_women_seats_ratio = models.FloatField(blank= True,null=True)#toilet seats in use (mix)
   individual_toilet_coverage =models.FloatField(blank= True,null=True)
   open_defecation_coverage = models.FloatField(blank= True,null=True)
   ctb_coverage = models.FloatField(blank= True,null=True)
   #dashboard parameters
   people_impacted = models.IntegerField(blank= True,null=True)
   count_of_toilets_completed = models.IntegerField(blank= True,null=True)
   slum_population = models.IntegerField(blank= True,null=True)

   class Meta:
	   unique_together = ('id', 'slum')
	   verbose_name = 'Dashboard data'
	   verbose_name_plural = 'Dashboard data'

   def __str__(self):
	   return str(self.slum)

   def __unicode__(self):
	   return str(self.slum)