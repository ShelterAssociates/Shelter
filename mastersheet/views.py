from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test, permission_required
from graphs.sync_avni_data import avni_sync
from mastersheet.forms import find_slum, file_form, account_find_slum, gis_tab
from django.db.models import Count, F, Q
from mastersheet.models import *
from sponsor.models import *
from itertools import chain
from master.models import *
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import pandas
import csv
from django.conf import settings
import collections
from mastersheet.daily_reporting_sync import ToiletConstructionSync, CommunityMobilizaitonSync
from utils.utils_permission import apply_permissions_ajax
from .decorators import deco_city_permission
from collections import defaultdict
import datetime
import itertools
from xlwt import Workbook
from mastersheet.models import *
from graphs.models import *
from django.core import serializers
from django.contrib.postgres.aggregates import ArrayAgg
from graphs.export_data import exportMethods


# The views in this file correspond to the mastersheet functionality of shelter app.
def give_details(request):
    slum_info_dict = {}
    try:
        delimiter = '&'
        slum_code = Slum.objects.filter(pk=int(request.GET.get('form').split('&')[1].split('=')[1])).values_list(
            "shelter_slum_code", "electoral_ward__administrative_ward__city__id", "electoral_ward__name", "name")
        slum_info_dict.update(
            {"Name of the slum": slum_code[0][3], "Electoral Ward": slum_code[0][2], "City Code": slum_code[0][1]})

    except Exception as e:
        print(e)
    return HttpResponse(json.dumps(slum_info_dict), content_type='application/json')


# 'masterSheet()' is the principal view.
# It collects the data from newest version of RHS form and family factsheets
# Also, it retrieves the data of accounts and SBM. This view bundles them in a single object
# to be displayed to the front end.

@csrf_exempt
@apply_permissions_ajax('mastersheet.can_view_mastersheet')
@deco_city_permission
def masterSheet(request, slum_code=0, FF_code=0, RHS_code=0):
    flag_fetch_rhs = 'show_rhs' in request.GET
    flag_fetch_ff = 'show_ff' in request.GET

    try:
        formdict = []
        formdict_family_factsheet = []
        slum_code = Slum.objects.filter(pk=int(request.GET['slumname'])).values_list("id", "shelter_slum_code",
                                                                                     "electoral_ward__administrative_ward__city__id",
                                                                                     "electoral_ward__name", "name")

        slum_funder = SponsorProjectDetails.objects.filter(slum__name=str(slum_code[0][4])).exclude(sponsor__id=10)
        form_ids = Survey.objects.filter(city__id=int(slum_code[0][2]))
        household_data = HouseholdData.objects.filter(slum__id=slum_code[0][0])

        if slum_code is not 0:
            if flag_fetch_rhs:

                # this check_rhs_data function return data as per occupacy status
                def check_rhs_data(record):
                    key_list = ['rhs_uuid', 'Date_of_survey', 'Name_s_of_the_surveyor_s', 'Type_of_structure_occupancy', 'Type_of_unoccupied_house', 'Parent_household_number', 'group_og5bx85/Full_name_of_the_head_of_the_household', "group_el9cl08/Enter_the_10_digit_mobile_number",
                    "group_el9cl08/Aadhar_number", "group_el9cl08/Number_of_household_members", 'group_el9cl08/Do_you_have_any_girl_child_chi', "group_el9cl08/How_many", "group_el9cl08/Type_of_structure_of_the_house",
                    "group_el9cl08/Ownership_status_of_the_house", "group_el9cl08/House_area_in_sq_ft", "group_el9cl08/Type_of_water_connection", "group_el9cl08/Facility_of_solid_waste_collection", "Plus code of the house", 'Plus Code Part']
                    # if occupied house then if block called otherwise else block called.
                    if record.rhs_data and record.rhs_data['Type_of_structure_occupancy'] == 'Occupied house':
                        data = {rhs_key :record.rhs_data[rhs_key] for rhs_key in key_list if rhs_key in record.rhs_data}
                        data['Household_number'] = record.household_number
                        data['group_og5bx85/Type_of_survey'] = "RHS"
                        data['Household_id'] = record.id
                        return data
                    else:
                        key_list = ['rhs_uuid', 'Date_of_survey', 'Name_s_of_the_surveyor_s', 'Type_of_structure_occupancy', 'group_og5bx85/Type_of_survey', "Plus code of the house", 'Plus Code Part']
                        if record.rhs_data:
                            data = {rhs_key :record.rhs_data[rhs_key] for rhs_key in key_list if rhs_key in record.rhs_data}
                        else:
                            data = {}
                        data['Household_number'] = record.household_number
                        data['Household_id'] = record.id
                        return data
                
                formdict = list(map(check_rhs_data, household_data))
                cod_data = FollowupData.objects.filter(slum=slum_code[0][0]).values('household_number', 'followup_data', 'submission_date')
                followup_data = {}
                for followup_record in cod_data:
                    if str(int(followup_record['household_number'])) in followup_data:
                        temp = followup_data[str(int(followup_record['household_number']))]
                        if temp['submission_date'] < followup_record['submission_date']:
                            hh = str(int(followup_record['household_number']))
                            del followup_record['household_number']
                            temp = followup_record
                            followup_data[hh] = temp
                    else:
                        hh = str(int(followup_record['household_number']))
                        temp_dict = {'submission_date':followup_record['submission_date'], 'followup_data':followup_record['followup_data']}
                        followup_data[hh] = temp_dict
                
            else:
                formdict = list(map(lambda x: {'Household_number': x.household_number, 'id': x.id, 'rhs_uuid': x.rhs_data['rhs_uuid'] if 'rhs_uuid' in x.rhs_data else None}, filter(lambda x: x.rhs_data != None, household_data)))
            # Family Factsheet - fetching data
            if flag_fetch_ff:
                try:
                    def get_factsheet_data(record):
                        key_list = ['group_vq77l17/Household_number', 'group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet', 
                        'group_ne3ao98/Cost_of_upgradation_in_Rs', 'group_ne3ao98/Where_the_individual_ilet_is_connected_to', 
                        'group_ne3ao98/Use_of_toilet', '_attachments', 'ff_uuid', 'Family_Photo', 'Toilet_Photo']
                        if record.ff_data:
                            data = {}
                            for data_key in key_list:
                                if data_key in record.ff_data:
                                    data[data_key] = record.ff_data[data_key]
                        else:
                            data = {'group_vq77l17/Household_number': 00}
                        return data

                    formdict_family_factsheet = list(map(get_factsheet_data, household_data))

                except Exception as e:
                    print(e, 'in ff')
                temp_FF = {str(int(obj_FF['group_vq77l17/Household_number'])): obj_FF for obj_FF in
                           formdict_family_factsheet}
                temp_FF_keys = temp_FF.keys()  # list of household numbers

            # Daily Reporting - fetching data
            toilet_reconstruction_fields = ['slum', 'slum__name', 'household_number', 'agreement_date_str',
                                            'agreement_cancelled',
                                            'septic_tank_date_str', 'phase_one_material_date_str',
                                            'phase_two_material_date_str', 'phase_three_material_date_str',
                                            'completion_date_str', 'status', 'comment', 'pocket',
                                            'p1_material_shifted_to',
                                            'p2_material_shifted_to', 'p3_material_shifted_to',
                                            'st_material_shifted_to',
                                            'id']

            daily_reporting_data = ToiletConstruction.objects.extra(
                select={'phase_one_material_date_str': "to_char(phase_one_material_date, 'YYYY-MM-DD ')",
                        'phase_two_material_date_str': "to_char(phase_two_material_date, 'YYYY-MM-DD ')",
                        'phase_three_material_date_str': "to_char(phase_three_material_date, 'YYYY-MM-DD ')",
                        'septic_tank_date_str': "to_char(septic_tank_date, 'YYYY-MM-DD ')",
                        'agreement_date_str': "to_char(agreement_date, 'YYYY-MM-DD ')",
                        'completion_date_str': "to_char(completion_date, 'YYYY-MM-DD ')"}).filter(
                slum__id=slum_code[0][0])

            daily_reporting_data = daily_reporting_data.values(*toilet_reconstruction_fields)

            for i in daily_reporting_data:
                if i['status'] is not None:
                    if i['status'].strip() != "":
                        i['status'] = ToiletConstruction.get_status_display(i['status'])
                        i['delay_flag'] = ''
                if i['agreement_date_str'] != None and i['status'] != 'Agreement cancel':
                    if i['phase_one_material_date_str'] == None and is_delayed(i['agreement_date_str']):
                        i['delay_flag'] = '#f9a4a4'  # phase one delayed
                    if i['phase_two_material_date_str'] == None and is_delayed(i['phase_one_material_date_str']):
                        i['delay_flag'] = '#f2f29f'  # phase two delayed
                    if i['phase_one_material_date_str'] != i['phase_three_material_date_str']:
                        if i['phase_three_material_date_str'] == None and is_delayed(i['phase_two_material_date_str']):
                            i['delay_flag'] = '#aaf9a4'
                        if i['completion_date_str'] == None and is_delayed(i['phase_three_material_date_str']):
                            i['delay_flag'] = '#aaa4f4'
                    else:
                        if i['completion_date_str'] == None and is_delayed(i['phase_two_material_date_str']):
                            i['delay_flag'] = '#aaa4f4'
            temp_daily_reporting = {str(int(obj_DR['household_number'])): obj_DR for obj_DR in daily_reporting_data}
            temp_DR_keys = temp_daily_reporting.keys()

            # SBM - fetching data
            sbm_fields = ['slum', 'slum__name', 'household_number', 'name', 'application_id', 'photo_uploaded',
                          'created_date_str', 'id', 'phone_number', 'aadhar_number', 'photo_verified', 'photo_approved',
                          'application_verified', 'application_approved', 'sbm_comment']
        
            sbm_data = SBMUpload.objects.extra(
                select={'created_date_str': "to_char(created_date, 'YYYY-MM-DD ')"}).filter(
                slum__id=slum_code[0][0])

            sbm_data = sbm_data.values(*sbm_fields)

            temp_sbm = {str(obj_DR['household_number']): obj_DR for obj_DR in sbm_data}
            temp_sbm_keys = temp_sbm.keys()

            # # Community Mobilization - fetching data
            community_mobilization_fields = ['slum', 'slum__name', 'household_number', 'activity_type',
                                             'activity_date_str',
                                             'id']
            community_mobilization_data = CommunityMobilization.objects.extra(
                select={'activity_date_str': "to_char(activity_date, 'YYYY-MM-DD ')"}).filter(
                slum__id=slum_code[0][0])
            community_mobilization_data_avni = list(CommunityMobilizationActivityAttendance.objects.filter(
                slum_id=slum_code[0][0]))

            # Vendor and Accounts - fetching data
            vendor = VendorHouseholdInvoiceDetail.objects.filter(slum__id=slum_code[0][0])
            invoices = InvoiceItems.objects.filter(slum__id=slum_code[0][0])

            dummy_formdict = {str(int(x['Household_number'])): x for x in formdict}

            for y in invoices:
                for z in y.household_numbers:
                    if str(z) not in dummy_formdict.keys():
                        dummy_formdict[str(z)] = {
                            "Household_number": str(z),
                            "_id": "",
                            "ff_id": "",
                            "no_rhs_flag": "#eba6fc"
                        }
                    invoice_number = "invoice_number" + str(y.material_type)
                    dummy_formdict[str(z)].update({
                        invoice_number: y.invoice.invoice_number,
                        str(y.material_type) + " Invoice Number" + "_id": y.invoice.id
                    })

            for y in community_mobilization_data_avni:
                new_activity_type = y.activity_type.name
                if y.household_number in dummy_formdict.keys():
                    dummy_formdict[str(y.household_number)].update(
                        {new_activity_type: str(y.date_of_activity), str(new_activity_type) + "_id": y.id})
                else:
                    dummy_formdict[str(int(y.household_number))] = {
                        "Household_number": str(int(y.household_number)),
                        "_id": "",
                        "ff_id": "",
                        "no_rhs_flag": "#eba6fc"
                    }
                    dummy_formdict[str(int(y.household_number))].update(
                        {new_activity_type: str(y.date_of_activity), str(new_activity_type) + "_id": y.id})

            for y in community_mobilization_data:
                if y.household_number != None:
                    y.household_number = [i for i in y.household_number if i != ""]
                    for z in y.household_number:
                        new_activity_type = y.activity_type.name
                        z = str(int(z))
                        if z not in dummy_formdict.keys():
                            dummy_formdict[z] = {
                                "Household_number": z,
                                "_id": "",
                                "ff_id": "",
                                "no_rhs_flag": "#eba6fc"
                            }
                        dummy_formdict[z].update(
                            {new_activity_type: y.activity_date_str, str(new_activity_type) + "_id": y.id})

            for i in temp_sbm_keys:
                if str(i) not in dummy_formdict.keys():
                    dummy_formdict[str(i)] = {
                        "Household_number": i,
                        "_id": "",
                        "ff_id": "",
                        "no_rhs_flag": "#eba6fc"
                    }
                dummy_formdict[str(i)].update(temp_sbm[str(i)])
                dummy_formdict[str(i)].update({'sbm_id_' + str(i): temp_sbm[str(i)]['id']})

            for i in temp_DR_keys:
                if str(i) not in dummy_formdict.keys():
                    dummy_formdict[str(i)] = {
                        "Household_number": i,
                        "_id": "",
                        "ff_id": "",
                        "no_rhs_flag": "#eba6fc"
                    }
                dummy_formdict[str(i)].update(temp_daily_reporting[str(i)])
                dummy_formdict[str(i)].update({'tc_id_' + str(i): temp_daily_reporting[str(i)]['id']})

            for key, x in dummy_formdict.items():
                try:
                    if len(x['p1_material_shifted_to']) != 0 or len(x['p2_material_shifted_to']) != 0 or len(
                            x['p3_material_shifted_to']) != 0 or len(x['st_material_shifted_to']) != 0:
                        x['material_shifts'] = '#f9cb9f'
                    else:
                        x['material_shifts'] = None
                except Exception as e:
                    x['material_shifts'] = None

                temp = x['_id'] if '_id' in x else None
                x['slum__name'] = slum_code[0][4]
                x['ff_id'] = None
                x['ff_xform_id_string'] = None
                x['Household_number'] = str(int(x['Household_number']))

                if flag_fetch_ff:
                    if key in temp_FF_keys:
                        if '_id' in temp_FF[x['Household_number']].keys():
                            ff_id = temp_FF[x['Household_number']]['_id']
                            del (temp_FF[x['Household_number']]['_id'])
                        else:
                            ff_id = temp_FF[x['Household_number']]

                        x.update(temp_FF[x['Household_number']])
                        x['OnfieldFactsheet'] = 'Yes'
                        x['_id'] = temp
                        x['ff_id'] = ff_id

                    # Adding hyperlink for factsheet photos
                    if '_attachments' in x.keys() and len(x['_attachments']) != 0:
                        PATH = '/media/shelter/attachments/' + "/".join(x['_attachments'][0]["filename"].split('/')[2:-1])
                        if 'Toilet_Photo' in x.keys():
                            x.update({'toilet_photo_url': PATH + '/' + x['Toilet_Photo']})
                        if 'Family_Photo' in x.keys():
                            x.update({'family_photo_url': PATH + '/' + x['Family_Photo']})

                    else:
                        if 'Toilet_Photo' and 'ff_uuid' in x.keys():
                            ff_url = settings.AVNI_URL + '/#/app/subject/viewProgramEncounter?uuid=' + str(x['ff_uuid'])
                            x.update({'toilet_photo_url': ff_url if ff_url else x['Toilet_Photo']})
                            x.update({'family_photo_url': ff_url if ff_url else x['Family_Photo']})
                    # Adding hyperlink for factsheet
                    if 'ff_uuid' in x.keys():
                        x.update({'ff_url': settings.AVNI_URL + '/#/app/subject/viewProgramEncounter?uuid=' + str(x['ff_uuid'])})

                # Adding hyperlink for RHS Data
                # if 'rhs_uuid' in x.keys():
                #     x.update({'rhs_url': settings.AVNI_URL + '#/app/subject?uuid=' + str(x['rhs_uuid'])})
                
                # Update Follow up data for household
                if flag_fetch_rhs:
                    if str(int(key)) in followup_data:
                        if 'Type_of_structure_occupancy' in x and x['Type_of_structure_occupancy'] == 'Occupied house':
                            final_followup_data = followup_data[str(int(key))]
                            data = final_followup_data['followup_data']
                            if 'group_oi8ts04/Current_place_of_defecation' in data:
                                temp = data['group_oi8ts04/Current_place_of_defecation']
                                data['current place of defecation'] = temp
                            x.update(data)
                    # check status if status is Completed change CPD to Toilet by SA.
                    if 'status' in x and x['status'] == 'Completed':
                        x.update({'current place of defecation': 'Toilet by SA'})
                        x.update({'group_oi8ts04/Status_of_toilet_under_SBM': ''})
                        x.update({'group_oi8ts04/Which_Community_Toil_r_family_members_use': ''})

                if len(slum_funder) != 0:
                    for funder in slum_funder:
                        if funder.household_code != None:
                            if int(x['Household_number']) in funder.household_code:
                                x.update({'Funder': funder.sponsor_project.name})  # funder.sponsor.organization_name})

            formdict = list(map(lambda x: dummy_formdict[x], dummy_formdict))
            for x in formdict:
                try:
                    if ('current place of defecation' in x and x['current place of defecation'] in ['SBM (Installment)', 'Own toilet']) and ('agreement_date_str' in x and x['agreement_date_str'] and len(x['agreement_date_str']) > 1):
                        x['incorrect_cpod'] = 'incorrect_cpod'

                except Exception as e:
                    pass
    except Exception as e:
        print(e)
    return HttpResponse(json.dumps(formdict), content_type="application/json")


