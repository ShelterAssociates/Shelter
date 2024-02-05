"""
Script to get aggregated data.
"""
from graphs.models import *
from .analyse_data import *
from master.models import *
import logging

# The `DashboardCard` class is a subclass of `RHSData` that initializes with a `slum` parameter.
class DashboardCard(RHSData):
    def __init__(self, slum):
        super(DashboardCard,self).__init__(slum)

    def dashboard_page_parameters(self):
        """
        The function updates the dashboard data with the count of completed toilets, the number of
        people impacted, and the slum population.
        """
        population = self.get_household_member_total()
        toilet_count = len(self.toilet_constructed())
        people_impacted = toilet_count * 5
        to_save = DashboardData.objects.update_or_create(slum=self.slum,
                defaults={'count_of_toilets_completed': toilet_count,'people_impacted':people_impacted,
                        'slum_population':population})

    def General_Info(self):
        """
        The function "General_Info" returns information about household ownership, average household
        size, slum area size, and total household count.
        :return: a tuple containing the following values:
        1. household_owners_count
        2. avg_household_size
        3. slum_area_size_in_hectors
        4. household_count
        """
        avg_household_size = self.get_household_member_total()
        slum_area_size_in_hectors = self.get_slum_area_size_in_hectors()
        household_owners_count = self.ownership_status()
        household_count = self.get_household_count()
        return (household_owners_count,avg_household_size, slum_area_size_in_hectors,household_count)

    def save_general(self):
        """
        The function saves general information about a slum to a database.
        """
        """Save information to database"""
        occupied_household_count = len(self.occupied_houses())
        kutcha_hh, puccha_hh, semi_puccha_hh = self.structure_data()
        shops_in_slum = self.get_shop_count()
        (household_owners_count, avg_household_size, slum_area_size_in_hectors, household_count) = self.General_Info()
        to_save = DashboardData.objects.update_or_create(slum = self.slum , defaults ={'city_id': self.slum.electoral_ward.administrative_ward.city.id,
                    'gen_tenement_density' : slum_area_size_in_hectors,'get_shops_count':shops_in_slum,'gen_avg_household_size': avg_household_size,
                    'household_count':household_count,'household_owners_count':household_owners_count,
                    'occupied_household_count':occupied_household_count, 'kutcha_household_cnt' : kutcha_hh, 'puccha_household_cnt' : puccha_hh, 'semi_puccha_household_cnt' : semi_puccha_hh})

    def Waste_Info(self):
        """
        The function calculates the percentage of waste collection from different facilities and adds the
        percentage of other waste collections.
        """
        door_to_door_percent = self.get_waste_facility('Door to door waste collection')
        openspace_percent= self.get_waste_facility('Open space')
        garbage_bin_facility = self.get_waste_facility('Garbage bin')
        ulb = self.get_waste_facility('ULB service')
        guttter = self.get_waste_facility('Inside gutter')
        canal = self.get_waste_facility('Along/Inside canal')
        other_waste_collections = guttter+canal
        return (door_to_door_percent,garbage_bin_facility,openspace_percent,ulb,other_waste_collections)

    def save_waste(self):
        """
        The function saves waste information to the database using the provided parameters.
        """
        (door_to_door_percent,garbage_bin_facility,openspace_percent,ulb,other_waste_collections)= self.Waste_Info()
        to_save = DashboardData.objects.update_or_create(slum =self.slum, defaults=
                                {'waste_door_to_door_collection_facility_percentile': door_to_door_percent,'waste_other_services':other_waste_collections,
            'waste_dump_in_open_percent': openspace_percent,'waste_no_collection_facility_percentile': garbage_bin_facility,'drains_coverage':ulb})

    def Water_Info(self):
        """
        The function "Water_Info" returns the percentage coverage of different types of water services.
        :return: a tuple containing the percentages of individual connection, shared connection, water
        standpost, and other water services.
        """
        individual_connection_percent = self.get_water_coverage('Individual connection')
        shared_connection_percent = self.get_water_coverage('Shared connection')
        water_standpost_percent = self.get_water_coverage('Water standpost')
        hand_pump = self.get_water_coverage('Hand pump')
        water_tanker = self.get_water_coverage('Water tanker')
        from_other_settlements = self.get_water_coverage('From other settlements')
        well = self.get_water_coverage('Well')
        other_water_services = hand_pump+water_tanker+from_other_settlements+well
        return (individual_connection_percent,shared_connection_percent,water_standpost_percent,other_water_services)

    def save_water(self):
        """
        The function saves water-related information to the DashboardData model.
        """
        (individual_connection_percent,shared_connection_percent,water_standpost_percent,other_water_services) = self.Water_Info()
        to_save = DashboardData.objects.update_or_create(slum =self.slum,
            defaults={'water_individual_connection_percentile':individual_connection_percent,'water_other_services':other_water_services,
            'water_shared_service_percentile':shared_connection_percent,'waterstandpost_percentile':water_standpost_percent})

    def Road_Info(self):
        """
        The function "Road_Info" returns information about the road type, road vehicle facility, and
        road coverage.
        :return: a tuple containing the following values:
        1. pucca: 1 if the road type is 'Pucca', 0 otherwise
        2. kutcha: 1 if the road type is 'Kutcha', 0 otherwise
        3. no_vehicle: 1 if the road vehicle facility is 'None', 0 otherwise
        4. pucca_
        """
        pucca = 1 if self.get_road_type() == 'Pucca' else 0
        kutcha = 1 if self.get_road_type() == 'Kutcha' else 0
        no_vehicle = 1 if self.get_road_vehicle_facility() =='None' else 0
        (kutcha_road_area,pucca_road_area,total_road_area) = self.get_road_coverage()
        return (pucca,kutcha,no_vehicle,pucca_road_area,kutcha_road_area,total_road_area)

    def save_road(self):
        """
        The function `save_road` updates or creates a `DashboardData` object with road information such
        as pucca road, kutcha road, road with no vehicle access, pucca road coverage, kutcha road
        coverage, and total road area.
        """
        (pucca,kutcha,no_vehicle,pucca_road_area,kutcha_road_area,total_road_area)= self.Road_Info()
        to_save = DashboardData.objects.update_or_create( slum = self.slum, defaults =
                                {'road_with_no_vehicle_access': no_vehicle,'pucca_road' : pucca,
                                'kutcha_road':kutcha,'pucca_road_coverage':pucca_road_area,
                                'kutcha_road_coverage':kutcha_road_area,'total_road_area':total_road_area})

    def save_toilet(self):
        """
        The function saves toilet data to the DashboardData model.
        """
        own_toilet_count = self.individual_toilet()
        ctb_use_count = self.ctb_count()
        (total_toilet_seats, fun_mix_seats, fun_male_seats, fun_female_seats) = self.get_toilet_data()
        to_save = DashboardData.objects.filter(slum=self.slum).update(individual_toilet_coverage  = own_toilet_count,
                                ctb_coverage = ctb_use_count,toilet_men_women_seats_ratio =  fun_mix_seats, fun_male_seats = fun_male_seats,
                                toilet_seat_to_person_ratio =  total_toilet_seats, fun_fmale_seats = fun_female_seats )

    def save_rim_gen(self):
        """
        The function `save_rim_gen` updates or creates a `SlumDataSplit` object with the given
        `land_owner`, `land_status`, and `topography` values.
        """
        (land_owner,land_status,topography) = self.key_takeaways_general()
        to_save = SlumDataSplit.objects.update_or_create(slum = self.slum, city_id = self.slum.electoral_ward.administrative_ward.city.id,
                defaults = {'land_status':land_status,'land_ownership':land_owner,'land_topography':topography})

    def save_rim_water(self):
        """
        The function saves water-related data for a slum in a database.
        """
        (water_availability, water_coverage, water_quality, alternate_water_source) = self.key_takeaways_water()
        to_save = SlumDataSplit.objects.update_or_create(slum=self.slum,city_id=self.slum.electoral_ward.administrative_ward.city.id,
        defaults={'availability_of_water': water_availability,'coverage_of_water':water_coverage,
                'quality_of_water':water_quality, 'alternative_source_of_water': alternate_water_source})

    def save_rim_waste(self):
        """
        The function saves waste-related data to the database.
        """
        (dump_in_drains,community_dump_site,waste_containers,waste_coll_by_mla_tempo,waste_coll_door_to_door,
        waste_coll_by_ghantagadi,waste_coll_by_ulb_van,waste_freq_bin,waste_freq_by_ghantagadi,waste_freq_by_mla_tempo,
        waste_freq_by_ulb_van,waste_freq_door_to_door) = self.key_takeaways_waste()
        to_save = SlumDataSplit.objects.update_or_create(slum = self.slum, city_id = self.slum.electoral_ward.administrative_ward.city.id,
        defaults = {'dump_in_drains':dump_in_drains,'community_dump_sites':community_dump_site,'number_of_waste_container':waste_containers,
        'waste_coverage_by_mla_tempo': waste_coll_by_mla_tempo,'waste_coverage_door_to_door': waste_coll_door_to_door,
        'waste_coverage_by_ghantagadi':waste_coll_by_ghantagadi,'waste_coverage_by_ulb_van': waste_coll_by_ulb_van,
        'waste_coll_freq_by_garbage_bin':waste_freq_bin, 'waste_coll_freq_by_ghantagadi':waste_freq_by_ghantagadi,
        'waste_coll_freq_by_mla_tempo':waste_freq_by_mla_tempo,'waste_coll_freq_by_ulb_van':waste_freq_by_ulb_van,
        'waste_coll_freq_door_to_door':waste_freq_door_to_door})

    def save_rim_drainGutter(self):
        """
        The function saves the values of drain blockage, drainage gradient, gutter flooding, and gutter
        gradient to the database.
        """
        (drain_block, drain_gradient, gutter_flood, gutter_gradient) = self.key_takeaways_drain_n_gutter()
        to_save = SlumDataSplit.objects.update_or_create(slum = self.slum, city_id = self.slum.electoral_ward.administrative_ward.city.id,
                defaults = {'do_the_drains_get_blocked':drain_block,'is_the_drainage_gradient_adequ':drain_gradient,
                            'do_gutters_flood':gutter_flood, 'is_gutter_gradient_adequate':gutter_gradient})

    def save_rim_road(self):
        """
        The function `save_rim_road` updates or creates a `SlumDataSplit` object with the slum level, huts
        level, and vehicular access information.
        """
        (slum_level, huts_level, vehicular_access) = self.key_takeaways_road()
        to_save = SlumDataSplit.objects.update_or_create(slum = self.slum, city = self.slum.electoral_ward.administrative_ward.city.id,
                defaults = {'is_the_settlement_below_or_above':slum_level,'are_the_huts_below_or_above':huts_level,
                            'point_of_vehicular_access':vehicular_access})

    def call_rim_ctb(self):
        """
        The function "call_rim_ctb" iterates through a list of toilet data and calls another function to
        save each toilet data with a corresponding number.
        """
        ctb = self.slum_data.rim_data['Toilet']
        ctb_no = 0
        for i in ctb:
            ctb_no += 1
            self.save_rim_toilet(i,ctb_no)

    def save_rim_toilet(self,one_ctb,ctb_count):
        """
        The function saves data related to a public toilet in a slum area.
        
        :param one_ctb: The parameter `one_ctb` is a dictionary or object that contains the following
        key-value pairs:
        :param ctb_count: The parameter `ctb_count` represents the count or ID of the CTB (Community
        Toilet Block) that you want to save. It is used to uniquely identify the CTB in the database
        """
        if self.key_takeaways_ctb(one_ctb):
            (electricity, sewage_system, ctb_available_at_night, ctb_cleaning, ctb_cleaning_freq, water_in_ctb,
            water_supply_type,ctb_door, ctb_condition, ctb_seats_good_condtn, ctb_tank_capacity, cost_per_use, ctb_caretaker, for_child,
            ctb_cond_for_child) = self.key_takeaways_ctb(one_ctb)

            to_save = SlumCTBdataSplit.objects.update_or_create(ctb_id = ctb_count,slum = self.slum,city_id = self.slum.electoral_ward.administrative_ward.city.id,
            defaults = {'electricity_in_ctb':electricity,'sewage_disposal_system':sewage_system,'ctb_available_at_night':ctb_available_at_night,
                        'cleanliness_of_the_ctb':ctb_cleaning,'ctb_cleaning_frequency':ctb_cleaning_freq,'water_availability':water_in_ctb,
                        'water_supply_type':water_supply_type,'ctb_structure_condition':ctb_condition,'doors_in_good_condtn':ctb_door,
                        'seats_in_good_condtn':ctb_seats_good_condtn,'ctb_tank_capacity':ctb_tank_capacity,'cost_of_ctb_use':cost_per_use,
                        'ctb_caretaker':ctb_caretaker,'ctb_for_child':for_child,'cond_of_ctb_for_child':ctb_cond_for_child})
        else: pass

