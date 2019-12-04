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
        wrk_fmale_seats = 0
        wrk_mix_seats = 0
        male_seats_not_in_use = 0
        fmale_seats_not_in_use=0
        mix_seats_not_in_use=0
        for i in toilet_data:
            wrk_male_seats += int(i['number_of_seats_allotted_to_me'] if 'number_of_seats_allotted_to_me' in i else 0)
            wrk_fmale_seats += int(i['number_of_seats_allotted_to_wo'] if 'number_of_seats_allotted_to_wo' in i else 0)
            wrk_mix_seats += int(i['total_number_of_mixed_seats_al'] if 'total_number_of_mixed_seats_al' in i else 0)
            # male_seats_not_in_use += int(i['number_of_seats_allotted_to_me_001'] if 'number_of_seats_allotted_to_me_001' in i else 0)
            # fmale_seats_not_in_use += int(i['number_of_seats_allotted_to_wo_001'] if 'number_of_seats_allotted_to_wo_001' in i else 0)
            # mix_seats_not_in_use += int(i['number_of_mixed_seats_allotted'] if 'number_of_mixed_seats_allotted' in i else 0)
            # fun_male_seats = wrk_male_seats - male_seats_not_in_use
            # fun_fmale_seats = wrk_fmale_seats- fmale_seats_not_in_use
            # fun_mix_seats = wrk_mix_seats -mix_seats_not_in_use
            # total_functional_toilets = fun_male_seats + fun_fmale_seats + fun_mix_seats  # these are seats in use n working
        total_toilet_seats = wrk_male_seats + wrk_fmale_seats + wrk_mix_seats #considered total seats
        return (total_toilet_seats, wrk_mix_seats, wrk_male_seats, wrk_fmale_seats)

    #road section
    def get_road_coverage(self):
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

    def get_shop_count(self):
        slum_type = ContentType.objects.get_for_model(Slum)
        get_shops_count_in_slum = len(Component.objects.filter(content_type=slum_type, object_id=self.slum.id,
                                                               metadata__name='Shops').values('shape'))
        return get_shops_count_in_slum

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

    def get_slum_area_size_in_hectors(self):
        return int(self.slum_data.rim_data['General']['approximate_area_of_the_settle']) / 10000 \
            if 'approximate_area_of_the_settle' in self.slum_data.rim_data['General'] else 0

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

    def key_takeaways_general(self):
        '''key take aways for general section'''
        general = self.slum_data.rim_data['General']
        land_owner = general['land_owner']
        land_status = general['legal_status']
        topography = general['topography']

        return (land_owner,land_status,topography)

    def key_takeaways_ctb(self,ctb):
        '''collecting each ctb data from slum where ctb in use'''
        if 'is_the_CTB_in_use' in ctb and ctb['is_the_CTB_in_use'] == 'Yes':
            electricity = ctb['availability_of_electricity_in_001'] if 'availability_of_electricity_in_001' in ctb else 0
            sewage_system = ctb['sewage_disposal_system'] if 'sewage_disposal_system' in ctb else 0
            ctb_available_at_night = ctb['is_the_ctb_available_at_night'] if 'is_the_ctb_available_at_night' in ctb else 0
            ctb_cleaning = ctb['cleanliness_of_the_ctb'] if 'cleanliness_of_the_ctb' in ctb else 0
            ctb_cleaning_freq = ctb['frequency_of_ctb_cleaning_by_U'] if 'frequency_of_ctb_cleaning_by_U' in ctb else 0
            water_in_ctb = ctb['availability_of_water_in_the_t'] if 'availability_of_water_in_the_t' in ctb else 0
            water_supply_type = ctb['type_of_water_supply_in_ctb'] if 'type_of_water_supply_in_ctb' in ctb else 0
            ctb_door = ctb['out_of_total_seats_no_of_doors_in_good_condition'] if 'out_of_total_seats_no_of_doors_in_good_condition' in ctb else 0
            ctb_condition = ctb['condition_of_ctb_structure'] if 'condition_of_ctb_structure' in ctb else 0
            ctb_seats_good_condtn = ctb['out_of_total_seats_no_of_pans_in_good_condition'] \
                if 'out_of_total_seats_no_of_pans_in_good_condition' in ctb else 0
            ctb_tank_capacity = ctb['capacity_of_ctb_water_tank_in'] if 'capacity_of_ctb_water_tank_in' in ctb else 0
            cost_per_use = ctb['cost_of_pay_and_use_toilet_pe'] if 'cost_of_pay_and_use_toilet_pe' in ctb else 0
            ctb_caretaker = ctb['is_there_a_caretaker_for_the_C'] if 'is_there_a_caretaker_for_the_C' in ctb else 0
            for_child = ctb['facility_in_the_toilet_block_f'] if 'facility_in_the_toilet_block_f' in ctb else 0
            ctb_cond_for_child = ctb['condition_of_facility_for_chil'] if 'condition_of_facility_for_chil' in ctb else 0

            return (electricity,sewage_system,ctb_available_at_night,ctb_cleaning,ctb_cleaning_freq,water_in_ctb,water_supply_type,
                    ctb_door,ctb_condition,ctb_seats_good_condtn,ctb_tank_capacity,cost_per_use,ctb_caretaker,for_child,ctb_cond_for_child)

    def key_takeaways_road(self):
        '''key take aways for road section'''
        road = self.slum_data.rim_data['Road']
        slum_level = road['is_the_settlement_below_or_abo'] if 'is_the_settlement_below_or_abo' in road else 0
        huts_level = road['are_the_huts_below_or_above_th'] if 'are_the_huts_below_or_above_th' in road else 0
        vehicular_access = road['point_of_vehicular_access_to_t'] if 'point_of_vehicular_access_to_t' in road else 0

        return (slum_level,huts_level,vehicular_access)

    def key_takeaways_water(self):
        '''key take aways for water section'''
        water = self.slum_data.rim_data['Water']
        water_availability = water['availability_of_water'] if 'availability_of_water' in water else 0
        water_quality = water['quality_of_water_in_the_system'] if 'quality_of_water_in_the_system' in water else 0
        water_coverage = water['coverage_of_wateracross_settle'] if 'coverage_of_wateracross_settle' in water else 0
        alternate_water_source = water['alternative_source_of_water'] if 'alternative_source_of_water' in water else 0

        return (water_availability,water_coverage,water_quality,alternate_water_source)

    def key_takeaways_drain_n_gutter(self):
        '''key take aways for drinage and gutter section'''
        drainage = self.slum_data.rim_data['Drainage']
        gutter = self.slum_data.rim_data['Gutter']
        drain_block = drainage['do_the_drains_get_blocked'] if 'do_the_drains_get_blocked' in drainage else 0
        drain_gradient = drainage['is_the_drainage_gradient_adequ'] if 'is_the_drainage_gradient_adequ' in drainage else 0
        gutter_flood = gutter['do_gutters_flood'] if 'do_gutters_flood' in gutter else 0
        gutter_gradient = gutter['is_gutter_gradient_adequate'] if 'is_gutter_gradient_adequate' in gutter else 0

        return (drain_block, drain_gradient, gutter_flood, gutter_gradient)

    def key_takeaways_waste(self):
        '''key take aways for waste section'''
        waste = self.slum_data.rim_data['Waste']
        dump_in_drains = waste['do_the_member_of_community_dep'] if 'do_the_member_of_community_dep' in waste else 0
        community_dump_site = waste['where_are_the_communty_open_du'] if 'where_are_the_communty_open_du' in waste else 0
        waste_containers = waste['total_number_of_waste_containe'] if 'total_number_of_waste_containe' in waste else 0
        waste_coll_by_mla_tempo = waste['coverage_of_waste_collection_a'] if 'coverage_of_waste_collection_a' in waste else 0
        waste_coll_door_to_door = waste['coverage_of_waste_collection_a_001'] if 'coverage_of_waste_collection_a_001' in waste else 0
        waste_coll_by_ghantagadi = waste['coverage_of_waste_collection_a_002'] if 'coverage_of_waste_collection_a_002' in waste else 0
        waste_coll_by_ulb_van = waste['coverage_of_waste_collection_a_003'] if 'coverage_of_waste_collection_a_003' in waste else 0
        waste_freq_by_ulb_van = waste['frequency_of_waste_collection_'] if 'frequency_of_waste_collection_' in waste else 0
        waste_freq_by_mla_tempo = waste['frequency_of_waste_collection'] if 'frequency_of_waste_collection' in waste else 0
        waste_freq_door_to_door = waste['frequency_of_waste_collection__002'] if 'frequency_of_waste_collection__002' in waste else 0
        waste_freq_by_ghantagadi = waste['frequency_of_waste_collection_001'] if 'frequency_of_waste_collection_001' in waste else 0
        waste_freq_bin = waste['frequency_of_waste_collection__001'] if 'frequency_of_waste_collection__001' in waste else 0

        return (dump_in_drains,community_dump_site,waste_containers,waste_coll_by_mla_tempo,waste_coll_door_to_door,
                waste_coll_by_ghantagadi,waste_coll_by_ulb_van,waste_freq_bin,waste_freq_by_ghantagadi,waste_freq_by_mla_tempo,
                waste_freq_by_ulb_van,waste_freq_door_to_door)