def to_date(s):
    if s != None:
        return datetime.datetime.strptime(s.strip(), "%Y-%m-%d").date()
    else:
        return None


def is_delayed(s):
    if (s and len(s) != 0):
        if (datetime.date.today() - to_date(s)).days > 8:
            return True
    else:
        return False


def trav(node):
    # Traverse up till the child node and add to list
    if 'type' in node and node['type'] == "group":
        return list(chain.from_iterable([trav(child) for child in node['children']]))
    elif (node['type'] == "select one" or node['type'] == "select all that apply") and 'children' in node.keys():
        return [node]
    return []


@apply_permissions_ajax('mastersheet.can_view_mastersheet')
def define_columns(request):
    """
    Method to send datatable columns.
    :param request:
    :return:
    """
    formdict_new = [
        {'data': 'a_missing', 'title': 'a_missing', 'bVisible': False},  # 0
        {'data': 'p1_missing', 'title': 'p1_missing', 'bVisible': False},
        {'data': 'p2_missing', 'title': 'p2_missing', 'bVisible': False},
        {'data': 'p3_missing', 'title': 'p3_missing', 'bVisible': False},  # 3

        {'data': 'a_amb', 'title': 'a_amb', 'bVisible': False},  # 4
        {'data': 'p1_amb', 'title': 'p1_amb', 'bVisible': False},  # 5
        {'data': 'p2_amb', 'title': 'p2_amb', 'bVisible': False},  # 6
        {'data': 'p3_amb', 'title': 'p3_amb', 'bVisible': False},  # 7
        {'data': 'c_amb', 'title': 'c_amb', 'bVisible': False},  # 8

        {"data": "delay_flag", "title": "delay_flag", "bVisible": False},  # 9
        {"data": "status", "title": "Dummy Status", "bVisible": False},  # 10
        {"data": "no_rhs_flag", "title": "no_rhs_flag", "bVisible": False},  # 11
        {"data": "material_shifts", "title": "Material Shifts", "bVisible": False},
        {"data": "incorrect_cpod", "title": "Incorrect CPoD", "bVisible": False},
        {"data": "slum__name", "title": "Slum Name", "bVisible": False},

        {"data": "Household_number", "title": "Household Number", "className": "add_hyperlink"},  # 1

        {"data": "Date_of_survey", "title": "Date of Survey"},
        {"data": "Name_s_of_the_surveyor_s", "title": "Name of the Surveyor"},
        {"data": "Type_of_structure_occupancy", "title": "Type of structure occupancy"},
        {"data": "Plus code of the house", "title": "Plus code of the house"},
        {"data": "Plus Code Part", "title": "Plus Code Part"},
        {"data": "Type_of_unoccupied_house", "title": "Type of unoccupied house"},  # 5
        {"data": "Parent_household_number", "title": "Parent household number"},
        {"data": "group_og5bx85/Full_name_of_the_head_of_the_household",
         "title": "Full name of the head of the household"},
        {"data": "group_og5bx85/Type_of_survey", "title": "Type of the survey"},
        {"data": "group_el9cl08/Enter_the_10_digit_mobile_number", "title": "Mobile number"},
        {"data": "group_el9cl08/Aadhar_number", "title": "Aadhar card number"},  # 10
        {"data": "group_el9cl08/Number_of_household_members", "title": "Number of household members"},
        {"data": "group_el9cl08/Do_you_have_any_girl_child_chi",
         "title": "Do you have any girl child/children under the age of 18?"},
        {"data": "group_el9cl08/How_many", "title": "How many?"},
        {"data": "group_el9cl08/Type_of_structure_of_the_house", "title": "Type of structure of the house"},
        {"data": "group_el9cl08/Ownership_status_of_the_house", "title": "Ownership status of the house"},  # 15
        {"data": "group_el9cl08/House_area_in_sq_ft", "title": "House area in sq. ft."},
        {"data": "group_el9cl08/Type_of_water_connection", "title": "Type of water connection"},
        {"data": "group_el9cl08/Facility_of_solid_waste_collection", "title": "Facility of solid waste management"},
        {"data": "group_el9cl08/Does_any_household_m_n_skills_given_below",
         "title": "Does any household member have any of the construction skills give below?"},

        {"data": "group_oi8ts04/Have_you_applied_for_individua",
         "title": "Have you applied for an individual toilet under SBM?"},  # 20
        {"data": "group_oi8ts04/How_many_installments_have_you", "title": "How many installments have you received?"},
        {"data": "group_oi8ts04/When_did_you_receive_ur_first_installment",
         "title": "When did you receive your first installment?"},
        {"data": "group_oi8ts04/When_did_you_receive_r_second_installment",
         "title": "When did you receive your second installment?"},
        {"data": "group_oi8ts04/When_did_you_receive_ur_third_installment",
         "title": "When did you receive your third installment?"},
        {"data": "group_oi8ts04/If_built_by_contract_ow_satisfied_are_you",
         "title": "If built by a contractor, how satisfied are you?"},  # 25
        {"data": "group_oi8ts04/Status_of_toilet_under_SBM", "title": "Status of toilet under SBM?"},
        {"data": "group_oi8ts04/What_was_the_cost_in_to_build_the_toilet",
         "title": "What was the cost incurred to build the toilet?"},
        {"data": "current place of defecation", "title": "Current place of defecation"},
        {"data": "group_oi8ts04/Which_Community_Toil_r_family_members_use", "title": "Which CTB"},  # 29

        {"data": "group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets",
         "title": "Is there availability of drainage to connect to the toilet?"},  # 30 new
        {"data": "group_oi8ts04/Are_you_interested_in_an_indiv",
         "title": "Are you interested in an individual toilet?"},  # 30
        {"data": "group_oi8ts04/What_kind_of_toilet_would_you_likes", "title": "What kind of toilet would you like?"},
        {"data": "group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built",
         "title": "Under what scheme would you like your toilet to be built?"},
        {"data": "group_oi8ts04/If_yes_why", "title": "If yes, why?"},
        {"data": "group_oi8ts04/If_no_why", "title": "If no, why?"},
        {"data": "group_oi8ts04/What_is_the_toilet_connected_to", "title": "What is the toilet connected to?"},  # 35
        {"data": "group_oi8ts04/Who_all_use_toilets_in_the_hou", "title": "Who all use toilets in the household?"},
        {"data": "group_oi8ts04/Reason_for_not_using_toilet", "title": "Reason for not using toilet"},

        {"data": "OnfieldFactsheet", "title": "Factsheet onfield"},
        {"data": "group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet",
         "title": "Have you upgraded your toilet/bathroom/house while constructing individual toilet?"},
        {"data": "group_ne3ao98/Cost_of_upgradation_in_Rs", "title": "House renovation cost"},  # 40
        {"data": "group_ne3ao98/Where_the_individual_ilet_is_connected_to",
         "title": "Where the individual toilet is connected to?"},
        {"data": "group_ne3ao98/Use_of_toilet", "title": "Use of toilet"},
        {"data": "family_photo_url", "title": "Family Photo"},
        {"data": "toilet_photo_url", "title": "Toilet Photo"},

        {"data": "name", "title": "SBM Applicant Name"},
        {"data": "application_id", "title": "Application ID"},  # 47
        {"data": "phone_number", "title": "Phone Number"},
        {"data": "aadhar_number", "title": "Aadhar Number"},
        {"data": "photo_uploaded", "title": "Is toilet photo uploaded on site?"},
        {"data": "photo_verified", "title": "Photo Verified"},
        {"data": "photo_approved", "title": "Photo Approved"},  # 52
        {"data": "application_verified", "title": "Application Verified"},
        {"data": "application_approved", "title": "Application Approved"},
        {"data": "sbm_comment", "title": "SBM Comment"},

        {"data": "agreement_date_str", "title": "Date of Agreement"},
        {"data": "agreement_cancelled", "title": "Agreement Cancelled?"},
        {"data": "septic_tank_date_str", "title": "Date of septic tank supplied"},  # 57
        {"data": "phase_one_material_date_str", "title": "Date of first phase material"},
        {"data": "phase_two_material_date_str", "title": "Date of second phase material"},
        {"data": "phase_three_material_date_str", "title": "Date of third phase material"},  # 60
        {"data": "completion_date_str", "title": "Construction Completion Date"},

        {"data": "p1_material_shifted_to", "title": "Phase one material shifted to"},  ##62
        {"data": "p2_material_shifted_to", "title": "Phase two material shifted to"},  ##63
        {"data": "p3_material_shifted_to", "title": "Phase three material shifted to"},  ##64
        {"data": "st_material_shifted_to", "title": "Septick tank shifted to"},  ##65
        {"data": "Funder", "title": "Funder (Project Name)"},  # 67#66
        {"data": "status", "title": "Final Status"},  ##67
        {"data": "pocket", "title": "Pocket"},
        {"data": "comment", "title": "Comment"},
        # Append community mobilization here #
        # Append vendor type here #
    ]
    number_of_invisible_columns = 0
    for i in formdict_new:
        if 'bVisible' in i.keys():
            number_of_invisible_columns += 1

    final_data = {}
    final_data['buttons'] = collections.OrderedDict()
    final_data['buttons']['RHS'] = list(range(number_of_invisible_columns + 1,
                                              number_of_invisible_columns + 1 + 20))  # range(14,34)#range(13,33)
    final_data['buttons']['Follow-up'] = list(range(number_of_invisible_columns + 1 + 20,
                                                    number_of_invisible_columns + 1 + 20 + 19))  # range(34,52)#range(33,51)
    final_data['buttons']['Family factsheet'] = list(range(number_of_invisible_columns + 1 + 20 + 19,
                                                           number_of_invisible_columns + 1 + 20 + 19 + 7))  # range(52,59)#range(51,58)
    final_data['buttons']['SBM'] = list(range(number_of_invisible_columns + 1 + 20 + 19 + 7,
                                              number_of_invisible_columns + 1 + 20 + 19 + 7 + 10))  # range(60,69)#range(58,68)
    final_data['buttons']['Construction status'] = list(range(number_of_invisible_columns + 1 + 20 + 19 + 7 + 10,
                                                              number_of_invisible_columns + 1 + 20 + 19 + 7 + 10 + 15))  # range(70,84)#range(68,83)
    # We define the columns for community mobilization and vendor details in a dynamic way. The
    # reason being these columns are prone to updates and additions.
    activity_pre_len = len(formdict_new)
    activity_type_model = ActivityType.objects.filter(display_flag=True).order_by('display_order')
    try:
        for i in range(len(activity_type_model)):
            formdict_new.append({"data": activity_type_model[i].name, "title": activity_type_model[i].name})
    except Exception as e:
        print(e)
    final_data['buttons']['Community Mobilization'] = list(range(activity_pre_len, len(formdict_new)))

    material_type_model = MaterialType.objects.filter(display_flag=True).order_by('display_order')
    vendor_pre_len = len(formdict_new)

    try:
        for i in material_type_model:
            formdict_new.append({"data": "invoice_number" + str(i.name), "title": str(i.name) + " Invoice Number"})
    except Exception as e:
        print(e)
    final_data['buttons']['Accounts'] = list(range(vendor_pre_len, len(formdict_new)))
    final_data['data'] = formdict_new
    return HttpResponse(json.dumps(final_data), content_type="application/json")


