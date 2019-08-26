"""
Script to get aggregated data.
"""
from graphs.models import *
from analyse_data import *
from master.models import *
class DashboardData(RHSData):
    def __init__(self, slum):
        super(DashboardData).__init__(self, slum)

    def General_Info(self):
        member_size = self.get_household_member_size()
        tenement_density = self.get_tenement_density()
        sex_ratio = self.get_sex_ratio()
        return (member_size, tenement_density, sex_ratio)

    def save_general(self):
        """Save information to database"""
        (member_size, tenement_density, sex_ratio) = self.General_Info()


def dashboard_data_Save(city):
    slums = Slum.objects.filter(electoral_ward__administrative_ward__city__id__in = [city])
    for slum in slums:
        try:
            dashboard_data = DashboardData(slum.id)
            dashboard_data.save_general()
        except Exception as e:
            print(e)

dashboard_data_Save(4)
