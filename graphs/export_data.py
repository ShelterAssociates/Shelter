from master.models import *
from graphs.models import *
from mastersheet.models import *
from sponsor.models import *
from component.models import *
from collections import Counter

def cityWiseQuery(city_id, startdate, enddate):
    all=[]
    city = CityReference.objects.filter(id = City.objects.filter(id = city_id).values_list('name_id')[0][0]).values_list('city_name')[0][0]

    construction_pocket = ToiletConstruction.objects.filter(slum__electoral_ward__administrative_ward__city__id = city_id, completion_date__range= [startdate, enddate])

    household_list = HouseholdData.objects.filter(city_id = city_id).values_list('household_number',flat= True)
    fff_data = HouseholdData.objects.filter(ff_data__isnull=False,city_id =city_id)

    family_factsheet_available = fff_data.values_list('household_number',flat= True)


    for i in fff_data:
        for j in construction_pocket :
            if i.household_number == j.household_number and i.slum_id == j.slum_id :
                family_data = {}
                family_data.update({'Household_number': i.household_number})

                sp = SponsorProjectDetails.objects.filter(slum_id = i.slum_id).exclude(sponsor_id = 10).values_list('household_code', 'sponsor_project_id')
                sp_name = ""
                for i1 in sp:
                    if i1[0] is not None:
                        if int(i.household_number) in i1[0]:
                            sp_name = SponsorProject.objects.filter(id = i1[1]).values_list('name', flat=True)[0]
                            break

                if sp_name == "":
                    family_data.update({'Sponsor Name': "Funder Not Assign"})
                else:
                    family_data.update({'Sponsor Name': sp_name})

                slum_name = Slum.objects.filter(id = i.slum_id).values_list('name',flat = True)[0]

                data1 =  SBMUpload.objects.filter(household_number = i.household_number, slum__id = i.slum_id).values_list('name', 'application_id', 'aadhar_number', 'phone_number')

                
                household_list = HouseholdData.objects.filter(household_number = i.household_number, slum__id = i.slum_id).values_list('rhs_data',flat= True)

                if  len(household_list) > 0:
                    if household_list[0] is not None and  household_list[0]['Type_of_structure_occupancy'] == 'Occupied house':
                        if 'group_og5bx85/Full_name_of_the_head_of_the_household' in household_list[0]:
                            family_data.update({'Name As Per RHS': household_list[0]['group_og5bx85/Full_name_of_the_head_of_the_household']})
                        else:
                            family_data.update({'Name As Per RHS': 'Name Not Available in RHS'})
                
                if data1.exists() == True:
                    data = data1.values_list('application_id', 'aadhar_number', 'phone_number')
                    if data[0][0] != 'nan':
                        family_data.update({'Application id': data[0][0]})
                    if data[0][1] != 'nan':
                        family_data.update({'Aadhar Number': data[0][1]})
                    if data[0][2] != 'nan':
                        family_data.update({'Phone Number': data[0][2]})

                
                family_data.update({'Slum Name': slum_name})
                ff_keys = i.ff_data.keys()
                questions_dict = {'group_im2th52/Total_family_members': 'Total_family_members', 'group_im2th52Number_of_members_over_60_years_of_age': 'Above 60 years', 'group_im2th52/Number_of_disabled_members': 'disable_members', 
                'group_im2th52/Number_of_Male_members': 'Male_members', 'group_im2th52/Number_of_Female_members': 'Female_members', 'group_im2th52/Number_of_Girl_children_between_0_18_yrs': 'Between_0_to_18', 
                'group_im2th52/Number_of_Children_under_5_years_of_age': 'Below 5 years', 'group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet': 'Have You Upgraded ?', 'group_ne3ao98/Cost_of_upgradation_in_Rs': 'Cost Of Upgradetion?', 
                'group_ne3ao98/Where_the_individual_ilet_is_connected_to': 'Toilet Connected To.', 'group_oh4zf84/Name_of_the_family_head': 'Name As Per Factsheet', 'group_oh4zf84/Ownership_status': 'Ownership Status As Per Factsheet', 
                'group_ne3ao98/Who_has_built_your_toilet': 'Who has built your toilet ?', 'group_im2th52/Number_of_members_over_60_years_of_age':'Above 60 years'}
                
                '''Using question_dict to iterate over the over all data for getting required data for factsheet export.'''
                for key in questions_dict.keys():
                    if key in ff_keys:
                        family_data.update({questions_dict[key]:i.ff_data[key]})
                
                all.append(family_data)


    return all, city

def get_slums(city):
    '''This function provide all the slum for a city.'''
    slums = Slum.objects.filter(electoral_ward__administrative_ward__city_id__in = [city])
    return slums

def get_slum_names(city):
    '''Using This function to get all Slum name count accross a city.'''
    slums = Slum.objects.filter(electoral_ward__administrative_ward__city_id__in = [city]).values_list('id', 'name')
    slum_name_dict = {i[0] : i[1] for i in slums}
    return slum_name_dict

def get_occupacy_status(city):
    '''Using This function to get Occupancy status count accross a city.'''
    data = HouseholdData.objects.filter(city_id = city, rhs_data__isnull = False).values_list('rhs_data', 'slum_id')
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

def get_structure_data(city):
    '''Using This function to get all Structure count accross a city.'''
    final_component_data = {}
    component_data = Component.objects.filter(metadata_id = 1, object_id__in = Slum.objects.filter(electoral_ward__administrative_ward__city_id__in = [city])).values_list('object_id', flat = True)
    final_component_data = Counter(component_data)   # Creating dictionary with slum_id as key and Structure conut as a value.
    return dict(final_component_data)



def Structure_data(city):
    '''We use this function for exporting structure data count with household data count.'''
    final_data_lst = []
    rhs_data_cnt = get_occupacy_status(city)
    component_data = get_structure_data(city)
    slum_names = get_slum_names(city)
    city_name = CityReference.objects.filter(id = City.objects.filter(id = city).values_list('name_id')[0][0]).values_list('city_name')[0][0]
    for slum_id, count in component_data.items():
        if slum_id in rhs_data_cnt:
            rhs_data_status = rhs_data_cnt[slum_id]
        else:
            rhs_data_status = {}
        rhs_data_status.update({'Slum Name': slum_names[slum_id], 'Total Structure (In KML)':count})
        final_data_lst.append(rhs_data_status)
    return final_data_lst, city_name
        
