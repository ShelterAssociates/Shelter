from django.db import models
from django.contrib.auth.models import User
from master.models import City, Slum
from jsonfield import JSONField
import datetime
from django.utils import timezone

class HouseholdData(models.Model):

	household_number = models.CharField(max_length=5)
	slum = models.ForeignKey(Slum, on_delete=models.DO_NOTHING)
	city = models.ForeignKey(City, on_delete=models.DO_NOTHING)
	submission_date = models.DateTimeField()
	created_date = models.DateTimeField(default=timezone.now)
	rhs_data = JSONField(null=True, blank=True)
	ff_data = JSONField(null = True, blank = True)
	kobo_id = models.IntegerField(null=True, blank=True)
	ff_kobo_id = models.IntegerField(null=True, blank=True)

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
	slum = models.ForeignKey(Slum, default = '', on_delete=models.DO_NOTHING)
	city = models.ForeignKey(City, default = '', on_delete=models.DO_NOTHING)
	submission_date = models.DateTimeField()
	created_date = models.DateTimeField(default=timezone.now)
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
	slum = models.ForeignKey(Slum, on_delete=models.DO_NOTHING)
	city = models.ForeignKey(City, on_delete=models.DO_NOTHING)
	submission_date = models.DateTimeField()
	created_on = models.DateTimeField(default=timezone.now)
	modified_on = models.DateTimeField(default=timezone.now)
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
	slum = models.ForeignKey(Slum, on_delete=models.DO_NOTHING)
	city = models.ForeignKey(City, on_delete=models.DO_NOTHING)
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
    slum = models.ForeignKey(Slum, on_delete=models.DO_NOTHING)
    city = models.ForeignKey(City, on_delete=models.DO_NOTHING)
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
	slum = models.ForeignKey(Slum, on_delete=models.DO_NOTHING)
	city = models.ForeignKey(City, on_delete=models.DO_NOTHING)
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
   slum = models.ForeignKey(Slum, on_delete=models.DO_NOTHING)
   city = models.ForeignKey(City, on_delete=models.DO_NOTHING)
   created_on = models.DateTimeField(default=datetime.datetime.now)
   modified_on = models.DateTimeField(default=datetime.datetime.now)
   household_count = models.FloatField(blank= True,null=True)
   occupied_household_count = models.IntegerField(blank=True,null=True)
   kutcha_household_cnt = models.IntegerField(blank = True, null = True, default = 0)
   puccha_household_cnt = models.IntegerField(blank = True, null = True, default = 0)
   semi_puccha_household_cnt = models.IntegerField(blank = True, null = True, default = 0)
   # Genreal section columns
   gen_avg_household_size = models.FloatField(blank= True,null=True)
   gen_tenement_density = models.FloatField(blank= True,null=True) # get_slum_area_size_in_hectors
   household_owners_count = models.FloatField(blank=True,null=True)
   get_shops_count = models.IntegerField(blank=True,null=True)
		   # gen_sex_ration = models.IntegerField(blank= True,null=True)
		   # gen_odf_status = models.IntegerField(blank= True,null=True)
   # Waste section columns
   waste_data_available = models.FloatField(blank=True, null=True)
   waste_no_collection_facility_percentile = models.FloatField(blank=True, null=True) # repalce this field to garbage_bin_facility
   waste_door_to_door_collection_facility_percentile = models.FloatField(blank=True, null=True)
   waste_dump_in_open_percent= models.FloatField(blank=True, null=True)
   waste_other_services = models.FloatField(blank=True, null=True)
   # water section columns
   water_data_available = models.FloatField(blank=True, null=True)
   water_individual_connection_percentile = models.FloatField(blank=True,null=True)
   water_shared_service_percentile  = models.FloatField(blank=True, null= True)
   waterstandpost_percentile = models.FloatField(blank=True, null= True)
   water_other_services= models.FloatField(blank=True, null=True)
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
   toilet_data_available = models.FloatField(blank=True, null=True)
   individual_toilet_coverage =models.FloatField(blank= True,null=True)
   open_defecation_coverage = models.FloatField(blank= True,null=True)
   ctb_coverage = models.FloatField(blank= True,null=True)
   shared_group_toilet_coverage = models.FloatField(blank= True,null=True, default = 0)
   other_services_toilet_coverage = models.FloatField(blank= True,null=True, default = 0)
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

# Model for covid data 
class CovidData(models.Model):
	household_number = models.IntegerField(null = True, verbose_name="House Number")
	slum = models.ForeignKey(Slum, on_delete=models.CASCADE)
	city = models.IntegerField(null = True)

	covid_uuid = models.CharField(max_length=100, verbose_name='Covid UUID', null=True)
	surveyor_name = models.CharField(max_length=100, verbose_name='Name of the surveyor', null=True)

	date_of_survey = models.DateField(null=True, verbose_name="Date Of Survey")
	last_modified_date = models.DateField(null=True, verbose_name='Last Modified Date')

	family_member_name = models.CharField(max_length=100, verbose_name='Family member name', null=True)
	gender = models.CharField(max_length=100, verbose_name='Gender', null=True)
	age = models.IntegerField(null=True, verbose_name='Age')
	aadhar_number = models.CharField(max_length=100, verbose_name='Addhar number', null=True)
	do_you_have_any_other_disease = models.CharField(max_length=100, verbose_name='Do you have any other disease', null=True)
	if_any_then_which_disease = models.CharField(max_length=100, verbose_name='If any then which disease', null=True)
	preganant_or_lactating_mother = models.CharField(max_length=100,
													 verbose_name='are you pregnant or lactating mother?', null=True)
	registered_for_covid_vaccination = models.CharField(max_length=100,
														verbose_name='Have you registered for covid vaccination?', null=True)
	registered_phone_number = models.CharField(max_length=100, verbose_name='Registered Phone Number', null=True)
	take_first_dose = models.CharField(max_length=100, verbose_name='Did you take first dose?', null= True)
	first_dose_date = models.DateField(null=True, verbose_name='Date of first dose?')
	vaccine_name = models.CharField(max_length=100, verbose_name='Which vaccine taken?', null=True)
	take_second_dose = models.CharField(max_length=100, verbose_name='Did you take second dose?', null=True)
	second_dose_date = models.DateField(null=True, verbose_name='Date of second dose?')
	corona_infected = models.CharField(max_length=100, verbose_name='Have you even been infected with corona?', null=True)
	if_corona_infected_days = models.CharField(max_length=100, verbose_name='If corona infected, how many days it had been since infection?', null=True)
	willing_to_vaccinated = models.CharField(max_length=100, verbose_name='Are you willing to get vaccinated?', null=True)
	if_not_why = models.TextField(verbose_name='If not, why?', null=True)
	note = models.TextField(verbose_name='Note', null=True)

