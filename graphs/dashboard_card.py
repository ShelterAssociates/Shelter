"""
Script to get aggregated data.
"""
from graphs.models import *
from analyse_data import *
from master.models import *

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
        (household_owners_count, avg_household_size, slum_area_size_in_hectors, household_count) = self.General_Info()
        # print type(occupied_household_count), type(get_slum_area_size_in_hectors)
        # print type(household_count), type(household_owners_count),type(avg_household_size),type(slum_area_size_in_hectors)
        to_save = DashboardData.objects.update_or_create(slum = self.slum , defaults ={'city_id': self.slum.electoral_ward.administrative_ward.city.id,
                    'gen_tenement_density' : get_slum_area_size_in_hectors,'gen_avg_household_size': avg_household_size,
                    'total_household_count':household_count,'household_owners_count':household_owners_count,
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

    # def save_qol_scores(self):
    #     scores = self.get_scores()

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
        except Exception as e:
            print 'Exception in dashboard_data_save',(e)