@permission_required('mastersheet.can_view_mastersheet', raise_exception=True)
def renderMastersheet(request):
    slum_search_field = find_slum()
    account_slum_search_field = account_find_slum()
    file_form1 = file_form()
    return render(request, 'masterSheet.html',
                  {'form': slum_search_field, 'form_account': account_slum_search_field, 'file_form': file_form1})


@csrf_exempt
@apply_permissions_ajax('mastersheet.can_upload_mastersheet')
def file_ops(request):
    slum_code = request.POST.get('slum_code')
    slum_search_field = find_slum()
    file_form1 = file_form()
    response = []
    resp = {}
    if request.method == "POST":
        try:
            resp = handle_uploaded_file(request.FILES.get('file'), response, slum_code)
            response = resp
        except Exception as e:
            response.append(('error msg', str(e)))
    return HttpResponse(json.dumps(response), content_type="application/json")


# Pandas libraries help us in handling DataFrames with convenience
# In the sheet that is being uploaded, the 'Agreement Cancelled' field should be blank if the agreement
# is not cancelled. If it has any entry, the agreement_cancelled field in the database will be set to
#  True
def handle_uploaded_file(f, response, slum_code):
    df = pandas.read_excel(f)

    flag_overall = 0

    try:

        df1 = df.set_index(str(list(df.columns.values)[0]))
        response.append(("total_records", len(df1.index.values)))
    except Exception as e:
        flag_overall = 1
        response.append(("Household number error", e))

        # We divide the dataframe into subframes for vendors, their invoices and community mobilization

    flag_accounts = 0
    flag_SBM = 0
    flag_ComMob = 0
    flag_TC = 0
    try:
        df_vendors = df1.filter(like='Vendor Name')
        df_invoice = df1.filter(like='Invoice')
    except:
        flag_accounts = 1

    try:
        df_ComMob = df1.loc[:, 'FGD with women':'Community Mobilization Ends']
    except:
        flag_ComMob = 1

    try:
        df_sbm = df1.loc[:, 'SBM Name':'SBM Comment']
    except:
        flag_SBM = 1

    try:
        df_TC = df1.loc[:, 'Date of Agreement':'Comment']
    except:
        flag_TC = 1

    # *******************************IMPORTANT!!!!*************************************
    # In the excel sheet that has been uploaded, it is imperative to have a column with
    # a header 'Community Mobilization Ends' right after the last mobilization activity's
    # column.This column will be blank. It will be used to slice a sub frame which will have
    # all the community mobilization activities.
    this_slum = Slum.objects.get(pk=slum_code)
    try:

        if flag_overall != 1:

            for i in df1.index.values:
                # this_slum = Slum.objects.get(name=str(df1.loc[int(i), 'Select Slum']))

                if flag_SBM != 1:
                    try:
                        SBM_instance = SBMUpload.objects.filter(slum=this_slum, household_number=int(i))

                        if len(SBM_instance) != 0:

                            SBM_instance.update(
                                name=df_sbm.loc[int(i), 'SBM Name'],
                                application_id=df_sbm.loc[int(i), 'Application ID'],
                                phone_number=df_sbm.loc[int(i), 'Phone Number'],
                                aadhar_number=df_sbm.loc[int(i), 'Aadhar Number'],
                                photo_uploaded=check_bool(df_sbm.loc[int(i), 'Toilet photo uploaded on SBM site']),
                                photo_verified=check_bool(df_sbm.loc[int(i), 'Toilet Photo Verified']),
                                photo_approved=check_bool(df_sbm.loc[int(i), 'Toilet Photo Approved']),
                                application_verified=check_bool(df_sbm.loc[int(i), 'Application Verified']),
                                application_approved=check_bool(df_sbm.loc[int(i), 'Application Approved']),
                                sbm_comment=df_sbm.loc[int(i), 'SBM Comment']
                            )
                            response.append(("updated sbm", int(i)))

                        else:
                            if True:
                                SBM_instance_1 = SBMUpload(
                                    slum=this_slum,
                                    household_number=int(i),
                                    name=df1.loc[int(i), 'SBM Name'],
                                    application_id=df_sbm.loc[int(i), 'Application ID'],
                                    phone_number=df_sbm.loc[int(i), 'Phone Number'],
                                    aadhar_number=df_sbm.loc[int(i), 'Aadhar Number'],
                                    photo_uploaded=check_bool(df_sbm.loc[int(i), 'Toilet photo uploaded on SBM site']),
                                    photo_verified=check_bool(df_sbm.loc[int(i), 'Toilet Photo Verified']),
                                    photo_approved=check_bool(df_sbm.loc[int(i), 'Toilet Photo Approved']),
                                    application_verified=check_bool(df_sbm.loc[int(i), 'Application Verified']),
                                    application_approved=check_bool(df_sbm.loc[int(i), 'Application Approved']),
                                    sbm_comment=df_sbm.loc[int(i), 'SBM Comment']

                                )
                                SBM_instance_1.save()
                                response.append(("newly created sbm", int(i)))
                    except Exception as e:
                        response.append(("The error says: " + str(
                            e) + ". This error is with SBM columns for following household numbers", int(i)))

                if flag_ComMob != 1:
                    for p, q in df_ComMob.loc[int(i)].items():

                        if check_null(q) is not None:
                            household_nums = []
                            try:
                                activityType_instance = ActivityType.objects.get(name=p)
                                if activityType_instance:
                                    try:

                                        ### IMPORTANT!!!!! Date should also be considered!!! INCOMPLETE!!!!!
                                        ComMob_instance = CommunityMobilization.objects.get(slum=this_slum,
                                                                                            activity_type=activityType_instance)

                                        temp = ComMob_instance.household_number
                                        if int(i) not in temp:
                                            temp.append(int(i))
                                            response.append(("updated ComMob", int(i)))
                                        ComMob_instance.household_number = temp
                                        ComMob_instance.save()

                                    except Exception as e:
                                        household_nums.append(int(i))
                                        CM_instance = CommunityMobilization(
                                            slum=this_slum,
                                            household_number=household_nums,
                                            activity_type=activityType_instance,
                                            activity_date=df_ComMob.loc[int(i), p]
                                        )
                                        CM_instance.save()
                                        response.append(("newly created ComMob", int(i)))
                            except Exception as e:
                                response.append(("The error says: " + str(
                                    e) + ". This error is in Commuinity Mobilization columns for " + p + ", for the following household numbers", int(i)))
                if flag_accounts != 1:
                    for j, m in df_vendors.loc[int(i)].items():
                        if check_null(m) is not None:
                            household_nums = []
                            k = df_vendors.columns.get_loc(j)
                            string = unicode(df_invoice.loc[int(i)][k])
                            try:
                                Vendor_instance = Vendor.objects.get(name=str(m))
                                if Vendor_instance:
                                    try:
                                        VHID_instance_1 = VendorHouseholdInvoiceDetail.objects.get(
                                            vendor=Vendor_instance,
                                            invoice_number=string.split('/')[0],
                                            slum=this_slum)
                                        temp = VHID_instance_1.household_number
                                        if int(i) not in temp:
                                            temp.append(int(i))
                                            response.append(("updated VHID", int(i)))
                                        VHID_instance_1.household_number = temp
                                        VHID_instance_1.save()
                                    except Exception as e:
                                        print(e)
                                        household_nums.append(int(i))
                                        VHID_instance = VendorHouseholdInvoiceDetail(
                                            vendor=Vendor.objects.get(name=str(m)),
                                            slum=this_slum,
                                            invoice_number=string.split('/')[0],
                                            invoice_date=datetime.datetime.strptime(string.split('/')[1], '%d.%m.%Y'),
                                            household_number=household_nums
                                        )
                                        VHID_instance.save()
                                        response.append(("newly created VHID", int(i)))
                            except Exception as e:
                                response.append(("The error says: " + str(
                                    e) + ". This error is in Vendor Invoice Details Columns for " + m + ", for the following household numbers", int(i)))
                if flag_TC != 1:
                    try:
                        TC_instance = ToiletConstruction.objects.select_related().filter(household_number=int(i), slum__name=this_slum)
                        if TC_instance:
                            try:
                                TC_instance[0].update_model(df_TC.loc[int(i), :])
                            except Exception as e:
                                print(e)
                            response.append(("updated TC", int(i)))

                        else:
                            this_status = " "
                            stat = df_TC.loc[int(i), 'Final Status']
                            for j in range(len(STATUS_CHOICES)):
                                if str(STATUS_CHOICES[j][1]).lower() == str(
                                        stat).lower():  # STATUS_CHOICE is imported from mastersheet/models.py
                                    this_status = STATUS_CHOICES[j][0]

                            TC_instance = ToiletConstruction(
                                slum=this_slum,
                                agreement_date=check_null(df_TC.loc[int(i), 'Date of Agreement']),
                                agreement_cancelled=check_bool(df_TC.loc[int(i), 'Agreement Cancelled']),
                                household_number=int(i),
                                septic_tank_date=check_null(df_TC.loc[int(i), 'Date of Septic Tank supplied']),
                                phase_one_material_date=check_null(df_TC.loc[int(i), 'Material Supply Date 1st']),
                                phase_two_material_date=check_null(df_TC.loc[int(i), 'Material Supply Date-2nd']),
                                phase_three_material_date=check_null(df_TC.loc[int(i), 'Material Supply Date-3rd']),
                                completion_date=check_null(df_TC.loc[int(i), 'Construction Completion Date']),
                                comment=check_null(df_TC.loc[int(i), 'Comment']),
                                pocket=check_null(df_TC.loc[int(i), 'Pocket']),
                                status=this_status
                            )

                            TC_instance.save()
                            response.append(("newly created TC", int(i)))
                    except Exception as e:
                        response.append(("The error says: " + str(
                            e) + ". This error is with Toilet Construction Columns for following household numbers", int(i)))

        else:
            response.append(("The error says: ",
                             "This is an overall error. Please check the uploaded Excle sheet for column names, slum names etc."))


    except Exception as e:
        response.append(("The error says: " + str(e),
                         "This is an overall error. Please check the uploaded Excle sheet for column names, slum names etc."))
    d = defaultdict(list)
    for k, v in response:
        d[k].append(v)
    return d


