from __future__ import division
from django.shortcuts import get_object_or_404
from graphs.models import *
from component.models import *
from mastersheet.models import *
import json
from django.contrib.contenttypes.models import ContentType
from component.views import slum_list

# json_file = json.loads(open('/home/shelter/Desktop/New_project/QOL_three/Shelter/graphs/json_reference_file.json').read())  # json reference data from json file

# The RHSData class retrieves and stores various data related to a specific slum.
class RHSData(object):
    def __init__(self, slum):
        self.slum = get_object_or_404(Slum, pk=slum)
        self.household_data = HouseholdData.objects.filter(slum=self.slum)
        self.followup_data =FollowupData.objects.filter(slum=self.slum)
        self.slum_data = SlumData.objects.get(slum=self.slum)
        self.toilet_ms_data = ToiletConstruction.objects.filter(slum=self.slum)
        self.hh_have_toilet_enc = self.toilet_data_available()
        self.hh_have_water_enc = self.water_data_available()
        self.hh_have_waste_enc = self.waste_data_available()
        
    def toilet_data_available(self):
        hh_toilet_data_available = []
        '''count of occupied houses in slums'''
        sanitation_hhs = filter(lambda x: x.rhs_data and 'Type_of_structure_occupancy' in x.rhs_data and 'group_oi8ts04/Current_place_of_defecation' in x.rhs_data, self.household_data)
        hh_toilet_data_available = [i.household_number for i in sanitation_hhs]
        # occupied houses ...
        occupied_houses = self.occupied_houses()
        # Also adding followup_households ...
        followup_hhs = self.followup_data.filter(household_number__in = occupied_houses).values_list('household_number', flat = True)
        hh_toilet_data_available.extend(list(followup_hhs))
        # Also adding household where SA toilet available ...
        SA_toilet_constructed = self.toilet_constructed()
        hh_toilet_data_available.extend(list(SA_toilet_constructed))
        return list(set(hh_toilet_data_available))
    
    def water_data_available(self):
        hh_water_data_available = []
        '''count of occupied houses in slums'''
        water_hhs = filter(lambda x: x.rhs_data and 'Type_of_structure_occupancy' in x.rhs_data and 'group_el9cl08/Type_of_water_connection' in x.rhs_data, self.household_data)
        hh_water_data_available = [i.household_number for i in water_hhs]
        return list(set(hh_water_data_available))
    
    def waste_data_available(self):
        hh_waste_data_available = []
        '''count of occupied houses in slums'''
        waste_hhs = filter(lambda x: x.rhs_data and 'Type_of_structure_occupancy' in x.rhs_data and 'group_el9cl08/Facility_of_solid_waste_collection' in x.rhs_data, self.household_data)
        hh_waste_data_available = [i.household_number for i in waste_hhs]
        return list(set(hh_waste_data_available))

    def get_unique_houses_rhs_householddata(self):
        """
        The function `get_unique_houses_rhs_householddata` returns a list of unique household numbers from
        the `household_data` collection.
        :return: a list of unique household numbers from the household_data.
        """
        unique_houses = self.household_data.distinct('household_number').values_list('household_number',flat=True)
        return unique_houses

    def occupied_houses(self):
        """
        The function "occupied_houses" returns a list of occupied households in slums by filtering the
        household data based on the "Type_of_structure_occupancy" field and checking with the toilet data.
        :return: a list of occupied households in the slums.
        """
        '''count of occupied houses in slums'''
        occupied_hhs = filter(lambda x: x.rhs_data and 'Type_of_structure_occupancy' in x.rhs_data and x.rhs_data[
                'Type_of_structure_occupancy'] == 'Occupied house', self.household_data)
        occupied_hhs = [i.household_number for i in occupied_hhs]
        # Check with toilet data ...
        toilet_hhs = list(self.toilet_constructed())
        # Extend Occupied households 
        occupied_hhs.extend(toilet_hhs)
        return list(set(occupied_hhs))
    
    def structure_data(self):
        """
        The function `structure_data` counts the number of occupied houses in different types of structures
        (kutcha, pucca, semi-pucca) based on the data in `self.household_data`.
        :return: The code is returning the values of the dictionary `final_slumwise_strc_data`.
        """
        final_slumwise_strc_data = {'Kutcha': 0, 'Pucca': 0, 'Semi-pucca': 0}
        for obj in self.household_data:
            if obj.rhs_data and 'Type_of_structure_occupancy' in obj.rhs_data and obj.rhs_data['Type_of_structure_occupancy'] == 'Occupied house':
                rhs = obj.rhs_data
                if 'group_el9cl08/Type_of_structure_of_the_house' in rhs:
                    struc_type = rhs['group_el9cl08/Type_of_structure_of_the_house']
                    if struc_type in final_slumwise_strc_data:
                        final_slumwise_strc_data[struc_type] += 1
        return final_slumwise_strc_data.values()

    def ownership_status(self):
        """
        The function `ownership_status` counts the number of households that own their house based on a
        specific condition in the `household_data` list.
        :return: the count of households where the ownership status of the house is 'Own house'.
        """
        owner_count =filter(lambda x: x.rhs_data and 'group_el9cl08/Ownership_status_of_the_house' in x.rhs_data and x.rhs_data[
            'group_el9cl08/Ownership_status_of_the_house'] == 'Own house', self.household_data)
        return len(list(owner_count))

    #toilet section
    def toilet_constructed(self):
        """
        The function `toilet_constructed` returns a list of household numbers for households that have
        completed the construction of toilets.
        :return: a queryset of household numbers for households that have completed the construction of
        toilets.
        """
        '''total toilets faciliated by SA '''
        households_with_toilets_completed = self.toilet_ms_data.filter(status='6').values_list('household_number',flat=True)
        return households_with_toilets_completed

    def ctb_count(self):
        """
        The `ctb_count` function counts the number of households that use a Community Toilet Block (CTB) as
        their current place of defecation.
        :return: the count of households where the latest record indicates that the household uses a CTB
        (Community Toilet Block) for defecation.
        """
        ctb_count = 0
        toilet_completed = self.toilet_constructed()
        for house in self.hh_have_toilet_enc:
            try:
                latest_record = self.followup_data.filter(household_number=house).latest('submission_date')
                if latest_record.household_number not in toilet_completed and \
                ('group_oi8ts04/Current_place_of_defecation' in latest_record.followup_data and \
                latest_record.followup_data['group_oi8ts04/Current_place_of_defecation'] == 'Use CTB'):
                        ctb_count += 1
            except : pass
        return ctb_count
    
    def shared_group_toilet_cnt(self):
        """
        The `ctb_count` function counts the number of households that use a Community Toilet Block (CTB) as
        their current place of defecation.
        :return: the count of households where the latest record indicates that the household uses a CTB
        (Community Toilet Block) for defecation.
        """
        toilet_cnt = 0
        toilet_completed = self.toilet_constructed()
        options = ['Shared toilet', 'Group toilet']
        for house in self.hh_have_toilet_enc:
            try:
                latest_record = self.followup_data.filter(household_number=house).latest('submission_date')
                if latest_record.household_number not in toilet_completed and \
                ('group_oi8ts04/Current_place_of_defecation' in latest_record.followup_data and \
                latest_record.followup_data['group_oi8ts04/Current_place_of_defecation']  in options):
                        toilet_cnt += 1
            except : pass
        return toilet_cnt

    def individual_toilet(self):
        """
        The function `individual_toilet` calculates the count of households with own toilets by checking
        the latest follow-up data for each household and counting those that have a toilet constructed
        or have specified a toilet by other means.
        :return: the count of own toilets, which includes both the number of toilets that have been
        completed and the number of households that have reported having their own toilets in the latest
        follow-up data.
        """
        toilet_by_other = ['SBM (Installment)','SBM (Contractor)','Toilet by SA (SBM)','Toilet by other NGO (SBM)','Own toilet','Toilet by other NGO']
        # toilet_by_other = [1,2,3,4,5,6,7]
        
        toilet_completed = self.toilet_constructed()
        own_toilet_count = 0
        for house in self.hh_have_toilet_enc:
            try:
                latest_record = self.followup_data.filter(household_number= house).latest('submission_date')
                if latest_record.household_number not in toilet_completed  and 'group_oi8ts04/Current_place_of_defecation' in latest_record.followup_data and \
                        (latest_record.followup_data['group_oi8ts04/Current_place_of_defecation']) in toilet_by_other:
                        own_toilet_count += 1
            except : pass

        own_toilet_count = own_toilet_count+len(toilet_completed)
        return own_toilet_count

    def get_toilet_data(self):
        """
        The function `get_toilet_data` retrieves data about toilets from a slum dataset and returns the
        total number of toilet seats, the number of mixed gender seats, the number of male seats, and
        the number of female seats.
        :return: a tuple containing the total number of toilet seats, the number of mixed gender seats,
        the number of male seats, and the number of female seats.
        """
        
        if 'Toilet' in self.slum_data.rim_data and len(self.slum_data.rim_data['Toilet']) > 0:
            toilet_data = self.slum_data.rim_data['Toilet']
        else:
            return (0, 0, 0, 0)

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
        """
        The function calculates the total length of kutcha and pucca roads in a slum area and returns
        the individual lengths as well as the total length.
        :return: a tuple containing the kutcha road area, pucca road area, and total road area.
        """
        kutcha_road_area = 0
        pucca_road_area = 0

        def get_road_len(linestring):
            """
            The function `get_road_len` takes a linestring object and returns the length of the road in
            meters.
            
            :param linestring: The `linestring` parameter is a dictionary that contains a key called
            'shape', which represents a line geometry. This line geometry represents a road
            :return: the length of the road in meters.
            """
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
        """
        The function returns the number of vehicle access points to a road in a slum area.
        :return: the value of the variable "no_vehicle_access".
        """
        no_vehicle_access = self.slum_data.rim_data['Road']['point_of_vehicular_access_to_t'] if 'point_of_vehicular_access_to_t' in \
                                                self.slum_data.rim_data['Road'] else 0
        return (no_vehicle_access)

    def get_road_type(self):
        """
        The function `get_road_type` returns the type of roads within a slum settlement, or 0 if the
        information is not available.
        :return: the value of the variable `road_type`.
        """
        road_type = self.slum_data.rim_data['Road']['type_of_roads_within_the_settl'] if 'type_of_roads_within_the_settl' in \
                                                self.slum_data.rim_data['Road'] else 0
        return road_type

    def get_shop_count(self):
        """
        The function `get_shop_count` returns the count of shops in a slum.
        :return: the count of shops in a slum.
        """
        slum_type = ContentType.objects.get_for_model(Slum)
        get_shops_count_in_slum = len(Component.objects.filter(content_type=slum_type, object_id=self.slum.id,
                                                            metadata__name='Shops').values('shape'))
        if self.slum.id in slum_list:
            get_shops_count_in_slum = len(list(filter(lambda x: x.rhs_data and 'Type_of_structure_occupancy' in x.rhs_data and x.rhs_data[
                'Type_of_structure_occupancy'] == 'Shop', self.household_data)))
            
        return get_shops_count_in_slum

    def get_household_count(self):
        """
        The function returns the count of household data.
        :return: The length of the household_data list.
        """
        return len(self.household_data)

    def get_slum_population(self):
        """
        The function calculates the population of a slum by multiplying the household count by 4.
        :return: the slum population, which is calculated by multiplying the household count by 4.
        """
        return self.get_household_count() * 4

    # Waste section data
    def get_waste_facility(self, facility):
        """
        The function `get_waste_facility` returns the count of households that have a specific waste
        facility.
        
        :param facility: The `facility` parameter is a string that represents the type of waste facility
        :return: the count of items in the `household_data` list that have a non-empty `rhs_data` field and
        where the value of the `group_el9cl08/Facility_of_solid_waste_collection` key in `rhs_data` matches
        the `facility` parameter.
        """
        waste_facility_count = filter(lambda x: x.rhs_data and 'group_el9cl08/Facility_of_solid_waste_collection' in x.rhs_data and
                    x.rhs_data['group_el9cl08/Facility_of_solid_waste_collection'] == facility,self.household_data)
        return len(list(waste_facility_count))

    def get_perc_of_waste_collection(self, facility ='Door to door waste collection'):
        """
        The function calculates the percentage of waste collection for a specific facility based on the
        number of households.
        
        :param facility: The parameter "facility" is a string that represents the type of waste collection
        facility. In this case, the default value is set to "Door to door waste collection", defaults to
        Door to door waste collection (optional)
        :return: the percentage of waste collection for a specific facility, such as "Door to door waste
        collection".
        """
        percent = (self.get_waste_facility(facility) / self.get_household_count()) * 100 if self.get_household_count() !=0 else 0
        return (percent)

    # Water section data
    def get_water_coverage(self, type):
        """
        The function `get_water_coverage` returns the count of water facilities of a specific type in a
        household dataset.
        
        :param type: The "type" parameter is used to specify the type of water connection. It is used to
        filter the "self.household_data" list and count the number of water facilities that match the
        specified type
        :return: the count of water facilities that match the specified type.
        """
        water_facility_count = filter(lambda x: x.rhs_data and 'group_el9cl08/Type_of_water_connection' in x.rhs_data and x.rhs_data[
            'group_el9cl08/Type_of_water_connection'] == type, self.household_data)
        return len(list(water_facility_count))

    def get_perc_of_water_coverage(self, type='Individual connection'):
        """
        The function calculates the percentage of water coverage based on the type of connection and the
        number of occupied houses.
        
        :param type: The `type` parameter is used to specify the type of water connection. It can take one
        of the following values:, defaults to Individual connection (optional)
        :return: the percentage of water coverage for a given type of connection.
        """
        percent = (self.get_water_coverage(type) / self.occupied_houses()) * 100 if  self.occupied_houses() !=0 else 0
        return percent

    # General Information data
    def get_household_members(self):
        """
        The function `get_household_members` filters the `household_data` list to return household members
        with a number of household members less than 20.
        :return: The variable `household_mem` is being returned.
        """
        household_member =filter(lambda x: x.rhs_data and 'group_el9cl08/Number_of_household_members' in x.rhs_data
                                            and int(x.rhs_data['group_el9cl08/Number_of_household_members']) < 20,
                                            self.household_data)
        return household_member

    def get_household_member_total(self):
        """
        The function `get_household_member_total` calculates the total number of household members in a slum
        population based on the provided data.
        :return: the total number of household members in the slum population.
        """
        slum_population = 0
        for hh_data in self.household_data:
            if hh_data.rhs_data and hh_data.rhs_data != {} and hh_data.rhs_data != 'None':
                rhs = hh_data.rhs_data
                if 'group_el9cl08/Number_of_household_members' in rhs and rhs['group_el9cl08/Number_of_household_members'] and rhs['group_el9cl08/Number_of_household_members'] != "None" and rhs['group_el9cl08/Number_of_household_members'] == rhs['group_el9cl08/Number_of_household_members']:
                    try:
                        slum_population += int(rhs['group_el9cl08/Number_of_household_members'])
                    except Exception as e:
                        print(hh_data.id, rhs['group_el9cl08/Number_of_household_members'])
        return slum_population

    def get_slum_area_size_in_hectors(self):
        """
        The function `get_slum_area_size_in_hectors` returns the approximate area size of a slum settlement
        in hectares.
        :return: the approximate area of the slum area in hectares.
        """
        return int(self.slum_data.rim_data['General']['approximate_area_of_the_settle']) / 10000 \
            if 'approximate_area_of_the_settle' in self.slum_data.rim_data['General'] else 0

    def get_sex_ratio(self):
        """
        The `get_sex_ratio` function retrieves the number of male and female members in a household and
        returns a dictionary containing the counts.
        :return: a dictionary `mem_count` which contains the count of males and females in the household
        data.
        """
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
        """
        The function "key_takeaways_general" returns the values of land_owner, legal_status, and topography
        from the "General" section of the slum_data.rim_data dictionary.
        :return: a tuple containing the values of the variables land_owner, land_status, and topography.
        """
        general = self.slum_data.rim_data['General']
        land_owner = general['land_owner']
        land_status = general['legal_status']
        topography = general['topography']
        return (land_owner,land_status,topography)

    def key_takeaways_ctb(self,ctb):
        """
        The function `key_takeaways_ctb` collects various data related to the availability, cleanliness,
        facilities, and condition of a community toilet block (CTB) in a slum.
        
        :param ctb: The parameter "ctb" is a dictionary that contains data related to a community toilet
        block (CTB) in a slum. It is used to collect various attributes of the CTB, such as the
        availability of electricity, sewage disposal system, availability of water, cleanliness, condition
        of the CT
        :return: a tuple containing the values of various attributes related to the CTB (Community Toilet
        Block) in a slum. The attributes include electricity availability, sewage disposal system,
        availability of CTB at night, cleanliness of CTB, frequency of CTB cleaning, availability of water
        in CTB, type of water supply in CTB, number of doors in good condition, condition of CT
        """
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
        """
        The function `key_takeaways_road` extracts key information related to the road section from the slum
        data.
        :return: a tuple containing the values of `slum_level`, `huts_level`, and `vehicular_access`.
        """
        '''key take aways for road section'''
        road = self.slum_data.rim_data['Road']
        slum_level = road['is_the_settlement_below_or_abo'] if 'is_the_settlement_below_or_abo' in road else 0
        huts_level = road['are_the_huts_below_or_above_th'] if 'are_the_huts_below_or_above_th' in road else 0
        vehicular_access = road['point_of_vehicular_access_to_t'] if 'point_of_vehicular_access_to_t' in road else 0
        return (slum_level,huts_level,vehicular_access)

    def key_takeaways_water(self):
        """
        The function "key_takeaways_water" retrieves key information about water availability, coverage,
        quality, and alternative sources from the slum data.
        :return: a tuple containing the values of water_availability, water_coverage, water_quality, and
        alternate_water_source.
        """
        '''key take aways for water section'''
        water = self.slum_data.rim_data['Water']
        water_availability = water['availability_of_water'] if 'availability_of_water' in water else 0
        water_quality = water['quality_of_water_in_the_system'] if 'quality_of_water_in_the_system' in water else 0
        water_coverage = water['coverage_of_wateracross_settle'] if 'coverage_of_wateracross_settle' in water else 0
        alternate_water_source = water['alternative_source_of_water'] if 'alternative_source_of_water' in water else 0
        return (water_availability,water_coverage,water_quality,alternate_water_source)

    def key_takeaways_drain_n_gutter(self):
        """
        The function "key_takeaways_drain_n_gutter" retrieves key information about drainage and gutter
        conditions from the slum data.
        :return: a tuple containing the values of drain_block, drain_gradient, gutter_flood, and
        gutter_gradient.
        """
        '''key take aways for drinage and gutter section'''
        drainage = self.slum_data.rim_data['Drainage']
        gutter = self.slum_data.rim_data['Gutter']
        drain_block = drainage['do_the_drains_get_blocked'] if 'do_the_drains_get_blocked' in drainage else 0
        drain_gradient = drainage['is_the_drainage_gradient_adequ'] if 'is_the_drainage_gradient_adequ' in drainage else 0
        gutter_flood = gutter['do_gutters_flood'] if 'do_gutters_flood' in gutter else 0
        gutter_gradient = gutter['is_gutter_gradient_adequate'] if 'is_gutter_gradient_adequate' in gutter else 0
        return (drain_block, drain_gradient, gutter_flood, gutter_gradient)

    def key_takeaways_waste(self):
        """
        The function `key_takeaways_waste` retrieves key data points related to waste management from the
        slum data.
        :return: a tuple containing the following values:
        """
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