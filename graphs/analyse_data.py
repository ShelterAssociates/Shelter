from __future__ import division
from django.shortcuts import get_object_or_404
from graphs.models import *
from component.models import *
from mastersheet.models import *
import json
from django.contrib.contenttypes.models import ContentType

# json_file = json.loads(open('/home/shelter/Desktop/New_project/QOL_three/Shelter/graphs/json_reference_file.json').read())  # json reference data from json file

class RHSData(object):
    def __init__(self, slum):
        self.slum = get_object_or_404(Slum, pk=slum)
        self.household_data = HouseholdData.objects.filter(slum=self.slum)
        self.followup_data =FollowupData.objects.filter(slum=self.slum)
        self.slum_data = SlumData.objects.get(slum=self.slum)
        self.toilet_ms_data = ToiletConstruction.objects.filter(slum=self.slum)

    def get_unique_houses_rhs_householddata(self):
        unique_houses = self.household_data.distinct('household_number').values_list('household_number',flat=True)
        return unique_houses

    def occupied_houses(self):
        '''count of occupied houses in slums'''
        occupide_house_count = filter(lambda x: 'Type_of_structure_occupancy' in x.rhs_data and x.rhs_data[
                'Type_of_structure_occupancy'] == 'Occupied house', self.household_data)
        return len(occupide_house_count)

    def ownership_status(self):
        owner_count =filter(lambda x: 'group_el9cl08/Ownership_status_of_the_house' in x.rhs_data and x.rhs_data[
            'group_el9cl08/Ownership_status_of_the_house'] == 'Own house', self.household_data)
        return len(owner_count)

    #toilet section
    def toilet_constructed(self):
        '''total toilets faciliated by SA '''
        households_with_toilets_completed = self.toilet_ms_data.filter(status='6').values_list('household_number',flat=True)
        return households_with_toilets_completed

    def ctb_count(self):
        ctb_count = 0
        toilet_completed = self.toilet_constructed()
        for house in self.get_unique_houses_rhs_householddata():
            try:
                latest_record = self.followup_data.filter(household_number=house).latest('submission_date')
                if latest_record.household_number not in toilet_completed and \
                ('group_oi8ts04/Current_place_of_defecation' in latest_record.followup_data and \
                latest_record.followup_data['group_oi8ts04/Current_place_of_defecation'] == '09'):
                        ctb_count += 1
            except :pass
        return ctb_count

    def individual_toilet(self):
        own_toilet_count = 0
        for house in self.get_unique_houses_rhs_householddata():
            try:
                latest_record = self.followup_data.filter(household_number= house).latest('submission_date')
                if 'group_oi8ts04/Current_place_of_defecation' in latest_record.followup_data and \
                        int(latest_record.followup_data['group_oi8ts04/Current_place_of_defecation']) in [1,2,3,4,5,6,7]:
                        own_toilet_count += 1
            except : pass
        own_toilet_count = own_toilet_count+len(self.toilet_constructed())
        return own_toilet_count

    def get_toilet_data(self):
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
        # total_functional_toilets = fun_male_seats + fun_fmale_seats + fun_mix_seats  # these are seats in use n working
        total_toilet_seats = wrk_male_seats + wrk_fmale_seats + wrk_mix_seats #considered total seats
        # toilet_to_per_ratio = household_population / total_toilet_seats if total_toilet_seats!=0 else 0
        #men_to_wmn_seats_ratio = (fun_male_seats/fun_fmale_seats)*100 if fun_fmale_seats !=0 else 0

        return (total_toilet_seats, fun_mix_seats, fun_male_seats, fun_fmale_seats)

    #road section
    def get_road_coverage(self): #add total coverage col to dn and len of road to db at road_coverage column
        kutcha_road_area = 0
        pucca_road_area = 0

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
                kutcha_road_area += get_road_len(j)

        for i in ['Coba road','Tar road','Concrete road']:
            shape = Component.objects.filter(content_type=slum_type, object_id=self.slum.id, metadata__name=i).values('shape')
            for j in shape:
                pucca_road_area += get_road_len(j)

        total_road_area = kutcha_road_area + pucca_road_area
        return (kutcha_road_area,pucca_road_area,total_road_area)

    def get_road_vehicle_facility(self):
        no_vehicle_access = self.slum_data.rim_data['Road']['point_of_vehicular_access_to_t'] if 'point_of_vehicular_access_to_t' in \
                                                 self.slum_data.rim_data['Road'] else 0
        return (no_vehicle_access)

    def get_road_type(self):
        road_type = self.slum_data.rim_data['Road']['type_of_roads_within_the_settl'] if 'type_of_roads_within_the_settl' in \
                                                 self.slum_data.rim_data['Road'] else 0
        return road_type

    def get_household_count(self):
        return len(self.household_data)

    def get_slum_population(self):
        return self.get_household_count() * 4

    # Waste section data
    def get_waste_facility(self, facility):
        waste_facility_count = filter(lambda x: 'group_el9cl08/Facility_of_solid_waste_collection' in x.rhs_data and
                    x.rhs_data['group_el9cl08/Facility_of_solid_waste_collection'] == facility,self.household_data)
        return len(waste_facility_count)

    def get_perc_of_waste_collection(self, facility ='Door to door waste collection'):
        """
        facility ['Door to door waste collection', 'Open space', 'Garbage bin', 'ULB service']
        :param facility:
        :return:
        """
        percent = (self.get_waste_facility(facility) / self.get_household_count()) * 100 if self.get_household_count() !=0 else 0
        return (percent)

    # Water section data
    def get_water_coverage(self, type):
        water_facility_count = filter(lambda x: 'group_el9cl08/Type_of_water_connection' in x.rhs_data and x.rhs_data[
            'group_el9cl08/Type_of_water_connection'] == type, self.household_data)
        return len(water_facility_count)

    def get_perc_of_water_coverage(self, type='Individual connection'):
        """
        type = ['Individual connection', 'Shared connection','Water standpost', 'Hand pump', 'Water tanker','Well','From other settlements']
        :param type:
        :return:
        """
        percent = (self.get_water_coverage(type) / self.occupied_houses()) * 100 if  self.occupied_houses() !=0 else 0
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

    # def get_household_member_size(self):
    #     avg_household_size = self.get_household_member_total() / len(self.get_household_members()) if len(self.get_household_members()) != 0 else 0
    #     return avg_household_size

    def get_slum_area_size_in_hectors(self):
        return int(self.slum_data.rim_data['General']['approximate_area_of_the_settle']) / 10000 \
            if 'approximate_area_of_the_settle' in self.slum_data.rim_data['General'] else 0

    # def get_tenement_density(self):
    #     area_size = self.get_slum_area_size()
    #     return self.get_household_count() / area_size if area_size != 0 else 0
    #
    # def get_population_density(self):
    #     area_size = self.get_slum_area_size()
    #     return self.get_slum_population() / area_size if area_size != 0 else 0

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