def check_null(s):
    if pandas.isnull(s):
        return None
    else:
        return s


def check_bool(s):
    if str(s).lower() == 'yes' or str(s).lower() == "true":
        return True
    else:
        return False


@csrf_exempt
@apply_permissions_ajax('mastersheet.can_delete_kobo_record')
def delete_selected(request):
    """
     Method to delete selected records.
    :param request:
    :return:
    """
    slum_search_field = find_slum()
    file_form1 = file_form()
    response = {}
    response['response'] = "Records deleted successfully"

    records = json.loads(request.body)
    delete_selected_records(records)

    return HttpResponse(json.dumps(response), content_type="application/json")


def delete_selected_records(records):
    """
    Method to delete selected records. CALLED from delete_selected
    :param records:
    :return:
    """
    kobo_form = 130  # *****IMPORTANT***** This form number (98) is for local setting. Do change it to 130 before going live.
    delimiter = 'slumname='
    slum_code = Slum.objects.get(pk=records['slum'])
    form_ids = Survey.objects.filter(city=slum_code.electoral_ward.administrative_ward.city,
                                     survey_type=SURVEYTYPE_CHOICES[1][0])
    if len(form_ids) > 0:
        kobo_form = form_ids[0].kobotool_survey_id
    headers = {}
    headers["Authorization"] = settings.KOBOCAT_TOKEN
    for r in records['records']:
        try:
            if r:
                deleteURL = '/'.join([settings.KOBOCAT_FORM_URL[:-1], 'data', str(kobo_form), str(r)])
                objresponseDeleted = requests.delete(deleteURL, headers=headers)
                print(' deleted for ' + str(r) + ' with response ' + str(objresponseDeleted))
        except Exception as e:
            print("No record selected to delete.")


@apply_permissions_ajax('mastersheet.can_sync_toilet_status')
@deco_city_permission
def sync_kobo_data(request):
    """
    Method to sync data from kobotoolbox for community mobilization and toilet construction status(Daily reporting)
    :param request:
    :param slum_id:
    :return: success/error msg
    """ 
    data = {}
    try:
        slum = Slum.objects.get(id=request.GET['slumname'])
        ''' Calling a method sync_rim_data() of avni_sync class to sync Slum-RIM data of the given slum.
            Argument => slum_id
            Return => Number of Forms synced.
        '''
        sync_obj = avni_sync()
        slum_in_avni_flag, rim_sync_num = sync_obj.sync_rim_data(slum.id)
        toilet_sync_num = sync_obj.sync_toilet_data(slum.id)
        data['flag'] = True
        if not (slum_in_avni_flag):
            data['msg'] = "The Avni UUID mapping is not available for this slum." + slum.name +"\n Please contact administrator."
        else:
            if rim_sync_num > 0:
                data['msg'] = "Rim Data successfully synced for slum - " + slum.name
                data['msg'] += "\nTotal records updated : " + str(rim_sync_num)
            else:
                data['msg'] = "There is no records available to sync RIM data for - " + slum.name
                data['msg'] += "\nTotal records updated : " + str(rim_sync_num)
            if toilet_sync_num > 0:
                data['msg'] += "\n Toilet Data successfully synced for slum - " + slum.name
                data['msg'] += "\nTotal records updated : " + str(toilet_sync_num)
            else:
                data['msg'] += "\n There is no records available to sync CTB data for slum - " + slum.name
                data['msg'] += "\nTotal records updated : " + str(toilet_sync_num)
    except Exception as e:
        data['flag'] = False
        data['msg'] = "Error occurred while sync from kobo. Please contact administrator." + str(e)
    return HttpResponse(json.dumps(data), content_type="application/json")