def dashboard_data_Save(city):
    slums = Slum.objects.filter(electoral_ward__administrative_ward__city__id__in = [city], associated_with_SA = True).exclude(status = False)
    for slum in slums:
        logging.basicConfig(filename="code_exec.log", format='%(asctime)s %(message)s', filemode='a')
        slum_data = SlumData.objects.filter(slum=slum.id)
        if slum_data.count() > 0:
            # Create a logger
            global logger_obj
            logger_obj = logging.getLogger(__name__)
            logger_obj.setLevel(logging.DEBUG)
            dashboard_data = DashboardCard(slum.id)
            try:
                dashboard_data.save_general()
                logger_obj.info(f'Successfully saved general data for slum {slum.id}')
            except Exception as e:
                logger_obj.error(f'Error in save_general for slum {slum.id}: {e}', exc_info=True)

            try:
                dashboard_data.dashboard_page_parameters()
                logger_obj.info(f'Successfully processed dashboard parameters for slum {slum.id}')
            except Exception as e:
                logger_obj.error(f'Error in dashboard_page_parameters for slum {slum.id}: {e}', exc_info=True)

            try:
                dashboard_data.save_waste()
                logger_obj.info(f'Successfully saved waste data for slum {slum.id}')
            except Exception as e:
                logger_obj.error(f'Error in save_waste for slum {slum.id}: {e}', exc_info=True)

            try:
                dashboard_data.save_water()
                logger_obj.info(f'Successfully saved water data for slum {slum.id}')
            except Exception as e:
                logger_obj.error(f'Error in save_water for slum {slum.id}: {e}', exc_info=True)

            try:
                dashboard_data.save_road()
                logger_obj.info(f'Successfully saved road data for slum {slum.id}')
            except Exception as e:
                logger_obj.error(f'Error in save_road for slum {slum.id}: {e}', exc_info=True)

            try:
                dashboard_data.save_toilet()
                logger_obj.info(f'Successfully saved toilet data for slum {slum.id}')
            except Exception as e:
                logger_obj.error(f'Error in save_toilet for slum {slum.id}: {e}', exc_info=True)
