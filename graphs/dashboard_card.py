"""
Script to get aggregated data.
"""
from graphs.models import *
from analyse_data import *
from master.models import *

from django.http import HttpResponse
import json

class DashboardCard(RHSData):
    def __init__(self, slum):
        super(DashboardCard,self).__init__(slum)

    def General_Info(self):
        member_size = self.get_household_member_size()
        tenement_density = self.get_tenement_density()
        sex_ratio = self.get_sex_ratio()
        household_count = self.get_household_count()
        return (member_size, tenement_density,household_count)

    def save_general(self):
        """Save information to database"""
        (member_size, tenement_density,household_count) = self.General_Info()
        to_save = DashboardData.objects.update_or_create(slum = self.slum , defaults = {'tenement_density' : tenement_density,
                                    'member_size' : member_size, 'household_count':household_count,
                                    'city_id': self.slum.electoral_ward.administrative_ward.city.id})
                                    # 'houehold_member_count':0, # remove houehold_member_count from model as well

    def Waste_Info(self):
        door_to_door_percent = self.get_perc_of_waste_collection('Door to door waste collection')
        openspace_percent= self.get_perc_of_waste_collection('Open space')
        gutter_facility = self.get_perc_of_waste_collection('inside gutter')
        canal_facility = self.get_perc_of_waste_collection('along/inside canal')
        No_facility_percent = (openspace_percent+gutter_facility+canal_facility)/3
        return (door_to_door_percent, No_facility_percent,openspace_percent)

    def save_waste(self):
        (door_to_door_percent, No_facility_percent,openspace_percent) = self.Waste_Info()
        to_save = DashboardData.objects.update_or_create(slum =self.slum, defaults={'no_facility_per': No_facility_percent,
                                'door_to_door_percent': door_to_door_percent,
                                'openspace_percent': openspace_percent })

def dashboard_data_Save(city):
    slums = Slum.objects.filter(electoral_ward__administrative_ward__city__id__in = [city])
    for slum in slums:
        try:
            dashboard_data = DashboardCard(slum.id)
            dashboard_data.save_general()
            dashboard_data.save_waste()
        except Exception as e:
            print 'Exception in dashboard_sata_save',(e)

dashboard_data_Save(4)