''' Mastersheet Report Tab '''
@permission_required('mastersheet.can_view_mastersheet_report', raise_exception=True)
def render_report(request):
    return render(request, 'mastersheet_report.html')


@apply_permissions_ajax('mastersheet.can_view_mastersheet_report')
def create_report(request):
    '''
        This view generates source structure for the fancy tree used in the report.
    '''
    electoral_wards_dict = {}
    admin_wards_dict = {}
    fancy_tree_data = []
    group_perm = request.user.groups.values_list('name', flat=True)
    if request.user.is_superuser:
        group_perm = Group.objects.all().values_list('name', flat=True)
    group_perm = map(lambda x: x.split(':')[-1], group_perm)

    cities = City.objects.filter(name__city_name__in=group_perm).values('id', 'name__city_name')
    for i in cities:
        temp = {}
        temp['name'] = i['name__city_name']
        temp['id'] = i['id']
        temp['children'] = list(AdministrativeWard.objects.filter(city=i['id']).values('id', 'name'))
        temp['tag'] = 'city'
        for j in temp['children']:
            j['tag'] = 'admin_ward'
            j['children'] = list(ElectoralWard.objects.filter(administrative_ward=j['id']).values('id', 'name'))
            for k in j['children']:
                k['tag'] = 'electoral_ward'
                k['children'] = list(Slum.objects.filter(electoral_ward=k['id']).values('id', 'name'))
        fancy_tree_data.append(temp)
    return HttpResponse(json.dumps(fancy_tree_data), content_type="application/json")

''' This is for quearing data level wise when we are using report tab methods'''
level_data = {
        'city':
            {
                'city_name': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level_id': F('slum__electoral_ward__administrative_ward__city__id')
            },
        'admin_ward':
            {
                'city_name': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level': F('slum__electoral_ward__administrative_ward__name'),
                'level_id': F('slum__electoral_ward__administrative_ward__id')
            },
        'electoral_ward':
            {
                'city_name': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level': F('slum__electoral_ward__name'),
                'level_id': F('slum__electoral_ward__id')
            },
        'slum':
            {
                'city_name': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level': F('slum__name'),
                'level_id': F('slum__id')
            }
    }

