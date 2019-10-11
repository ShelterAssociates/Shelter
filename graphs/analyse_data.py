from __future__ import division
from django.shortcuts import get_object_or_404
from graphs.models import *
from master.models import Slum
from component.models import *
from mastersheet.models import *
import json
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count



# json_file = json.loads(open('/home/shelter/Desktop/New_project/QOL_three/Shelter/graphs/json_reference_file.json').read())  # json reference data from json file

class RHSData(object):
    def __init__(self, slum):
        self.slum = get_object_or_404(Slum, pk=slum)
        self.household_data = HouseholdData.objects.filter(slum=self.slum)
        self.followup_data =FollowupData.objects.filter(slum=self.slum)
        self.slum_data = SlumData.objects.get(slum=self.slum)
        self.toilet_ms_data = ToiletConstruction.objects.filter(slum=self.slum)

    def occupied_houses(self):
        '''count of occupied houses in slums'''
        occupide_house_count = 0

        repeated_houses = self.household_data.values('household_number').annotate(Count('household_number')).order_by()\
            .filter(household_number__count__gte = 1).values_list('household_number', flat=True)

        for i in repeated_houses:
            if self.household_data.filter(household_number = int(i)):
                data = json.loads(self.household_data.values('rhs_data')[0].values()[0])
                if 'Type_of_structure_occupancy' in data.keys() and data['Type_of_structure_occupancy'] == 'Occupied house':
                    occupide_house_count +=1

        return occupide_house_count

    def ownership_status(self):
        owner_count = filter(lambda x: 'group_el9cl08/Ownership_status_of_the_house' in x.rhs_data and x.rhs_data[
            'group_el9cl08/Ownership_status_of_the_house'] == 'Own house', self.household_data)

        owner_percent =(len(owner_count)/self.occupied_houses())*100 if self.occupied_houses() !=0 else 0
        return owner_percent

    # def ctb_coverage(self):
    #     rhs_count = filter(lambda x: 'group_oi8ts04/Current_place_of_defecation' in x.followup_data and
    #                 (x.followup_data['group_oi8ts04/Current_place_of_defecation'].encode('ascii','ignore')) == '09',
    #                 self.followup_data)
    #
    #     ctb_coverage_in_slum = (len(rhs_count)/len(self.followup_data)) * 100 if len(self.followup_data) !=0 else 0
    #
    #     return ctb_coverage_in_slum
    # toilet data
    def individual_toilet_count(self):

        own_toilet_count = 0
        ctb_count = 0

        repeated_houses = self.followup_data.values('household_number').annotate(Count('household_number')).order_by().filter(
           household_number__count__gt = 1).values_list('household_number',flat=True)

        households_with_toilets_completed = self.toilet_ms_data.filter(status='6').values_list('household_number',flat=True)

        common_households = [value for value in repeated_houses if value in households_with_toilets_completed]

        for i in repeated_houses:
            latest_record = self.followup_data.filter(household_number=int(i)).values('followup_data').latest('submission_date')
            for j in latest_record.values():
                j =json.loads(j)
                if 'group_oi8ts04/Current_place_of_defecation' in j.keys() and (j['group_oi8ts04/Current_place_of_defecation'].encode('ascii','ignore')) == '09' :
                    ctb_count +=1
                if 'group_oi8ts04/Current_place_of_defecation' in j.keys() and int(j['group_oi8ts04/Current_place_of_defecation']) in [1,2,3,4,5,6,7]:
                    own_toilet_count += 1

        own_toilet_count = (own_toilet_count/self.occupied_houses())*100
        ctb_use_count = (ctb_count/self.occupied_houses())*100

        return (own_toilet_count,ctb_use_count,common_households)

    def toilet_constructed(self):
        '''total toilets faciliated by SA '''
        data = len(self.individual_toilet_count()[2])
        result = self.toilet_ms_data.filter(status='6').count()
        return result + data

    def get_toilet_data(self):
        household_population = self.occupied_houses() * 4
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
        toilet_to_per_ratio = household_population / total_fun_toilets if total_fun_toilets!=0 else 0
        men_to_wmn_seats_ratio = (fun_male_seats/fun_fmale_seats)*100 if fun_fmale_seats !=0 else 0

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
        kutcha_road_coverage_percent = (kutcha_road_coverage / total_coverage) *100 if total_coverage!=0 else 0
        pucca_road_coverage_percent =  (pucca_road_coverage / total_coverage) *100 if total_coverage!=0 else 0
        return (pucca_road_coverage_percent,kutcha_road_coverage_percent)

    def get_road_vehicle_facility(self):
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
        percent = (self.get_water_coverage(type) / self.occupied_houses()) * 100 if self.occupied_houses() !=0 else 0
        return percent

    # General Information data
    def get_household_members(self):
        household_member =filter(lambda x: 'group_el9cl08/Number_of_household_members' in x.rhs_data
                                            and int(x.rhs_data['group_el9cl08/Number_of_household_members']) < 20,
                                            self.household_data)
        return household_member

    def get_household_member_total(self):
       slum_population = sum(map(lambda x: int(x.rhs_data['group_el9cl08/Number_of_household_members']
                            if int(x.rhs_data['group_el9cl08/Number_of_household_members']) else 0) ,self.get_household_members()))
       return slum_population

    def get_household_member_size(self):
        avg_household_size = self.get_household_member_total() / len(self.get_household_members()) if len(self.get_household_members()) != 0 else 0
        return avg_household_size

    def get_slum_area_size(self):
        return int(self.slum_data.rim_data['General']['approximate_area_of_the_settle']) / 10000 \
            if 'approximate_area_of_the_settle' in self.slum_data.rim_data['General'] else 0

    def get_tenement_density(self):
        area_size = self.get_slum_area_size()
        return self.get_household_count() / area_size if area_size != 0 else 0

    def get_population_density(self):
        area_size = self.get_slum_area_size()
        return self.get_slum_population() / area_size if area_size != 0 else 0

    def get_sex_ratio(self):
        rhs_ff = self.household_data.values('ff_data')
        mem_count ={ 'males':[],'females':[]}
        for i in rhs_ff:
            for k,v in i.items():
                if v == None:
                    pass
                else:
                    for k1,v1 in (json.loads(v)).items():
                        if k1 == 'group_im2th52/Number_of_Male_members':
                            mem_count['males'].append(int(v1))
                        if k1 == 'group_im2th52/Number_of_Female_members':
                            mem_count['females'].append(int(v1))
        # female_male_ratio =(sum(mem_count['females'])/sum(mem_count['males'])) if sum(mem_count['males'])!= 0 else 0
        return mem_count