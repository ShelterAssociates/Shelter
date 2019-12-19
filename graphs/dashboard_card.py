"""
Script to get aggregated data.
"""
from graphs.models import *
from analyse_data import *
from master.models import *
from django.http import HttpResponse

class DashboardCard(RHSData):
    def __init__(self, slum):
        super(DashboardCard,self).__init__(slum)

    def dashboard_page_parameters(self):
        population = self.get_household_member_total()
        toilet_count = len(self.toilet_constructed())
        people_impacted = toilet_count * 5
        to_save = DashboardData.objects.update_or_create(slum=self.slum,
                defaults={'count_of_toilets_completed': toilet_count,'people_impacted':people_impacted,
                          'slum_population':population})

    def General_Info(self):
        avg_household_size = self.get_household_member_total()
        slum_area_size_in_hectors = self.get_slum_area_size_in_hectors()
        household_owners_count = self.ownership_status()
        household_count = self.get_household_count()
        return (household_owners_count,avg_household_size, slum_area_size_in_hectors,household_count)

    def save_general(self):
        """Save information to database"""
        occupied_household_count = self.occupied_houses()
        get_slum_area_size_in_hectors = self.get_slum_area_size_in_hectors()
        shops_in_slum = self.get_shop_count()
        (household_owners_count, avg_household_size, slum_area_size_in_hectors, household_count) = self.General_Info()
        to_save = DashboardData.objects.update_or_create(slum = self.slum , defaults ={'city_id': self.slum.electoral_ward.administrative_ward.city.id,
                    'gen_tenement_density' : get_slum_area_size_in_hectors,'get_shops_count':shops_in_slum,'gen_avg_household_size': avg_household_size,
                    'household_count':household_count,'household_owners_count':household_owners_count,
                    'occupied_household_count':occupied_household_count})

    def Waste_Info(self):
        door_to_door_percent = self.get_waste_facility('Door to door waste collection')
        openspace_percent= self.get_waste_facility('Open space')
        # gutter_facility = self.get_perc_of_waste_collection('inside gutter')
        # canal_facility = self.get_perc_of_waste_collection('along/inside canal')
        garbage_bin_facility = self.get_waste_facility('Garbage bin')
        return (door_to_door_percent,garbage_bin_facility,openspace_percent)

    def save_waste(self):
        (door_to_door_percent,garbage_bin_facility,openspace_percent)= self.Waste_Info()
        to_save = DashboardData.objects.update_or_create(slum =self.slum, defaults=
                                {'waste_door_to_door_collection_facility_percentile': door_to_door_percent,
            'waste_dump_in_open_percent': openspace_percent,'waste_no_collection_facility_percentile': garbage_bin_facility})

    def Water_Info(self):
        individual_connection_percent = self.get_water_coverage('Individual connection')
        shared_connection_percent = self.get_water_coverage('Shared connection')
        water_standpost_percent = self.get_water_coverage('Water standpost')
        return (individual_connection_percent,shared_connection_percent,water_standpost_percent)

    def save_water(self):
        (individual_connection_percent,shared_connection_percent,water_standpost_percent) = self.Water_Info()
        to_save = DashboardData.objects.update_or_create(slum =self.slum,
            defaults={'water_individual_connection_percentile':individual_connection_percent,
            'water_shared_service_percentile':shared_connection_percent,'waterstandpost_percentile':water_standpost_percent})

    def Road_Info(self):
        pucca = 1 if self.get_road_type() == 'Pucca' else 0
        kutcha = 1 if self.get_road_type() == 'Kutcha' else 0
        no_vehicle = 1 if self.get_road_vehicle_facility() =='None' else 0
        (kutcha_road_area,pucca_road_area,total_road_area) = self.get_road_coverage()
        return (pucca,kutcha,no_vehicle,pucca_road_area,kutcha_road_area,total_road_area)

    def save_road(self):
        (pucca,kutcha,no_vehicle,pucca_road_area,kutcha_road_area,total_road_area)= self.Road_Info()
        to_save = DashboardData.objects.update_or_create( slum = self.slum, defaults =
                                {'road_with_no_vehicle_access': no_vehicle,'pucca_road' : pucca,
                                 'kutcha_road':kutcha,'pucca_road_coverage':pucca_road_area,
                                 'kutcha_road_coverage':kutcha_road_area,'total_road_area':total_road_area})

    def save_toilet(self):
        own_toilet_count = self.individual_toilet()
        ctb_use_count = self.ctb_count()
        (total_toilet_seats, fun_mix_seats, fun_male_seats, fun_female_seats) = self.get_toilet_data()
        to_save = DashboardData.objects.update_or_create(slum=self.slum, defaults= {'individual_toilet_coverage':own_toilet_count,
                                 'ctb_coverage':ctb_use_count,'toilet_men_women_seats_ratio': fun_mix_seats, 'fun_male_seats':fun_male_seats,
                                'toilet_seat_to_person_ratio': total_toilet_seats, 'fun_fmale_seats':fun_female_seats })

    def save_rim_gen(self):
       (land_owner,land_status,topography) = self.key_takeaways_general()
       to_save = SlumDataSplit.objects.update_or_create(slum = self.slum, city_id = self.slum.electoral_ward.administrative_ward.city.id,
                defaults = {'land_status':land_status,'land_ownership':land_owner,'land_topography':topography})

    def save_rim_water(self):
        (water_availability, water_coverage, water_quality, alternate_water_source) = self.key_takeaways_water()
        to_save = SlumDataSplit.objects.update_or_create(slum=self.slum,city_id=self.slum.electoral_ward.administrative_ward.city.id,
         defaults={'availability_of_water': water_availability,'coverage_of_water':water_coverage,
                   'quality_of_water':water_quality, 'alternative_source_of_water': alternate_water_source})

    def save_rim_waste(self):
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
       (drain_block, drain_gradient, gutter_flood, gutter_gradient) = self.key_takeaways_drain_n_gutter()
       to_save = SlumDataSplit.objects.update_or_create(slum = self.slum, city_id = self.slum.electoral_ward.administrative_ward.city.id,
                defaults = {'do_the_drains_get_blocked':drain_block,'is_the_drainage_gradient_adequ':drain_gradient,
                            'do_gutters_flood':gutter_flood, 'is_gutter_gradient_adequate':gutter_gradient})

    def save_rim_road(self):
       (slum_level, huts_level, vehicular_access) = self.key_takeaways_road()
       to_save = SlumDataSplit.objects.update_or_create(slum = self.slum, city = self.slum.electoral_ward.administrative_ward.city.id,
                defaults = {'is_the_settlement_below_or_above':slum_level,'are_the_huts_below_or_above':huts_level,
                            'point_of_vehicular_access':vehicular_access})

    def call_rim_ctb(self):
        ctb = self.slum_data.rim_data['Toilet']
        ctb_no = 0
        for i in ctb:
            ctb_no += 1
            self.save_rim_toilet(i,ctb_no)

    def save_rim_toilet(self,one_ctb,ctb_count):
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
    slums = Slum.objects.filter(electoral_ward__administrative_ward__city__id__in = [city])

    for slum in slums:
        try:
            dashboard_data = DashboardCard(slum.id)
            # dashboard_data.save_qol_scores()
            dashboard_data.save_general()
            dashboard_data.dashboard_page_parameters()
            dashboard_data.save_waste()
            dashboard_data.save_water()
            dashboard_data.save_road()
            dashboard_data.save_toilet()
            # dashboard_data.save_rim_drainGutter()
            # dashboard_data.save_rim_road()
            # dashboard_data.save_rim_waste()
            # dashboard_data.save_rim_water()
            # dashboard_data.save_rim_gen()
            # dashboard_data.call_rim_ctb()
        except Exception as e:
            print 'Exception in dashboard_data_save',(e)
