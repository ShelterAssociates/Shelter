from __future__ import division
from django.shortcuts import get_object_or_404
from graphs.models import *
from master.models import Slum
from component.models import *
from mastersheet.models import *
import json
from django.contrib.contenttypes.models import ContentType

json_data = json.loads(open('graphs/reference_file.json').read())  # json reference data from json file

class RHSData(object):
    def __init__(self, slum):
        self.slum = get_object_or_404(Slum, pk=slum)
        self.household_data = HouseholdData.objects.filter(slum=self.slum)
        self.followup_data = FollowupData.objects.filter(slum=self.slum)
        self.slum_data = SlumData.objects.get(slum=self.slum)
        self.toilet_ms_data = ToiletConstruction.objects.filter(slum=self.slum)

    def occupide_houses(self):
        '''count of occupied houses in slums'''
        count = filter(lambda x:'Type_of_structure_occupancy' in x.rhs_data and x.rhs_data[
                    'Type_of_structure_occupancy'] == 'Occupied house',self.household_data)
        return len(count)

    def get_scores(self):
        drain =self.get_drain_gutter_score()
        return 0

    def get_drain_gutter_score(self):
        score = 0
        drain = self.slum_data.rim_data['Drainage']
        gutter =self.slum_data.rim_data['Gutter']

        return score

    #toilet data
    def get_toilet_data(self):
        household_count = self.occupide_houses() * 4
        # toilet_status = self.get_toilet_status()
        toilet_data = self.slum_data.rim_data['Toilet']
        wrk_male_seats = 0
        wrk_nt_male_seats = 0
        wrk_fmale_seats=0
        wrk_nt_fmale_seats=0
        wrk_mix_seats=0
        wrk_nt_mix_seats=0
        for i in toilet_data:
            wrk_male_seats += int(i['number_of_seats_allotted_to_me'] if 'number_of_seats_allotted_to_me' in i else 0)
            wrk_nt_male_seats += int(i['number_of_seats_allotted_to_me_001'] if 'number_of_seats_allotted_to_me_001' in i else 0)
            wrk_fmale_seats += int(i['number_of_seats_allotted_to_wo'] if 'number_of_seats_allotted_to_wo' in i else 0)
            wrk_nt_fmale_seats += int(i['number_of_seats_allotted_to_wo_001'] if 'number_of_seats_allotted_to_wo_001' in i else 0)
            wrk_mix_seats += int(i['total_number_of_mixed_seats_al'] if 'total_number_of_mixed_seats_al' in i else 0)
            wrk_nt_mix_seats += int(i['number_of_mixed_seats_allotted'] if 'number_of_mixed_seats_allotted' in i else 0)

        fun_male_seats = wrk_male_seats - wrk_nt_male_seats
        fun_fmale_seats = wrk_fmale_seats- wrk_nt_fmale_seats
        fun_mix_seats = wrk_mix_seats -wrk_nt_mix_seats

        total_fun_toilets = fun_male_seats + fun_fmale_seats + fun_mix_seats
        toilet_to_per_ratio = household_count / total_fun_toilets if total_fun_toilets!=0 else 0
        men_to_wmn_seats_ratio = fun_male_seats/fun_fmale_seats if fun_fmale_seats !=0 else 0

        return (toilet_to_per_ratio, men_to_wmn_seats_ratio)

    def get_road_coverage(self):
        kutcha_road_coverage = 0
        pucca_road_coverage = 0

        def get_road_len(linestring):
            # converts the road length into meters
            line = linestring['shape']
            line.srid = 4326
            line.transform(3857)
            len_in_meter = line.length
            return len_in_meter

        slum_type = ContentType.objects.get_for_model(Slum)
        for i in ['Kutcha road','Paving block','Farashi']:
            shape = Component.objects.filter(content_type=slum_type, object_id=self.slum.id, metadata__name=i).values('shape')
            for j in shape:
                kutcha_road_coverage += get_road_len(j)

        for i in ['Coba road','Tar road','Concrete road']:
            shape = Component.objects.filter(content_type=slum_type, object_id=self.slum.id, metadata__name=i).values('shape')
            for j in shape:
                pucca_road_coverage += get_road_len(j)

        total_coverage = kutcha_road_coverage + pucca_road_coverage
        kutcha_road_coverage_percent = (kutcha_road_coverage / total_coverage) *100
        pucca_road_coverage_percent =  (pucca_road_coverage / total_coverage) *100
        return (pucca_road_coverage_percent,kutcha_road_coverage_percent)

    def get_road_vehicle_facility(self):
        a =self.get_road_coverage()
        no_vehicle_access = self.slum_data.rim_data['Road']['point_of_vehicular_access_to_t'] if 'point_of_vehicular_access_to_t' in \
                                                 self.slum_data.rim_data['Road'] else 0
        return (no_vehicle_access)

    def get_road_type(self):
        road_type = self.slum_data.rim_data['Road']['type_of_roads_within_the_settl'] if 'type_of_roads_within_the_settl' in \
                                                 self.slum_data.rim_data['Road'] else 0
        return road_type

    def get_household_count(self):
        return self.household_data.count()

    def get_slum_population(self):
        # group_el9cl08 / Number_of_household_members (col in rhs data for household member count)
        return self.get_household_count() * 4

    def get_waste_facility(self, facility):
        waste_facility = filter(lambda x: 'group_el9cl08/Facility_of_solid_waste_collection' in x.rhs_data
                        and x.rhs_data['group_el9cl08/Facility_of_solid_waste_collection'] == facility,self.household_data)
        return len(waste_facility)

    def get_water_coverage(self, type):
        water_coverage = filter(
            lambda x: 'group_el9cl08/Type_of_water_connection' in x.rhs_data and x.rhs_data[
                'group_el9cl08/Type_of_water_connection'] == type, self.household_data)
        return len(water_coverage)

    #Waste data
    def get_perc_of_waste_collection(self, facility ='Door to door waste collection'):
        """
        facility ['Door to door waste collection', 'Open space', 'Garbage bin', 'ULB service']
        :param facility:
        :return:
        """
        percent = (self.get_waste_facility(facility) / self.get_household_count()) * 100 if self.get_household_count() !=0 else 0
        return (percent)

    #Water data
    def get_perc_of_water_coverage(self, type='Individual connection'):
        """
        type = ['Individual connection', 'Shared connection','Water standpost', 'Hand pump', 'Water tanker','Well','From other settlements']
        :param type:
        :return:
        """
        percent = (self.get_water_coverage(type) / self.get_household_count()) * 100 if self.get_household_count() !=0 else 0
        return percent

    # General Information data
    def get_household_member_size(self):
        household_member = filter(lambda x: 'group_el9cl08/Number_of_household_members' in x.rhs_data
                                    and int(x.rhs_data['group_el9cl08/Number_of_household_members']) < 20,
                                  self.household_data)
        return sum(map(lambda x: int(x.rhs_data['group_el9cl08/Number_of_household_members']), household_member)) \
               / len(household_member) if len(household_member) != 0 else 0

    def get_slum_area_size(self):
        return int(self.slum_data.rim_data['General']['approximate_area_of_the_settle']) / 1000 \
            if 'approximate_area_of_the_settle' in self.slum_data.rim_data['General'] else 0

    def get_tenement_density(self):
        area_size = self.get_slum_area_size()
        return self.get_slum_population() / area_size if area_size != 0 else 0

    def get_sex_ratio(self):
        return 0