''' Mastersheet Report Tab Methods'''
@csrf_exempt
@apply_permissions_ajax('mastersheet.can_view_mastersheet_report')
def give_report_table_numbers(request):  # view for toilet construction
    tag_key_dict = json.loads(request.body)
    tag = tag_key_dict['tag']
    keys = tag_key_dict['keys']
    group_perm = request.user.groups.values_list('name', flat=True)
    if request.user.is_superuser:
        group_perm = Group.objects.all().values_list('name', flat=True)
    group_perm = map(lambda x: x.split(':')[-1], group_perm)

    keys = Slum.objects.filter(id__in=keys,
                               electoral_ward__administrative_ward__city__name__city_name__in=group_perm).values_list(
        'id', flat=True)
    start_date = tag_key_dict['startDate']
    end_date = tag_key_dict['endDate']
    if start_date == None or end_date == None:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(tag_key_dict['startDate'], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(tag_key_dict['endDate'], "%Y-%m-%d").date()

    query_on = {'agreement_date': 'total_ad', 'phase_one_material_date': 'total_p1',
                'phase_two_material_date': 'total_p2', 'phase_three_material_date': 'total_p3',
                'completion_date': 'total_c', 'septic_tank_date': 'total_st',
                'use_of_toilet': 'use_of_toilet', 'toilet_connected_to': 'toilet_connected_to',
                'factsheet_done': 'factsheet_done'}
    
    '''Report table data object for response'''
    report_table_data = defaultdict(dict)
    for query_field in query_on.keys():
        if query_field in ['agreement_date', 'phase_one_material_date', 'phase_two_material_date',
                           'phase_three_material_date',
                           'completion_date', 'septic_tank_date', 'use_of_toilet', 'toilet_connected_to',
                           'factsheet_done']:
            filter_field = {'slum__id__in': keys, 'phase_one_material_date__range': [start_date, end_date],
                            query_field + '__isnull': False}
        else:
            filter_field = {'slum__id__in': keys, query_field + '__range': [start_date, end_date]}
        count_field = {query_on[query_field]: Count('level_id')}
        tc = ToiletConstruction.objects.filter(**filter_field) \
            .exclude(Q(agreement_cancelled=True)| Q(status = '7')) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
            .annotate(**count_field).order_by('city_name')
        tc = {obj_ad['level_id']: obj_ad for obj_ad in tc}
        filter_field = {'slum__id__in': keys, 'phase_one_material_date__range': [start_date, end_date]}

        for level_id, data in tc.items():
            report_table_data[level_id].update(data)

        '''Here we are checking the write off cases ...'''
        if query_field == 'factsheet_done':
            count_field = {'status': Count('level_id')}
            filter_field = {'slum__id__in': keys, 'phase_one_material_date__range': [start_date, end_date], 'status' : '7'}
            toilet_data = ToiletConstruction.objects.filter(**filter_field).exclude(agreement_cancelled=True).annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
                .annotate(**count_field).order_by('city_name')
            toilet_data = {obj_ad['level_id']: obj_ad for obj_ad in toilet_data}
            for level_id, data in toilet_data.items():
                report_table_data[level_id].update({'write_off_cases':data['status']})
        level_data_tag = {
                'city':
                    {
                        'level_id': 'slum__electoral_ward__administrative_ward__city__id'
                    },
                'admin_ward':
                    {
                        'level_id': 'slum__electoral_ward__administrative_ward__id'
                    },
                'electoral_ward':
                    {
                        'level_id': 'slum__electoral_ward__id'
                    },
                'slum':
                    {
                        'level_id': 'slum__id'
                    }
                }
        ''' For Factsheet Assign Check '''
        if query_field == 'factsheet_done':
            for t in tc:
                l = tc[t]['level_id']
                '''Assigning Initla count as 0 for every level.'''
                report_table_data[l]['factAssign'] = 0
                '''Query filter for toilet construction data'''
                query_field_TC = {level_data_tag[tag]['level_id'] : l, 'phase_one_material_date__range':[start_date, end_date], 'factsheet_done__isnull' : False}
                '''Query filter for Sponsor data'''
                query_field_sponsor = {level_data_tag[tag]['level_id'] : l,}
                T_Housenum = ToiletConstruction.objects.filter(**query_field_TC).values_list('household_number', 'slum_id')
                Spsr_Housecode = SponsorProjectDetails.objects.filter(**query_field_sponsor).exclude(sponsor__id=10).values_list('household_code', 'slum_id')
                '''Here we are cheching that the funder assign or not to the household.'''
                # Creating dict object of sponsor hh data.
                Spnsr_data_with_hh = {}
                for households, slum in Spsr_Housecode:
                    if slum not in Spnsr_data_with_hh:
                        Spnsr_data_with_hh[slum] = households
                    else:
                        temp_spsr_obj = Spnsr_data_with_hh[slum]
                        temp_spsr_obj.extend(households)
                
                # Loop for checking hh have toilet data and sponsor data.
                FactsheetAssign = 0
                for query_obj in T_Housenum:
                    household, slum = query_obj
                    if slum in Spnsr_data_with_hh:
                        temp_spsr_obj = Spnsr_data_with_hh[slum]
                        if int(household) in temp_spsr_obj:
                            FactsheetAssign += 1
                    
                report_table_data[l]['factAssign'] = FactsheetAssign
                
    '''Query filter for the total houses which have rhs data...'''
    for query_key in report_table_data.keys():
        query_field = {level_data_tag[tag]['level_id'] : query_key, 'rhs_data__isnull':False}
        h = HouseholdData.objects.filter(**query_field)
        report_table_data[query_key]['total_structure'] = h.count()
    return HttpResponse(json.dumps(list(map(lambda x: report_table_data[x], report_table_data))), content_type="application/json")


@csrf_exempt
def report_table_cm(request):
    tag_key_dict = json.loads(request.body)
    tag = tag_key_dict['tag']
    keys = tag_key_dict['keys']
    group_perm = request.user.groups.values_list('name', flat=True)
    if request.user.is_superuser:
        group_perm = Group.objects.all().values_list('name', flat=True)
    group_perm = map(lambda x: x.split(':')[-1], group_perm)

    keys = Slum.objects.filter(id__in=keys,
                               electoral_ward__administrative_ward__city__name__city_name__in=group_perm).values_list(
        'id', flat=True)

    start_date = tag_key_dict['startDate']
    end_date = tag_key_dict['endDate']

    if start_date == None or end_date == None:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(tag_key_dict['startDate'], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(tag_key_dict['endDate'], "%Y-%m-%d").date()
    '''Report table data object for response'''
    report_table_data_cm = defaultdict(dict)
    activity_type = ActivityType.objects.all()
    for x in activity_type:
        key_for_datatable = "total_" + (x.name).replace(" ", "")
        filter_field = {'slum__id__in': keys, 'activity_date__range': [start_date, end_date]}
        filter_field_new = {'slum_id__in': keys, 'date_of_activity__range': [start_date, end_date]}
        count_field = {key_for_datatable: ArrayAgg('household_number')}
        count_field1 = {key_for_datatable: Count('household_number')}

        y = x.communitymobilization_set.filter(**filter_field) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
            .annotate(**count_field).order_by('city_name')

        yy = x.communitymobilizationactivityattendance_set.filter(**filter_field_new) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
            .annotate(**count_field1).order_by('city_name')

        for data in yy:

            level_id = data['level_id']
            if str(level_id) in report_table_data_cm.keys() and key_for_datatable in report_table_data_cm[
                str(level_id)].keys():
                report_table_data_cm[str(level_id)][key_for_datatable] += data[key_for_datatable]
            else:
                report_table_data_cm[str(level_id)].update(data)

        for data in y:
            cnt = []
            for i in data[key_for_datatable]:
                if i:
                    cnt += i

            level_id = data['level_id']
            if str(level_id) in report_table_data_cm.keys() and key_for_datatable in report_table_data_cm[
                str(level_id)].keys():
                report_table_data_cm[str(level_id)][key_for_datatable] += len(cnt)
            else:
                data[key_for_datatable] = len(cnt)
                report_table_data_cm[str(level_id)].update(data)

    return HttpResponse(json.dumps(list(map(lambda x: report_table_data_cm[x], report_table_data_cm))),
                        content_type="application/json")


@csrf_exempt
def report_table_cm_activity_count(request):
    tag_key_dict = json.loads(request.body)
    tag = tag_key_dict['tag']
    keys = tag_key_dict['keys']
    group_perm = request.user.groups.values_list('name', flat=True)
    if request.user.is_superuser:
        group_perm = Group.objects.all().values_list('name', flat=True)
    group_perm = map(lambda x: x.split(':')[-1], group_perm)

    keys = Slum.objects.filter(id__in=keys,
                               electoral_ward__administrative_ward__city__name__city_name__in=group_perm).values_list(
        'id', flat=True)

    start_date = tag_key_dict['startDate']
    end_date = tag_key_dict['endDate']

    if start_date == None or end_date == None:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(tag_key_dict['startDate'], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(tag_key_dict['endDate'], "%Y-%m-%d").date()
    report_table_data_cm_activity_count = defaultdict(dict)
    activity_type = ActivityType.objects.all()

    for x in activity_type:
        key_for_datatable = "total_" + (x.name).replace(" ", "")
        filter_field = {'slum__id__in': keys, 'activity_date__range': [start_date, end_date]}
        filter_field_new = {'slum_id__in': keys, 'date_of_activity__range': [start_date, end_date]}
        count_field = {key_for_datatable: Count('activity_type')}

        y = x.communitymobilization_set.filter(**filter_field) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
            .annotate(**count_field).order_by('city_name')

        yy = x.communitymobilizationactivityattendance_set.filter(**filter_field_new) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
            .annotate(**count_field).order_by('city_name', 'date_of_activity')

        for data in y:
            level_id = data['level_id']
            if str(level_id) in report_table_data_cm_activity_count.keys() and key_for_datatable in \
                    report_table_data_cm_activity_count[str(level_id)].keys():
                report_table_data_cm_activity_count[str(level_id)][key_for_datatable] += data[key_for_datatable]
            else:
                report_table_data_cm_activity_count[str(level_id)].update(data)

        for data in yy:
            level_id = data['level_id']
            if str(level_id) in report_table_data_cm_activity_count.keys() and key_for_datatable in \
                    report_table_data_cm_activity_count[str(level_id)].keys():
                report_table_data_cm_activity_count[str(level_id)][key_for_datatable] += 1
            else:
                data[key_for_datatable] = 1
                report_table_data_cm_activity_count[str(level_id)].update(data)

    return HttpResponse(
        json.dumps(list(map(lambda x: report_table_data_cm_activity_count[x], report_table_data_cm_activity_count))),
        content_type="application/json")


@csrf_exempt
def give_report_table_numbers_accounts(request):
    tag_key_dict = json.loads(request.body)
    tag = tag_key_dict['tag']
    keys = tag_key_dict['keys']
    group_perm = request.user.groups.values_list('name', flat=True)
    if request.user.is_superuser:
        group_perm = Group.objects.all().values_list('name', flat=True)
    group_perm = map(lambda x: x.split(':')[-1], group_perm)
    keys = Slum.objects.filter(id__in=keys,
                               electoral_ward__administrative_ward__city__name__city_name__in=group_perm).values_list(
        'id', flat=True)

    start_date = tag_key_dict['startDate']
    end_date = tag_key_dict['endDate']

    if start_date == None or end_date == None:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(tag_key_dict['startDate'], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(tag_key_dict['endDate'], "%Y-%m-%d").date()
    '''For Daily reporting data count'''
    query_on = {'phase_one_material_date': 'total_date_phase_1',
                'phase_two_material_date': 'total_date_phase_2',
                'phase_three_material_date': 'total_date_phase_3',
                }
    report_table_accounts_data = defaultdict(dict)
    for query_field in query_on.keys():
        filter_field = {'slum__id__in': keys, 'phase_one_material_date' + '__range': [start_date, end_date], query_field + '__isnull': False}
        count_field = {query_on[query_field]: Count('level_id')}
        tc = ToiletConstruction.objects.filter(**filter_field) \
            .exclude(agreement_cancelled=True) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
            .annotate(**count_field).order_by('city_name')
        tc = {obj_ad['level_id']: obj_ad for obj_ad in tc}
        for level_id, data in tc.items():
            report_table_accounts_data[level_id].update(data)
    ''' Filter field for Invoice data'''
    filter_field = {'slum__id__in': keys, 'invoice__invoice_date__range': [start_date, end_date]}
    invoiceItems = InvoiceItems.objects.filter(**filter_field) \
        .annotate(**level_data[tag]).values('level', 'level_id', 'city_name', 'phase', 'household_numbers', 'slum_id',
                                            'material_type__name').order_by('city_name')
    ''' Creating Group by objects using level_id.'''
    invoiceItems = itertools.groupby(sorted(invoiceItems, key=lambda x: x['level_id']), key=lambda x: x['level_id'])
    ''' Iterating level wise and counting distinct household numbers (phase wise)'''
    for level, level_wise_list in invoiceItems:
        ''' Creating Group by objects Phase wise.'''
        phasewise = itertools.groupby(sorted(level_wise_list, key=lambda x: x['phase']), key=lambda x: x['phase'])
        level_name = None
        city_name = None
        phase_wise_material_cnt = {}  # Here we are checking slum wise households count for each phase.
        for phase, phasewisedata in phasewise:
            slum_wise_acc_data = {}  # here we are checking slum wise households count.
            for record in phasewisedata:
                level_name = record['level']
                city_name = record['city_name']
                if record['slum_id'] in slum_wise_acc_data:
                    temp = slum_wise_acc_data[record['slum_id']]
                    temp.extend(record['household_numbers'])
                    slum_wise_acc_data[record['slum_id']] = list(set(temp))
                else:
                    slum_wise_acc_data[record['slum_id']] = record['household_numbers']
            phasecnt = sum(list(map(len, slum_wise_acc_data.values())))  # Generating total count of households phase wise
            phase_wise_material_cnt["total_material_phase_" + str(phase)] = phasecnt
        phase_wise_material_cnt.update({'level':level_name, 'level_id':level, 'city_name':city_name})  # Adding Level details and citu names for cases where we have accounts data but not daily reporting.
        report_table_accounts_data[level].update(phase_wise_material_cnt)   # adding this count into final response data level wise.
    return HttpResponse(json.dumps(list(map(lambda x: report_table_accounts_data[x], report_table_accounts_data))),
                        content_type="application/json")


'''This function is for removing invalid characters from strings'''
def remove_invalid_char(fname):
    invalid_char = '''@$%&\/:*?"'<>|~`#^+={}[];!,.'''
    final_str = ""
    for char1 in fname:
        if char1 not in invalid_char:
            final_str += char1
    return final_str

@user_passes_test(lambda u: u.groups.filter(name="Account").exists() or u.is_superuser)
def accounts_excel_generation(request):
    account_form = account_find_slum(request.POST)
    city_id = request.POST.get('account_cityname')
    slum_id = request.POST.get('account_slumname')
    if len(request.POST.get('account_start_date')) == 0 or len(request.POST.get('account_end_date')) == 0:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(request.POST.get('account_start_date'), "%d-%m-%Y").date()
        end_date = datetime.datetime.strptime(request.POST.get('account_end_date'), "%d-%m-%Y").date()
    '''For adding date as a postfix in filename'''
    filename_date_ext = "_" + str(start_date) + '_' + str(end_date)
    wb = Workbook()
    sheet1 = wb.add_sheet('Sheet1')
    sheet1.write(0, 0, 'Date')
    sheet1.write(0, 1, 'Invoice No')
    sheet1.write(0, 2, 'Name of Vendor')
    sheet1.write(0, 3, 'Donar Name')
    sheet1.write(0, 4, 'City')
    sheet1.write(0, 5, 'Slum')
    sheet1.write(0, 6, 'House No')
    sheet1.write(0, 7, 'Phase I')
    sheet1.write(0, 8, 'Phase II')
    sheet1.write(0, 9, 'Phase III')
    sheet1.write(0, 10, 'Type of Material')
    sheet1.write(0, 11, 'Quantity')
    sheet1.write(0, 12, 'Rate')
    sheet1.write(0, 13, 'Gross Amount')
    sheet1.write(0, 14, 'Tax Rate')
    sheet1.write(0, 15, 'Tax Amount')
    sheet1.write(0, 16, 'Transport Charges')
    sheet1.write(0, 17, 'Unloading Charges')
    sheet1.write(0, 18, 'Amount')
    sheet1.write(0, 19, 'Toilet Record In MasterSheet')

    if len(city_id) == 0:
        invoiceItems = InvoiceItems.objects.filter(slum__id=int(slum_id),
                                                   invoice__invoice_date__range=[start_date, end_date])
        fname = remove_invalid_char(str(Slum.objects.get(id=int(slum_id)))) + filename_date_ext + '.xls'
        sponsor = SponsorProjectDetails.objects.filter(slum__id=int(slum_id)).exclude(sponsor_project=1)
        Toilet = ToiletConstruction.objects.filter(slum__id=int(slum_id)).exclude(agreement_cancelled = True).values_list('slum_id', 'household_number', 'phase_one_material_date', 'phase_two_material_date', 'phase_three_material_date')
    else:
        invoiceItems = InvoiceItems.objects.filter(slum__electoral_ward__administrative_ward__city__id=int(city_id),
                                                   invoice__invoice_date__range=[start_date, end_date])
        fname = str(City.objects.get(id=int(city_id))) + filename_date_ext + '.xls'
        sponsor = SponsorProjectDetails.objects.filter(slum__electoral_ward__administrative_ward__city__id=int(city_id)).exclude(sponsor_project=1)
        Toilet = ToiletConstruction.objects.filter(slum__electoral_ward__administrative_ward__city__id=int(city_id)).exclude(agreement_cancelled = True).values_list('slum_id', 'household_number', 'phase_one_material_date', 'phase_two_material_date', 'phase_three_material_date')
    
    dict_of_dict = defaultdict(dict)
    sponsor_with_slum = {}
    toiletData = {}
    for i in sponsor:
        slum = i.slum_id
        if slum not in sponsor_with_slum:
            sponsor_with_slum[slum] = [(i.sponsor_project.name, i.household_code)]
        else:
            temp_data = sponsor_with_slum[slum]
            temp_data.append((i.sponsor_project.name, i.household_code))
            sponsor_with_slum[slum] = temp_data

    for i in Toilet:
        (slum, household, phaseOne, phaseTwo, phaseThree) = i
        if phaseOne or phaseTwo or phaseThree:
            if slum not in toiletData:
                toiletData[slum] = [household]
            else:
                temp = toiletData[slum]
                temp.append(household)
                toiletData[slum] = temp

    def check_funder(house, slum):
        try:
            if slum in sponsor_with_slum:
                sponsor_with_slum_lst = sponsor_with_slum[slum]
                for i in sponsor_with_slum_lst:
                    if house in i[1]:
                        return i[0]
                return "Funder Not Assign"
            return "No Funder For This Slum"
        except Exception as e:
            print(e, house, slum)
    def check_toilet_data(house, slum):
        try:
            if slum in toiletData:
                if str(house) in toiletData[slum]:
                    return "Toilet Record Found"
            return "Toilet Record Not Found"
        except Exception as e:
            print(e, house, slum)

    for i in invoiceItems:
        for j in i.household_numbers:
            try:
                dict_of_dict[(j, i.slum)].update({i.material_type: i})
            except:
                dict_of_dict[(j, i.slum)] = {i.material_type: i}
    i = 1
    for k, v in dict_of_dict.items():
        for inner_k, inner_v in v.items():
            sheet1.write(i, 0, str(inner_v.invoice.invoice_date))
            sheet1.write(i, 1, inner_v.invoice.invoice_number)
            sheet1.write(i, 2, inner_v.invoice.vendor.name)
            sheet1.write(i, 3, check_funder(k[0], inner_v.slum.id))
            sheet1.write(i, 4, inner_v.slum.electoral_ward.administrative_ward.city.name.city_name)
            sheet1.write(i, 5, inner_v.slum.name)
            sheet1.write(i, 6, k[0])
            if inner_v.phase == '1':
                sheet1.write(i, 7, 'Phase - I')
            if inner_v.phase == '2':
                sheet1.write(i, 8, 'Phase - II')
            if inner_v.phase == '3':
                sheet1.write(i, 9, 'Phase - III')

            sheet1.write(i, 10, inner_k.name)
            sheet1.write(i, 11, inner_v.quantity)
            sheet1.write(i, 12, inner_v.rate)
            sheet1.write(i, 13, inner_v.quantity * inner_v.rate)
            sheet1.write(i, 14, inner_v.tax)
            sheet1.write(i, 15, round((float(inner_v.tax) / 100) * float(inner_v.quantity) * float(inner_v.rate), 2))
            tc = 0
            luc = 0
            total_hh = 1
            if inner_v.invoice.transport_charges != 0:
                total_hh = 0
                for x in inner_v.invoice.invoiceitems_set.all():
                    total_hh += len(x.household_numbers)
                tc = inner_v.invoice.transport_charges / total_hh
            if inner_v.invoice.loading_unloading_charges != 0:
                total_hh = 0
                for x in inner_v.invoice.invoiceitems_set.all():
                    total_hh += len(x.household_numbers)
                tc = inner_v.invoice.transport_charges / total_hh
            sheet1.write(i, 16, round(tc, 2))
            sheet1.write(i, 17, round(luc, 2))
            sheet1.write(i, 18, round(inner_v.total / len(inner_v.household_numbers) + tc + luc, 2))
            sheet1.write(i, 19, check_toilet_data(k[0], inner_v.slum.id))
            i = i + 1
    response = HttpResponse(content_type="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=%s' % str(fname).replace(' ', '_')
    wb.save(response)
    return response


# For Mastersheet Summery View rendering mastersheet summery page
@permission_required('mastersheet.can_view_mastersheet', raise_exception=True)
def renderSummery(request):
    slum_search_field = find_slum()
    gis_field = gis_tab()
    return render(request, 'mastersheet_summery.html', {'form': slum_search_field, 'form_gis': gis_field})



def getRhsData(record):
    key_list = {'Plus code of the house': 'pluscodes', 'Type_of_structure_occupancy': 'occupancy_status', 
    'group_og5bx85/Full_name_of_the_head_of_the_household': 'name_head_of_he_household', 'group_el9cl08/Ownership_status_of_the_house': 'ownership_status', 
    'group_oi8ts04/Current_place_of_defecation': 'current_place_of_defication', 'Plus Code Part':'pluscodepart', 'group_el9cl08/Do_you_have_any_girl_child_chi':'girls_child', 
    'group_el9cl08/Type_of_structure_of_the_house':'house_structure', 'group_el9cl08/Ownership_status_of_the_house':'ownership_status', 
    'group_el9cl08/House_area_in_sq_ft':'house_area', 'Do you have addhar card?':'isAadharCard', 'group_el9cl08/Aadhar_number':
	'aadhar_number', 'Colour of ration card':'color_of_ration_card',
    'group_el9cl08/Type_of_water_connection':'Type_of_water_connection', 'group_el9cl08/Facility_of_solid_waste_collection':"Facility_of_solid_waste_collection"}
    if record.rhs_data and record.rhs_data['Type_of_structure_occupancy'] == 'Occupied house':
        data = {key_list[i] : record.rhs_data[i] for i in key_list.keys() if i in record.rhs_data}
        if 'Type_of_water_connection' in data and data['Type_of_water_connection'] == 'Individual connection':
            data["Do you have individual water connection at home?"] = 'Yes'
        else:
            data["Do you have individual water connection at home?"] = 'No'
        data['household_number'] = record.household_number
    else:
        key_list = {'Plus code of the house': 'pluscodes', 'Type_of_structure_occupancy': 'occupancy_status', 'Type_of_unoccupied_house':'typeUnoccupiedHouse'}
        data = {key_list[i] : record.rhs_data[i] for i in key_list.keys() if i in record.rhs_data}
        data['household_number'] = record.household_number
    if record.ff_data:
        factsheet_keys = {'group_ne3ao98/Cost_of_upgradation_in_Rs': 'Cost of upgradation', 'group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet': 'Have you upgraded your toilet/bathroom/house while constructing individual toilet?', 'group_oh4zf84/Name_of_the_family_head': 'family_factsheet_name', 'group_ne3ao98/Where_the_individual_ilet_is_connected_to': 'toilet_connected_to'}
        for fact_key in factsheet_keys:
            if fact_key in record.ff_data:
                data[factsheet_keys[fact_key]] = record.ff_data[fact_key]
        data['factsheet_done'] = 'Yes'
    data['slum'] = slum_code[0][1]
    data['city_name'] = slum_code[0][2]
    return data

def communityActivityData(slum_code):
    act_data = CommunityMobilization.objects.filter(slum_id = slum_code[0][0]).values_list('activity_type', 'household_number')
    comm_avni = CommunityMobilizationActivityAttendance.objects.filter(slum_id = slum_code[0][0]).values_list('activity_type', 'household_number')
    try:
        activity_data_with_hh = {}
        for activity_record in act_data:    # here we are processing data where we have household numbers in json field.
            if activity_record[0] in activity_data_with_hh:
                temp = activity_data_with_hh[activity_record[0]]
                temp.extend(activity_record[1])
                activity_data_with_hh[activity_record[0]] = list(set(temp))
            else:
                activity_data_with_hh[activity_record[0]] = activity_record[1]

        for activity_record in comm_avni:    # here we are processing data where we have household numbers as str.
            if activity_record[0] in activity_data_with_hh:
                temp = activity_data_with_hh[activity_record[0]]
                temp.append(activity_record[1])
                activity_data_with_hh[activity_record[0]] = list(set(temp))
            else:
                activity_data_with_hh[activity_record[0]] = [activity_record[1]]
        
        hh_activity_cnt = {}     # counting number of distinct activity attended by the household. 
        for k, v in activity_data_with_hh.items():
            for i in list(set(v)):
                if i in hh_activity_cnt:
                    hh_activity_cnt[i] += 1
                else:
                    hh_activity_cnt[i] = 1
        return hh_activity_cnt
    except Exception as e:
        print(e)


# For Mastersheet Summery View Processing data
@csrf_exempt
@apply_permissions_ajax('mastersheet.can_view_mastersheet')
@deco_city_permission
def ProcessShortView(request, slum_details=0):
    try:
        formdict = []
        rhs_not_done = []
        global slum_code
        slum_code = Slum.objects.filter(pk=int(request.GET['slumname'])).values_list("id", "name", "electoral_ward__administrative_ward__city__name__city_name")
        slum_funder = SponsorProjectDetails.objects.filter(slum=slum_code[0][0]).exclude(sponsor__id=10)
        invoice_data = InvoiceItems.objects.filter(slum_id = slum_code[0][0]).values_list('household_numbers', flat = True)

        householdData = HouseholdData.objects.filter(slum_id = slum_code[0][0], rhs_data__isnull = False)
        formdict = list(map(getRhsData, householdData))
        check_formdict = {str(int(x['household_number'])): x for x in formdict}

        household_with_invoice_data = []
        for i in invoice_data:
            household_with_invoice_data.extend(i)
        
        for i in list(set(household_with_invoice_data)):
            if str(i) in check_formdict:
                temp = check_formdict[str(i)]
                temp['invoice_entry'] = 'Yes'
            else:
                temp_dict = {'household_number':str(i), 'occupancy_status': "RHS Not Done", 'invoice_entry':'Yes'}
                rhs_not_done.append(temp_dict)

        hh_activity_cnt = communityActivityData(slum_code)

        for k, v in hh_activity_cnt.items():   # Adding activity count to the json data for response.
            if k in check_formdict:
                temp = check_formdict[k]
                temp['total_moilization_acticity'] = v
            else:
                temp_dict = {'household_number':k, 'occupancy_status': "RHS Not Done", 'total_moilization_acticity':v}
                rhs_not_done.append(temp_dict)

        # Daily Reporting - fetching data
        toilet_reconstruction_fields = ['slum', 'slum__name', 'household_number', 'agreement_date_str',
                                            'agreement_cancelled',
                                            'septic_tank_date_str', 'phase_one_material_date_str',
                                            'phase_two_material_date_str', 'phase_three_material_date_str',
                                            'completion_date_str', 'status', 'comment', 'pocket',
                                            'p1_material_shifted_to',
                                            'p2_material_shifted_to', 'p3_material_shifted_to',
                                            'st_material_shifted_to',
                                            'id']

        daily_reporting_data = ToiletConstruction.objects.extra(
                select={'phase_one_material_date_str': "to_char(phase_one_material_date, 'YYYY-MM-DD ')",
                        'phase_two_material_date_str': "to_char(phase_two_material_date, 'YYYY-MM-DD ')",
                        'phase_three_material_date_str': "to_char(phase_three_material_date, 'YYYY-MM-DD ')",
                        'septic_tank_date_str': "to_char(septic_tank_date, 'YYYY-MM-DD ')",
                        'agreement_date_str': "to_char(agreement_date, 'YYYY-MM-DD ')",
                        'completion_date_str': "to_char(completion_date, 'YYYY-MM-DD ')"}).filter(
                slum__id=slum_code[0][0])

        daily_reporting_data = daily_reporting_data.values(*toilet_reconstruction_fields)
        for i in daily_reporting_data:   # Prpcessing Daily Reporting data.
            if i['household_number'] in check_formdict:
                temp = check_formdict[i['household_number']]
                temp['phase_one_material_date'] = i['phase_one_material_date_str']
                if i['phase_two_material_date_str']: # Checking completion delayed.
                    if not i['completion_date_str'] and is_delayed(i['phase_two_material_date_str']):
                        temp['Completion delayed'] = 'Yes'
                    else:
                        temp['Completion delayed'] = 'No'
                temp['agreement_cancelled'] = i['agreement_cancelled']

                if i['p1_material_shifted_to'] or i['p2_material_shifted_to'] or i['p3_material_shifted_to']:  # Checking material is shifted or not.
                    temp['material_shifted'] = 'Yes'
                else:
                    temp['material_shifted'] = 'No'
                if i['status'] is not None:    # Checking Status of the household
                    if i['status'].strip() != "":
                        temp['toilet_status'] = ToiletConstruction.get_status_display(i['status'])
                        if temp['toilet_status'] == 'Completed':
                            temp['current_place_of_defication'] = 'Toilet by SA'

                if len(slum_funder) != 0:   # Adding funder project name.
                    for funder in slum_funder:
                        if funder.household_code != None:
                            if int(i['household_number']) in funder.household_code:
                                temp.update({'sponsor_project': funder.sponsor_project.name})  # funder.sponsor.organization_name})
                check_formdict[i['household_number']] = temp
            else:
                temp_dict = {'household_number':i['household_number'], 'occupancy_status': "RHS Not Done"}
                rhs_not_done.append(temp_dict)
        formdict.extend(rhs_not_done)


    except Exception as e:
        print(e)
    return HttpResponse(json.dumps(formdict), content_type="application/json")


def AnalyseGisTabData(slum_id):
    try:
        global slum_code
        slum_code = Slum.objects.filter(pk=int(slum_id)).values_list("id", "name", "electoral_ward__administrative_ward__city__name__city_name")
        slum_funder = SponsorProjectDetails.objects.filter(slum=slum_code[0][0]).exclude(sponsor__id=10)
        Toilet_data = ToiletConstruction.objects.filter(slum=slum_code[0][0], phase_one_material_date__isnull = False).exclude(agreement_cancelled = True)
        householdData = HouseholdData.objects.filter(slum_id = slum_code[0][0], rhs_data__isnull = False)
        columns_lst = ['city_name', 'slum', 'household_number', 'occupancy_status', 'typeUnoccupiedHouse', 'pluscodes', 'pluscodepart', 
                        'house_structure', 'ownership_status', 'name_head_of_he_household', 'isAadharCard', 'aadhar_number', 'color_of_ration_card', 
                        'girls_child', 'house_area', 'Do you have individual water connection at home?', 'Type_of_water_connection', 'Facility_of_solid_waste_collection', 
                        'Do you have a toilet at home?', 'Status of toilet under SBM ?', 'Where the individual toilet is connected to ?', 'Who all use toilets in the household ?', 
                        'Reason for not using toilet ?', 'current_place_of_defication', 'Is there availability of drainage to connect it to the toilet?', 'Are you interested in an individual toilet ?', 
                        'Which CTB do your family members use ?', 'Does any household member have any of the construction skills given below ?', 'final_status', 'pocket', 'comment', 
                        'sponsor_project', 'factsheet_done', 'family_factsheet_name', 'toilet_connected_to', 'Have you upgraded your toilet/bathroom/house while constructing individual toilet?', 
                        'Cost of upgradation', 'activity_count']
        formdict = list(map(getRhsData, householdData))

        # For Follow-up data.....
        followup_data = {}
        cod_data = FollowupData.objects.filter(slum=slum_code[0][0]).values('household_number', 'followup_data', 'submission_date')
        for followup_record in cod_data:
            if str(int(followup_record['household_number'])) in followup_data:
                temp = followup_data[str(int(followup_record['household_number']))]
                if temp['submission_date'] < followup_record['submission_date']:
                    hh = str(int(followup_record['household_number']))
                    del followup_record['household_number']
                    temp = followup_record
                    followup_data[hh] = temp
            else:
                hh = str(int(followup_record['household_number']))
                temp_dict = {'submission_date':followup_record['submission_date'], 'followup_data':followup_record['followup_data']}
                followup_data[hh] = temp_dict
        # For Daily Reporting data....
        def getToiletData(record):
            data = {}
            if record.status is not None and record.status.strip() != '':
                data['final_status'] = ToiletConstruction.get_status_display(record.status)
            if record.pocket is not None:
                data['pocket'] = record.pocket
            if record.comment is not None and record.comment.strip() != "":
                data['comment'] = record.comment
            data['household_number'] = str(int(record.household_number))
            return data
        toiletdict = list(map(getToiletData, Toilet_data))
        toiletdict = {temp_data['household_number'] : temp_data for temp_data in toiletdict}
        # for Communication Activity data ...
        activity_count = communityActivityData(slum_code)

        sanitation_keys = {'Do you have a toilet at home?': 'Do you have a toilet at home?', 'group_oi8ts04/Status_of_toilet_under_SBM': 'Status of toilet under SBM ?', 'group_oi8ts04/What_is_the_toilet_connected_to': 'Where the individual toilet is connected to ?', 
                            'group_oi8ts04/Who_all_use_toilets_in_the_hou': 'Who all use toilets in the household ?', 'group_oi8ts04/Reason_for_not_using_toilet': 'Reason for not using toilet ?', 'group_oi8ts04/Current_place_of_defecation': 'current_place_of_defication', 
                            'group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets': 'Is there availability of drainage to connect it to the toilet?', 'group_oi8ts04/Are_you_interested_in_an_indiv': 'Are you interested in an individual toilet ?', 
                            'group_oi8ts04/Which_Community_Toil_r_family_members_use': 'Which CTB do your family members use ?', 'group_el9cl08/Does_any_household_m_n_skills_given_below': 'Does any household member have any of the construction skills given below ?'}
        check_formdict = {}
        for dct in formdict:
            if 'occupancy_status' in dct and dct['occupancy_status'] == "Occupied house":
                hh = str(int(dct['household_number']))
                # checking for followup-data
                if hh in followup_data:
                    temp = followup_data[hh]
                    sanitation_data = {sanitation_keys[key]: temp['followup_data'][key] for key in sanitation_keys.keys() if key in temp['followup_data']}
                    dct.update(sanitation_data)
                # adding Daily Reporting data ...
                if str(int(hh)) in toiletdict:
                    temp_data = toiletdict[str(int(hh))]
                    del temp_data['household_number']
                    dct.update(temp_data)
                # Adding Funder project data .....
                if len(slum_funder) != 0:   # Adding funder project name.
                    for funder in slum_funder:
                        if funder.household_code != None:
                            if int(hh) in funder.household_code:
                                dct.update({'sponsor_project': funder.sponsor_project.name})
                # Adding Activity Attend count ...
                if hh in activity_count:
                    dct.update({'activity_count':activity_count[hh]})
                diff_keys = set(columns_lst).difference(set(dct.keys())) # Handling Empty data fields
                temp_dict = {i : None for i in diff_keys}
                dct.update(temp_dict)
            check_formdict[dct['household_number']] = dct
        return list(check_formdict.values()), columns_lst, slum_code[0][1]
    except Exception as e:
        print(e)

# For Gis Tab
@csrf_exempt
def gisDataDownload(request):
    slum_id = request.POST.get('gisdata_slumname')
    city_id = request.POST.get('gisdata_cityname')
    if not city_id:
        response_data,  columns_lst, slum_name = AnalyseGisTabData(slum_id)
        filename = remove_invalid_char(str(slum_name))+'.csv'
    else:
        exportClassObj = exportMethods(city_id)
        response_data, city_name = exportClassObj.cityWiseRhsData()
        columns_lst = ['Household_id', 'Avni UUID', 'Household number', 'Slum', 'Survey Date','slum_id', 'Name of the Surveyor', 'Type of structure occupancy', 'Type of unoccupied house', 'Parent household number', 'Full name of the head of the household', 'Enter the 10 digit mobile number', 'Aadhar number', 'Number of household members', 'Total female members', 'total male members', 'total other gender members', 'Do you have any girl child/children under the age of 18?', 'How many ? ( Count )', 'Type of structure of house', 'Ownership status of the household', 'House area in sq. ft.', 'Type of water connection', 'group_el9cl08/Facility_of_solid_waste_collection', 'Plus code of the house', 'group_oi8ts04/Current_place_of_defecation', 'Type of household toilet ?', "Are you interested in an individual toilet?", "Current place of defecation", 'Does any member of the household go for open defecation ?', 'Do you have a toilet at home?', 'If no for individual toilet , why?', 
            'Under what scheme would you like your toilet to be built ?', 'Does any household member have any of the construction skills give below?', 'Have you applied for an individual toilet under SBM?', 'How many installments have you received?', 'When did you receive your first installment?', 'When did you receive your second installment?', 'When did you receive your third installment?', 'If built by a contractor, how satisfied are you?', 'Status of toilet under SBM?', 'What was the cost incurred to build the toilet?', 'Current place of defecation', 'Which CTB', 'Is there availability of drainage to connect to the toilet?', 'Are you interested in an individual toilet?', 'What kind of toilet would you like?', 'Under what scheme would you like your toilet to be built?', 'If yes, why?', 'If no, why?', 'What is the toilet connected to?', 'Who all use toilets in the household?', 'Reason for not using toilet']
        filename = remove_invalid_char(str(city_name))+'.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition']  =  'attachment; filename='+filename
    writer = csv.DictWriter(response, columns_lst)
    writer.writeheader()
    writer.writerows(response_data)
    return response