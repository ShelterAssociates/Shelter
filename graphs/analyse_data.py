from django.shortcuts import get_object_or_404
from graphs.models import *
from master.models import Slum

class RHSData:
    def __init__(self, slum):
        self.slum = get_object_or_404(Slum, pk=slum)
        self.household_data = HouseholdData.objects.filter(slum=self.slum)
        self.slum_data = SlumData.objects.get(slum=self.slum)

    def get_household_count(self):
        return self.household_data.count()

    def get_slum_population(self):
        return self.get_household_count() * 4

    def get_waste_facility(self, facility):
        waste_facility = filter(lambda x: 'group_el9cl08/Facility_of_solid_waste_collection' in x.rhs_data and x.rhs_data['group_el9cl08/Facility_of_solid_waste_collection'] == facility,self.household_data)
        return len(waste_facility)

    def get_water_coverage(self, type):
        water_coverage = filter(
            lambda x: 'group_el9cl08/Type_of_water_connection' in x.rhs_data and x.rhs_data[
                'group_el9cl08/Type_of_water_connection'] == type, self.household_data)
        return len(water_coverage)

    #General Information data
    def get_household_member_size(self):
        household_member = filter(lambda x:'group_el9cl08/Number_of_household_members' in x.rhs_data and int(x.rhs_data['group_el9cl08/Number_of_household_members'])<20, self.household_data)
        return sum(map(lambda x:int(x.rhs_data['group_el9cl08/Number_of_household_members']), household_member)) / len(household_member)

    def get_slum_area_size(self):
        return int(self.slum_data.rim_data['group_zl6oo94/group_wb1hp47/approximate_area_of_the_settle'])/1000 if 'group_zl6oo94/group_wb1hp47/approximate_area_of_the_settle' in self.slum_data.rim_data else 0

    def get_tenement_density(self):
        area_size = self.get_slum_area_size()
        return self.get_slum_population() / area_size if area_size!=0 else 0

    def get_sex_ratio(self):
        return 0

    #Waste data
    def get_perc_of_waste_collection(self, facility='Door to door waste collection'):
        """
        facility ['Door to door waste collection', 'Open space', 'Garbage bin', 'ULB service']
        :param facility:
        :return:
        """
        return (self.get_waste_facility(facility) / self.get_household_count()) * 100

    #Water data
    def get_perc_of_water_coverage(self, type='Individual connection'):
        """
        type = ['Individual connection', 'Shared connection','Water standpost', 'Hand pump', 'Water tanker','Well','From other settlements']
        :param type:
        :return:
        """
        return (self.get_water_coverage(type) / self.get_household_count()) * 100