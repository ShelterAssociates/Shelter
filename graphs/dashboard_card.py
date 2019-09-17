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

    def General_Info(self):
        avg_household_size = self.get_household_member_size()
        tenement_density = self.get_tenement_density()
        # sex_ratio = self.get_sex_ratio()
        household_count = self.get_household_count()
        return (avg_household_size, tenement_density,household_count)

    def get_general_score(self):
        # qol_score = qol_score_save() # get rim data and
        pass

    def save_general(self):
        """Save information to database"""
        (avg_household_size, tenement_density,household_count) = self.General_Info()
        to_save = DashboardData.objects.update_or_create(slum = self.slum , defaults = {'gen_tenement_density' : tenement_density,
                                    'gen_avg_household_size': avg_household_size , 'household_count':household_count,
                                    'city_id': self.slum.electoral_ward.administrative_ward.city.id})
                                    # 'gen_sex_ration':sex_ratio, 'gen_odf_status' : gen_ofd

    def Waste_Info(self):
        door_to_door_percent = self.get_perc_of_waste_collection('Door to door waste collection')
        openspace_percent= self.get_perc_of_waste_collection('Open space')
        gutter_facility = self.get_perc_of_waste_collection('inside gutter')
        canal_facility = self.get_perc_of_waste_collection('along/inside canal')
        waste_no_collection_facility_percentile = (openspace_percent+gutter_facility+canal_facility)/3
        return (door_to_door_percent, waste_no_collection_facility_percentile,openspace_percent)

    def save_waste(self):
        (door_to_door_percent, waste_no_collection_facility_percentile,openspace_percent) = self.Waste_Info()
        to_save = DashboardData.objects.update_or_create(slum =self.slum, defaults=
                                {'waste_no_collection_facility_percentile': waste_no_collection_facility_percentile,
                                'waste_door_to_door_collection_facility_percentile': door_to_door_percent,
                                'waste_dump_in_open_percent': openspace_percent })

    def Water_Info(self):
        individual_connection_percent = self.get_perc_of_water_coverage('Individual connection')
        # no_connection_percent = self.get_perc_of_water_coverage('')
        return (individual_connection_percent)

    def save_water(self):
        (individual_connection_percent) = self.Water_Info()
        to_save = DashboardData.objects.update_or_create(slum =self.slum,
                                defaults={'water_individual_connection_percentile':individual_connection_percent})
                                          #'water_no_service_percentile':no_connection_percent})

    def Road_Info(self):
        pucca = 1 if self.get_road_type() == 'Pucca' else 0
        kutcha = 1 if self.get_road_type() == 'Kutcha' else 0
        no_vehicle = 1 if self.get_road_vehicle_facility() =='None' else 0
        pucca_road_coverage, kutcha_road_coverage = self.get_road_coverage()
        return (pucca,kutcha,no_vehicle,pucca_road_coverage,kutcha_road_coverage)

    def save_road(self):
        (pucca,kutcha,no_vehicle,pucca_road_coverage,kutcha_road_coverage) = self.Road_Info()
        to_save = DashboardData.objects.update_or_create( slum = self.slum, defaults =
                                {'road_with_no_vehicle_access': no_vehicle,'pucca_road' : pucca,
                                 'kutcha_road':kutcha,'pucca_road_coverage':pucca_road_coverage,
                                 'kutcha_road_coverage':kutcha_road_coverage })

    def save_toilet(self):
        (toilet_to_per_ratio, men_to_wmn_seats_ratio) = self.get_toilet_data()
        to_save = DashboardData.objects.update_or_create(slum=self.slum, defaults=
                                {'toilet_men_women_seats_ratio': men_to_wmn_seats_ratio,
                                 'toilet_seat_to_person_ratio': toilet_to_per_ratio })

    def save_qol_scores(self):
        scores = self.get_scores()

def dashboard_data_Save(city):
    slums = Slum.objects.filter(electoral_ward__administrative_ward__city__id__in = [city])
    for slum in slums:
        try:
            dashboard_data = DashboardCard(slum.id)
            # dashboard_data.save_qol_scores()
            dashboard_data.save_general()
            dashboard_data.save_waste()
            dashboard_data.save_water()
            dashboard_data.save_road()
            dashboard_data.save_toilet()
        except Exception as e:
            print 'Exception in dashboard_data_save',(e)

def trial(request):
    dashboard_data_Save(3)
    return HttpResponse(json.dumps('dashboard'))