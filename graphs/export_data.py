import itertools
from master.models import *
from graphs.models import *
from mastersheet.models import *
from sponsor.models import *
from component.models import *
from collections import Counter, defaultdict
import datetime


class exportMethods:
    
    def __init__(self, city_id):
        self.household_data = HouseholdData.objects.all()
        self.city_reference = CityReference.objects.all()
        self.toilet_data = ToiletConstruction.objects.all()
        self.slum = Slum.objects.all()
        self.city = city_id
        self.city_name = self.city_reference.get(id =  City.objects.get(id = self.city).name_id).city_name
        
        
    def cityWiseQuery(self, startdate, enddate):
        output_data = []
        """ In Array we are storing the household queryset objects which have factsheet data available."""
        factsheet_data_households = []
        """ Here we are checking construction data available for selected city. """
        """Case :-1 phase_one_material_date not null """
        construction_data_phase_1 = self.toilet_data.filter(slum__electoral_ward__administrative_ward__city__id = self.city, phase_one_material_date__range = [startdate, enddate], completion_date__isnull = False)
        """Case :-2 phase_one_material_date is null. In this case we are going to query on phase_two_material_date"""
        construction_data_phase_2 = self.toilet_data.filter(slum__electoral_ward__administrative_ward__city__id = self.city, phase_two_material_date__range = [startdate, enddate], phase_one_material_date__isnull = True, completion_date__isnull = False)
        """ Here we are combining the both queryset object to single object"""
        construction_data = construction_data_phase_1.values_list('slum_id', 'household_number') | construction_data_phase_2.values_list('slum_id', 'household_number')
        """ Creating a groupby object to for making groups of slum_ids and households. """
        construction_group = itertools.groupby(sorted(construction_data.values_list('slum_id', 'household_number'), key = lambda x:x[0]), key = lambda x:x[0])
        """ Here we iterate on construction data groups slum by slum and getting the household querysets which have factsheet data available."""
        for i in construction_group:
            slum_id, households = i[0], [obj[1] for obj in list(i[1])]
            factsheet_objects = self.household_data.filter(slum_id = slum_id, household_number__in = households, ff_data__isnull = False)
            if len(factsheet_objects) > 0:
                factsheet_data_households.extend(list(factsheet_objects))
        # Get Sponsor Project details slum_wise.
        slums = set(list(construction_data.values_list('slum_id', flat = True)))
        sponsor_data = SponsorProjectDetails.objects.filter(slum_id__in = slums).exclude(sponsor_id = 10)
        sponsor_name = SponsorProject.objects.filter(id__in = set(sponsor_data.values_list('sponsor_project_id', flat = True)))
        sponsor_name_dict = {i.id : i.name for i in sponsor_name}
        sponsor_data_lst = {}
        for sp_obj in sponsor_data:
            for hh in sp_obj.household_code:
                search_key = str(sp_obj.slum_id) + str(hh)
                sponsor_data_lst[search_key] = sponsor_name_dict[sp_obj.sponsor_project_id]
        # Create factsheet data for Response.
        for hh_object in factsheet_data_households:
                family_data = {}
                family_data.update({'Household_number': hh_object.household_number})
                # Getting Sponsor Project name details from sponsor_data_lst.
                search_key = str(hh_object.slum_id) + str(hh_object.household_number)
                if not search_key in sponsor_data_lst:
                    family_data.update({'Sponsor Name': "Funder Not Assign"})
                else:
                    family_data.update({'Sponsor Name': sponsor_data_lst[search_key]})
                """ Adding Slum Name details here."""
                slum_name = self.slum.get(id = hh_object.slum_id).name
                family_data.update({'Slum Name': slum_name})
                """SBM data questions for report(household wise)."""
                sbmData =  SBMUpload.objects.filter(household_number = hh_object.household_number, slum__id = hh_object.slum_id)
                """Removing Null Keys and adding to the response dict."""    
                if sbmData.exists():
                    data = sbmData.values('application_id', 'aadhar_number', 'phone_number')[0]
                    sbm_data = {k.replace('_', " ").capitalize() : v for k, v in data.items() if v != 'nan'}
                    family_data.update(sbm_data)
                """ Adding Factsheet data in Response dict."""
                ff_keys = hh_object.ff_data.keys()
                questions_dict = {'group_im2th52/Total_family_members': 'Total_family_members', 'group_im2th52Number_of_members_over_60_years_of_age': 'Above 60 years', 'group_im2th52/Number_of_disabled_members': 'disable_members', 
                'group_im2th52/Number_of_Male_members': 'Male_members', 'group_im2th52/Number_of_Female_members': 'Female_members', 'group_im2th52/Number_of_Girl_children_between_0_18_yrs': 'Between_0_to_18', 
                'group_im2th52/Number_of_Children_under_5_years_of_age': 'Below 5 years', 'group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet': 'Have You Upgraded ?', 'group_ne3ao98/Cost_of_upgradation_in_Rs': 'Cost Of Upgradetion?', 
                'group_ne3ao98/Where_the_individual_ilet_is_connected_to': 'Toilet Connected To.', 'group_oh4zf84/Name_of_the_family_head': 'Name As Per Factsheet', 'group_oh4zf84/Ownership_status': 'Ownership Status As Per Factsheet', 
                'group_ne3ao98/Who_has_built_your_toilet': 'Who has built your toilet ?', 'group_im2th52/Number_of_members_over_60_years_of_age':'Above 60 years'}
                '''Using question_dict to iterate over the over all data for getting required data for factsheet export.'''
                for key in questions_dict.keys():
                    if key in ff_keys:
                        family_data.update({questions_dict[key]:hh_object.ff_data[key]})
                if 'group_og5bx85/Full_name_of_the_head_of_the_household' in hh_object.rhs_data:
                    family_data.update({'Name As Per RHS':hh_object.rhs_data['group_og5bx85/Full_name_of_the_head_of_the_household']})
                # Adding Data to output list household wise.
                output_data.append(family_data)
        return output_data, self.city_name
    
    def get_occupacy_status(self):
        '''Using This function to get Occupancy status count accross a city.'''
        data = self.household_data.filter(city_id = self.city, rhs_data__isnull = False).values_list('rhs_data', 'slum_id')
        status_cnt_dct = {}
        for data_obj in data:
            record, slum = data_obj
            if 'Type_of_structure_occupancy' in record:
                if slum not in status_cnt_dct:
                    status_cnt_dct[slum] = {record['Type_of_structure_occupancy']:1}
                else:
                    temp = status_cnt_dct[slum]
                    if record['Type_of_structure_occupancy'] not in temp:
                        temp[record['Type_of_structure_occupancy']] = 1
                    else:
                        temp[record['Type_of_structure_occupancy']]  += 1
        return status_cnt_dct
    
    def get_structure_data(self):
        '''Using This function to get all Structure count accross a city.'''
        final_component_data = {}
        component_data = Component.objects.filter(metadata_id = 1, object_id__in = Slum.objects.filter(electoral_ward__administrative_ward__city_id__in = [self.city])).values_list('object_id', flat = True)
        final_component_data = Counter(component_data)   # Creating dictionary with slum_id as key and Structure conut as a value.
        return dict(final_component_data)
    
    def SlumNameLst(self):
        """ Creating a dictionary with slum names."""
        slums = self.slum.filter(electoral_ward__administrative_ward__city_id__in = [self.city]).values_list('id', 'name', 'electoral_ward__administrative_ward__name')
        slum_name_dict = {i[0] : [i[1], i[2]] for i in slums}
        return slum_name_dict
    
    def Structure_data(self):
        '''We use this function for exporting structure data count with household data count.'''
        final_data_lst = []
        rhs_data_cnt = self.get_occupacy_status()
        component_data = self.get_structure_data()
        """ Creating a dictionary with slum names."""
        slum_name_dict = self.SlumNameLst()
        for slum_id, count in component_data.items():
            if slum_id in rhs_data_cnt:
                rhs_data_status = rhs_data_cnt[slum_id]
            else:
                rhs_data_status = {}
            rhs_data_status.update({'Slum Name': slum_name_dict[slum_id][0], 'Admin Ward' : slum_name_dict[slum_id][1], 'Total Structure (In KML)':count})
            final_data_lst.append(rhs_data_status)
        return final_data_lst, self.city_name
    
    def cityWiseRhsData(self):
        question = {'rhs_uuid' : "Avni UUID", 'Date_of_survey' : "Survey Date", 'Name_s_of_the_surveyor_s' :"Name of the Surveyor", 'Type_of_structure_occupancy' : "Type of structure occupancy", 'Type_of_unoccupied_house' : "Type of unoccupied house", 'Parent_household_number' : "Parent household number", 'group_og5bx85/Full_name_of_the_head_of_the_household' : "Full name of the head of the household", "group_el9cl08/Enter_the_10_digit_mobile_number" : "Enter the 10 digit mobile number",
            "group_el9cl08/Aadhar_number" : "Aadhar number", "group_el9cl08/Number_of_household_members":"Number of household members", 'group_el9cl08/Do_you_have_any_girl_child_chi':"Do you have any girl child/children under the age of 18?", "group_el9cl08/How_many":"How many ? ( Count )", "group_el9cl08/Type_of_structure_of_the_house":"Type of structure of house",
            "group_el9cl08/Ownership_status_of_the_house":"Ownership status of the household", "group_el9cl08/House_area_in_sq_ft":"House area in sq. ft.", "group_el9cl08/Type_of_water_connection" :"Type of water connection", "group_el9cl08/Facility_of_solid_waste_collection" : "group_el9cl08/Facility_of_solid_waste_collection", "Plus code of the house":"Plus code of the house", "group_oi8ts04/Are_you_interested_in_an_indiv":"Are you interested in an individual toilet?", "group_oi8ts04/Current_place_of_defecation": "Current place of defecation", 'group_oi8ts04/OD1':'Does any member of the household go for open defecation ?', 'Do you have a toilet at home?':'Do you have a toilet at home?',
            'group_oi8ts04/If_no_why': 'If no for individual toilet , why?', 'group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built': 'Under what scheme would you like your toilet to be built ?', "Total number of female members (including children)": "Total female members", "Total number of male members (including children)":"total male members", "Total number of third gender members (including children)?":"total other gender members", "Do you have electricity in the house ?" : "Do you have electricity in the house ?", "If yes for electricity ,  type of meter ?" : "If yes for electricity ,  type of meter ?", "Date of Survey" : "Date of Survey for sanitation",
            'Is there any seperated woman in the household ?': 'Is there any seperated woman in the household ?', 'Is there any widow woman in the household?': 'Is there any widow woman in the household?', 'Is any family member physically/mentally challenged?': 'Is any family member physically/mentally challenged?', 'HH_can_connect_to_Drainage' : 'HH can connect to Drainage line', 'floor_type' : 'Floor Type'}
        
        """ Creating a dictionary with slum names."""
        slum_name_dict = self.SlumNameLst()
        construction_data = self.toilet_data.filter(slum_id__in = list(slum_name_dict.keys())).exclude(agreement_cancelled = True).values_list('household_number', 'status', 'slum_id')
        """ Create groupby object of construction_data for mapping."""
        construction_data_dct = defaultdict(dict)
        for household, status, slum_id in construction_data:
            if household not in construction_data_dct[slum_id]:
                construction_data_dct[slum_id][household] = status
                
        construction_data = dict(construction_data_dct)
        """ Here we are creating slum wise group of hh who has toilet construction data (for mapping)"""
        """Extracting Followup data and sorting data as per the last modified date."""
        cod_data = FollowupData.objects.filter(slum_id__in = list(slum_name_dict.keys())).values('household_number', 'followup_data', 'submission_date', 'slum_id')
        followup_data = {}
        for followup_record in cod_data:
            if followup_record['slum_id'] in followup_data:
                followup_data_slum = followup_data[followup_record['slum_id']]
                if str(int(followup_record['household_number'])) in followup_data_slum:
                    temp = followup_data_slum[str(int(followup_record['household_number']))]
                    if temp['submission_date'] < followup_record['submission_date']:
                        hh = str(int(followup_record['household_number']))
                        del followup_record['household_number']
                        temp = followup_record
                        followup_data_slum[hh] = temp
                else:
                    hh = str(int(followup_record['household_number']))
                    temp_dict = {'submission_date':followup_record['submission_date'], 'followup_data':followup_record['followup_data']}
                    followup_data_slum[hh] = temp_dict
            else:
                slum = followup_record['slum_id']
                hh = str(int(followup_record['household_number']))
                temp_dict = {'submission_date':followup_record['submission_date'], 'followup_data':followup_record['followup_data']}
                dict_ = {hh:temp_dict}
                followup_data[slum] = dict_
        """Extracting City wise household data."""
        householdData = self.household_data.filter(city_id = self.city, rhs_data__isnull = False)
        def check_rhs_data(record):
            key_list = ['rhs_uuid', 'Date_of_survey', 'Name_s_of_the_surveyor_s', 'Type_of_structure_occupancy', 'Type_of_unoccupied_house', 'Parent_household_number', 'group_og5bx85/Full_name_of_the_head_of_the_household', "group_el9cl08/Enter_the_10_digit_mobile_number",
            "group_el9cl08/Aadhar_number", "group_el9cl08/Number_of_household_members", 'group_el9cl08/Do_you_have_any_girl_child_chi', 'Is there any seperated woman in the household ?', 'Is there any widow woman in the household?', 'Is any family member physically/mentally challenged?', "group_el9cl08/How_many", "group_el9cl08/Type_of_structure_of_the_house",
            "group_el9cl08/Ownership_status_of_the_house", "group_el9cl08/House_area_in_sq_ft", "group_el9cl08/Type_of_water_connection", "group_el9cl08/Facility_of_solid_waste_collection", "Plus code of the house", 'Total number of female members (including children)', 'Total number of male members (including children)', 'Total number of third gender members (including children)?', 'HH_can_connect_to_Drainage', 'floor_type']
            # if occupied house then if block called otherwise else block called.
            electricity_keys = ['If yes for electricity ,  type of meter ?', 'Do you have electricity in the house ?']
            member_keys = {"group_el9cl08/Total_number_of_fema_including_children": "Total female members", "group_el9cl08/Total_number_of_male_including_children":"total male members", "group_el9cl08/Total_number_of_Other_gender_members":"total other gender members"}
            if record.rhs_data:
                if record.rhs_data['Type_of_structure_occupancy'] == 'Occupied house':
                    data = {question[rhs_key] :record.rhs_data[rhs_key] for rhs_key in key_list if rhs_key in record.rhs_data}
                    if "Electricity_data" in record.rhs_data:
                        electricity_data_obj = record.rhs_data['Electricity_data']
                        electricity_data = {question[key] :electricity_data_obj[key] for key in electricity_keys if key in electricity_data_obj}
                        data.update(electricity_data)
                    member_data = {member_keys[mem_key] :record.rhs_data[mem_key] for mem_key, mem_val in member_keys.items() if mem_val not in data and mem_key in record.rhs_data}
                    data.update(member_data)
                else:
                    key_list = ['rhs_uuid', 'Date_of_survey', 'Name_s_of_the_surveyor_s', 'Type_of_structure_occupancy', "Plus code of the house", 'HH_can_connect_to_Drainage', 'floor_type']
                    data = {question[rhs_key] :record.rhs_data[rhs_key] for rhs_key in key_list if rhs_key in record.rhs_data}
            else:
                data = {}
            data['Household number'] = record.household_number
            data['Household_id'] = record.id
            data['slum_id'] = record.slum_id
            data['Last Modified At'] = str(datetime.datetime.strptime(str(record.submission_date)[:10], '%Y-%m-%d').date())
            if record.slum_id in slum_name_dict:
                data['Slum'] = slum_name_dict[record.slum_id][0]
                data['Admin'] = slum_name_dict[record.slum_id][1]
            return data
        """Iterating household data and selecting question for response data."""
        formdict = list(map(check_rhs_data, householdData))
        """Adding Followup data and Construction data in this city wise data."""
        for rhs_data in formdict:
            """ If the followup data is available then this block will run."""
            if rhs_data['slum_id'] in followup_data and ("Type of structure occupancy" in rhs_data and rhs_data["Type of structure occupancy"] == 'Occupied house'):
                followup_slum_data = followup_data[rhs_data['slum_id']]
                if str(int(rhs_data['Household number'])) in followup_slum_data:
                    final_followup_data = followup_slum_data[str(int(rhs_data['Household number']))]
                    data = final_followup_data['followup_data']
                    temp = {}
                    key_lst = {'Type of household toilet ?' : 'Type of household toilet ?', 'group_el9cl08/Does_any_household_m_n_skills_given_below': 'Does any household member have any of the construction skills give below?', 'group_oi8ts04/Have_you_applied_for_individua': 'Have you applied for an individual toilet under SBM?', 'group_oi8ts04/How_many_installments_have_you': 'How many installments have you received?', 'group_oi8ts04/When_did_you_receive_ur_first_installment': 'When did you receive your first installment?', 'group_oi8ts04/When_did_you_receive_r_second_installment': 'When did you receive your second installment?', 'group_oi8ts04/When_did_you_receive_ur_third_installment': 'When did you receive your third installment?', 'group_oi8ts04/If_built_by_contract_ow_satisfied_are_you': 'If built by a contractor, how satisfied are you?', 'group_oi8ts04/Status_of_toilet_under_SBM': 'Status of toilet under SBM?', 'group_oi8ts04/What_was_the_cost_in_to_build_the_toilet': 'What was the cost incurred to build the toilet?', 'group_oi8ts04/Current_place_of_defecation': 'Current place of defecation', 'group_oi8ts04/Which_Community_Toil_r_family_members_use': 'Which CTB', 'group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets': 'Is there availability of drainage to connect to the toilet?', 'group_oi8ts04/Are_you_interested_in_an_indiv': 'Are you interested in an individual toilet?', 'group_oi8ts04/What_kind_of_toilet_would_you_likes': 'What kind of toilet would you like?', 'group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built': 'Under what scheme would you like your toilet to be built?', 'group_oi8ts04/If_yes_why': 'If yes, why?', 'group_oi8ts04/If_no_why': 'If no, why?', 'group_oi8ts04/What_is_the_toilet_connected_to': 'What is the toilet connected to?', 'group_oi8ts04/Who_all_use_toilets_in_the_hou': 'Who all use toilets in the household?', 'group_oi8ts04/Reason_for_not_using_toilet': 'Reason for not using toilet', 'Do you have a toilet at home?': 'Do you have a toilet at home?', "Date of Survey" : "Date of Survey for sanitation"}
                    for key in key_lst.keys():
                        if key in data:
                            temp[key_lst[key]] = data[key]
                    if temp != {}:
                        rhs_data.update(temp)
            """ If the household has construction data then this block will run."""
            try :
                exclude_lst = {1053: ['791'], 1294: ['141'], 1008: ['882'], 1047: ['130'], 1014: ['213'], 1052: ['178'], 1119: ['108'], 1059: ['117'], 1028: ['819'], 1138: ['1970'], 1054: ['140'], 600: ['405'], 1285: ['35'], 1348: ['131']}
                if rhs_data['slum_id'] in construction_data:
                    if rhs_data['slum_id'] in exclude_lst:
                        if str(int(rhs_data['Household number'])) in exclude_lst[rhs_data['slum_id']]:
                            continue
                    slum_construction_data = construction_data[rhs_data['slum_id']]
                    if str(int(rhs_data['Household number'])) in slum_construction_data:
                        rhs_data['Final_Status'] = ToiletConstruction.get_status_display(int(slum_construction_data[str(int(rhs_data['Household number']))]))
            except Exception as e:
                print(e)
                    
        return formdict, self.city_name