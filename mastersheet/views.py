from __future__ import division
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test, permission_required
from mastersheet.forms import find_slum, file_form, account_find_slum
from django.db.models import Count, F
from mastersheet.models import *
from sponsor.models import *
from itertools import chain
from master.models import *
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import pandas
from urllib import request as urllib2
from django.conf import settings
import collections
from django.http import JsonResponse
from mastersheet.daily_reporting_sync import ToiletConstructionSync, CommunityMobilizaitonSync
from utils.utils_permission import apply_permissions_ajax
from .decorators import deco_city_permission
from collections import defaultdict
import datetime
import itertools
from django.db.models.functions import Length
import xlwt
from xlwt import Workbook
from mastersheet.models import *
from graphs.models import *
from django.core import serializers

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
        temp_formdict = []
        formdict_family_factsheet = []
        slum_code = Slum.objects.filter(pk=int(request.GET['slumname'])).values_list("id", "shelter_slum_code",
                                                         "electoral_ward__administrative_ward__city__id",
                                                         "electoral_ward__name", "name")

        slum_funder = SponsorProjectDetails.objects.filter(slum__name=str(slum_code[0][4])).exclude(sponsor__id=10)
        form_ids = Survey.objects.filter(city__id=int(slum_code[0][2]))

        household_data = HouseholdData.objects.filter(slum__id=slum_code[0][0])
        followup_data_false = FollowupData.objects.filter(slum=slum_code[0][0])#,flag_followup_in_rhs = False)
        # followup_data_true = FollowupData.objects.filter(slum=slum_code[0][0],flag_followup_in_rhs = True)

        if slum_code is not 0:
            if flag_fetch_rhs :
                formdict = list(map(lambda x: x.rhs_data, filter(lambda x: x.rhs_data!=None, household_data)))
                for i in formdict:
                       if i['Type_of_structure_occupancy'] == 'Locked house':
                           list_of_keys= ['Household_number', 'Date_of_survey', 'Name_s_of_the_surveyor_s', 'Type_of_structure_occupancy']
                           temp_dict = {}
                           for cust_key in list_of_keys:
                               if cust_key in i:
                                   temp_dict[cust_key] = i[cust_key]
                           #print(temp_dict)
                           temp_formdict.append(temp_dict)
                       else:
                            temp_formdict.append(i)

                formdict = temp_formdict

            else:
                formdict = list(map(lambda x:{'Household_number':x.household_number, '_id':x.rhs_data['_id'] if '_id' in x.rhs_data else None,
                '_xform_id_string':x.rhs_data['_xform_id_string'] if '_xform_id_string' in x.rhs_data else None}, filter(lambda x:x.rhs_data!=None, household_data)))

            if flag_fetch_ff:
                try:
                    formdict_family_factsheet = list(map(lambda x:(x.ff_data if x.ff_data else {'group_vq77l17/Household_number': 00 }),household_data))
                    # formdict_family_factsheet = map(lambda x:(x.ff_data if x.ff_data else {'group_vq77l17/Household_number': 00 }),household_data)
                # Family Factsheet - fetching data
                # arranging data with respect to household numbers
                except Exception as e:
                    print(e,'in ff')
                temp_FF = {str(int(obj_FF['group_vq77l17/Household_number'])): obj_FF for obj_FF in formdict_family_factsheet}
                temp_FF_keys = temp_FF.keys() # list of household numbers

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

            # # SBM - fetching data
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
            # community_mobilization_data1 = community_mobilization_data.values(*community_mobilization_fields)
            # community_mobilization_data_list = list(community_mobilization_data1)
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
                            "ff_xform_id_string": "",
                            "_xform_id_string": "",
                            "_attachments": "",
                            "no_rhs_flag": "#eba6fc"
                        }
                    vendor_name = "vendor_type" + str(y.material_type)
                    invoice_number = "invoice_number" + str(y.material_type)
                    dummy_formdict[str(z)].update({
                        vendor_name: y.invoice.vendor.name,
                        invoice_number: y.invoice.invoice_number,
                        str(y.material_type) + " Invoice Number" + "_id": y.invoice.id,
                        "Name of " + str(y.material_type) + " vendor" + "_id": y.invoice.id
                    })

            for y in community_mobilization_data_avni:
                new_activity_type = y.activity_type.name
                if y.household_number in dummy_formdict.keys():
                    dummy_formdict[str(y.household_number)].update({new_activity_type: str(y.date_of_activity), str(new_activity_type) + "_id": y.id})
                else :
                    dummy_formdict[str(int(y.household_number)) ] = {
                        "Household_number": str(int(y.household_number)),
                        "_id": "",
                        "ff_id": "",
                        "ff_xform_id_string": "",
                        "_xform_id_string": "",
                        "_attachments": "",
                        "no_rhs_flag": "#eba6fc"
                    }
                    dummy_formdict[str(int(y.household_number))].update({new_activity_type: str(y.date_of_activity), str(new_activity_type) + "_id": y.id})

            for y in community_mobilization_data:
                #y = community_mobilization_data[i]
                for z in y.household_number:
                    new_activity_type = y.activity_type.name
                    z = str(int(z))
                    if z not in dummy_formdict.keys():
                        dummy_formdict[z] = {
                            "Household_number": z,
                            "_id": "",
                            "ff_id": "",
                            "ff_xform_id_string": "",
                            "_xform_id_string": "",
                            "_attachments": "",
                            "no_rhs_flag": "#eba6fc"
                        }
                    dummy_formdict[z].update({new_activity_type: y.activity_date_str, str(new_activity_type) + "_id": y.id})

            for i in temp_sbm_keys:
                if str(i) not in dummy_formdict.keys():
                    dummy_formdict[str(i)] = {
                        "Household_number": i,
                        "_id": "",
                        "ff_id": "",
                        "ff_xform_id_string": "",
                        "_xform_id_string": "",
                        "_attachments": "",
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
                        "ff_xform_id_string": "",
                        "_xform_id_string": "",
                        "_attachments": "",
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
                        else :
                            ff_id = temp_FF[x['Household_number']]

                        if '_xform_id_string' in temp_FF[x['Household_number']].keys():
                            ff_xform_id_string = temp_FF[x['Household_number']]['_xform_id_string']
                            del (temp_FF[x['Household_number']]['_xform_id_string'])
                        else :
                            ff_xform_id_string = None

                        x.update(temp_FF[x['Household_number']])
                        x['OnfieldFactsheet'] = 'Yes'
                        x['_id'] = temp
                        x['ff_id'] = ff_id
                        x['ff_xform_id_string'] = ff_xform_id_string

                if '_attachments' in x.keys() and len(x['_attachments']) != 0:
                    PATH = settings.BASE_URL + '/'.join(x['_attachments'][0]['download_url'].split('/')[:-1])
                    if 'Toilet_Photo' in x.keys():
                        x.update({'toilet_photo_url': PATH + '/' + x['Toilet_Photo']})
                    if 'Family_Photo' in x.keys():
                        x.update({'family_photo_url': PATH + '/' + x['Family_Photo']})
                else:
                    if 'Toilet_Photo' and 'ff_uuid' in x.keys():
                        ff_url = settings.AVNI_URL + '/#/app/subject/viewProgramEncounter?uuid=' + str(x['ff_uuid'])
                        x.update({'toilet_photo_url': ff_url if ff_url else x['Toilet_Photo']})
                        x.update({'family_photo_url': ff_url if ff_url else x['Family_Photo']})

                if '_xform_id_string' in x.keys():
                    x.update({'rhs_url': settings.BASE_URL + str('shelter/forms/') + str(x['_xform_id_string']) + str('/instance#/') + str(x['_id'])})
                elif 'rhs_uuid' in x.keys() :
                    x.update({'rhs_url':settings.AVNI_URL + '#/app/subject?uuid=' + str(x['rhs_uuid'])})
                else:pass

                if 'ff_xform_id_string' in x.keys():
                    x.update({'ff_url': settings.BASE_URL + str('shelter/forms/') + str(x['ff_xform_id_string']) + str('/instance#/') + str(x["ff_id"])})
                elif 'ff_id' in x.keys():
                    x.update({'ff_url': settings.AVNI_URL + '/#/app/subject/viewProgramEncounter?uuid=' + str(x['ff_uuid'])})
                else:pass

                if 'group_oi8ts04/Current_place_of_defecation' in x:
                    x.update({'current place of defecation': x['group_oi8ts04/Current_place_of_defecation']})

                if 'status' in x and x['status'] == 'Completed':
                    x.update({'current place of defecation': 'Toilet by SA'})

                cod_data = followup_data_false.filter(household_number = int(key)).order_by('-submission_date').first()
                # print(cod_data.followup_data.keys())

                if cod_data:
                    if 'group_oi8ts04/Which_Community_Toil_r_family_members_use' in cod_data.followup_data:
                        data1 = cod_data.followup_data['group_oi8ts04/Which_Community_Toil_r_family_members_use']
                        x.update({'group_oi8ts04/Which_Community_Toil_r_family_members_use': data1})
                    if 'group_oi8ts04/Current_place_of_defecation' in cod_data.followup_data:
                        data = cod_data.followup_data['group_oi8ts04/Current_place_of_defecation']
                        x.update({'current place of defecation':data})
                    if 'status' in x and x['status'] == 'Completed':
                        x.update({'current place of defecation': 'Toilet by SA'})
                        x.update({'group_oi8ts04/Status_of_toilet_under_SBM': ''})
                        x.update({'group_oi8ts04/Which_Community_Toil_r_family_members_use':''})

                if len(slum_funder) != 0:
                    for funder in slum_funder:
                        if int(x['Household_number']) in funder.household_code:
                            x.update({'Funder': funder.sponsor_project.name}) #funder.sponsor.organization_name})

            formdict = list(map(lambda x: dummy_formdict[x], dummy_formdict))
            for x in formdict:
                try:
                    if x['current place of defecation'] in ['SBM (Installment)', 'Own toilet'] and len(x['agreement_date_str']) > 1:
                        x['incorrect_cpod'] = 'incorrect_cpod'

                    if x['group_oi8ts04/Current_place_of_defecation'] == 'Own toilet' and x['status'] == 'Completed':
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
        {"data": "group_oi8ts04/Which_Community_Toil_r_family_members_use", "title": "Which CTB"}, #29

        {"data": "group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets",
         "title": "Is there availability of drainage to connect to the toilet?"}, # 30 new
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
                                         number_of_invisible_columns + 1 + 18))  # range(14,32)#range(13,31)
    final_data['buttons']['Follow-up'] = list(range(number_of_invisible_columns + 1 + 18,
                                               number_of_invisible_columns + 1 + 18 + 19))  # range(32,50)#range(31,49)
    final_data['buttons']['Family factsheet'] = list(range(number_of_invisible_columns + 1 + 18 + 19,
                                                      number_of_invisible_columns + 1 + 18 + 19 + 7))  # range(50,57)#range(49,56)
    final_data['buttons']['SBM'] = list(range(number_of_invisible_columns + 1 + 18 + 19 + 7,
                                         number_of_invisible_columns + 1 + 18 + 19 + 7 + 10))  # range(57,67)#range(56,66)
    final_data['buttons']['Construction status'] = list(range(number_of_invisible_columns + 1 + 18 + 19 + 7 + 10,
                                                         number_of_invisible_columns + 1 + 18 + 19 + 7 + 10 + 15))  # range(67,82)#range(66,81)
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
            formdict_new.append({"data": "vendor_type" + str(i.name), "title": "Name of " + str(i.name) + " vendor"})
            formdict_new.append({"data": "invoice_number" + str(i.name), "title": str(i.name) + " Invoice Number"})
    except Exception as e:
        print(e)
    final_data['buttons']['Accounts'] = list(range(vendor_pre_len, len(formdict_new)))
    # print final_data['buttons']['Accounts'] , len(final_data['buttons']['Accounts'])
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
                    # print "in sbm"
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
                            response.append(("updated sbm", i))

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
                                response.append(("newly created sbm", i))
                    except Exception as e:
                        response.append(("The error says: " + str(
                            e) + ". This error is with SBM columns for following household numbers", i))

                if flag_ComMob != 1:
                    # print "in commob"

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
                                            response.append(("updated ComMob", i))
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
                                        response.append(("newly created ComMob", i))
                            except Exception as e:
                                response.append(("The error says: " + str(
                                    e) + ". This error is in Commuinity Mobilization columns for " + p + ", for the following household numbers",
                                                 i))

                if flag_accounts != 1:
                    # print "in accounts"

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
                                            response.append(("updated VHID", i))
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
                                        response.append(("newly created VHID", i))

                            except Exception as e:
                                response.append(("The error says: " + str(
                                    e) + ". This error is in Vendor Invoice Details Columns for " + m + ", for the following household numbers",
                                                 i))

                if flag_TC != 1:
                    try:
                        TC_instance = ToiletConstruction.objects.select_related().filter(household_number=int(i),
                                                                                         slum__name=this_slum)
                        if TC_instance:
                            try:
                                TC_instance[0].update_model(df_TC.loc[int(i), :])
                            except Exception as e:
                                print(e)
                            response.append(("updated TC", i))

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
                            response.append(("newly created TC", i))
                    except Exception as e:
                        response.append(("The error says: " + str(
                            e) + ". This error is with Toilet Construction Columns for following household numbers", i))

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
        user = request.user
        toilet_const = ToiletConstructionSync(slum, user)
        t_data = toilet_const.fetch_data()
        com_mobilization = CommunityMobilizaitonSync(slum, user)
        c_data = com_mobilization.fetch_data()

        if any(t_data) and any(c_data):
            if t_data[2] > c_data[2]:
                toilet_const.update_sync_info(t_data[2])
            else:
                com_mobilization.update_sync_info(c_data[2])
        elif any(t_data) and not any(c_data):
            toilet_const.update_sync_info(t_data[2])
        elif not any(t_data) and any(c_data):
            com_mobilization.update_sync_info(c_data[2])
        data['flag'] = True
        if not any(t_data) and not any(c_data):
            data['msg'] = "Nothing to sync for slum - " + slum.name
        else:
            data['msg'] = "Data successfully synced for slum - " + slum.name
            data['msg'] += "\nTotal records updated : " + str(t_data[0] + c_data[0])
    except Exception as e:
        data['flag'] = False
        data['msg'] = "Error occurred while sync from kobo. Please contact administrator." + str(e)
    return HttpResponse(json.dumps(data), content_type="application/json")


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
    electoral_ward__administrative_ward__city__name__city_name__in=group_perm).values_list('id', flat=True)
    #slumFunderCount =SponsorProjectDetails.objects.filter().values('sponsor__organization_name')
    #SponsorProjectDetails.objects.filter().values('sponsor_project__name').count()

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
                    #,'pocket':'pocket','name': 'factsheet_assign'

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
    report_table_data = defaultdict(dict)
    for query_field in query_on.keys():
        if query_field in ['agreement_date', 'phase_one_material_date','phase_two_material_date','phase_three_material_date',
        'completion_date', 'septic_tank_date','use_of_toilet','toilet_connected_to', 'factsheet_done']:
            #['pocket','factsheet_done', 'use_of_toilet', 'toilet_connected_to','completion_date']:
            filter_field = {'slum__id__in': keys, 'completion_date__range': [start_date, end_date],
                            query_field + '__isnull': False}
        else:
            filter_field = {'slum__id__in': keys, query_field + '__range': [start_date, end_date]}
        count_field = {query_on[query_field]: Count('level_id')}
        tc = ToiletConstruction.objects.filter(**filter_field) \
            .exclude(agreement_cancelled=True) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
            .annotate(**count_field).order_by('city_name')
        tc = {obj_ad['level_id']: obj_ad for obj_ad in tc}
        for level_id, data in tc.items():
            report_table_data[level_id].update(data)
            #print(type(report_table_data),len(report_table_data))
     #for cust_obj in report_table_data:
         #report_table_data[cust_obj]['factsheet_assign'] = 4
        #print(report_table_data[cust_obj])
    #print(report_table_data)

    return HttpResponse(json.dumps(list(map(lambda x: report_table_data[x], report_table_data))),
                        content_type="application/json")

@csrf_exempt
def report_table_cm(request):
    tag_key_dict = json.loads(request.body)
    tag = tag_key_dict['tag']
    keys = tag_key_dict['keys']
    group_perm = request.user.groups.values_list('name', flat=True)
    if request.user.is_superuser:
        group_perm = Group.objects.all().values_list('name', flat=True)
    group_perm = map(lambda x: x.split(':')[-1], group_perm)

    keys = Slum.objects.filter(id__in=keys,electoral_ward__administrative_ward__city__name__city_name__in=group_perm).values_list(
        'id', flat=True)

    start_date = tag_key_dict['startDate']
    end_date = tag_key_dict['endDate']

    if start_date == None or end_date == None:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(tag_key_dict['startDate'], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(tag_key_dict['endDate'], "%Y-%m-%d").date()

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
                'level_id': F('slum__id'),

            }
    }
    report_table_data_cm = defaultdict(dict)
    all_activities = []
    data = {}
    activity_type = ActivityType.objects.all()
    for x in activity_type:
        key_for_datatable = "total_" + (x.name).replace(" ", "")
        filter_field = {'slum__id__in': keys, 'activity_date__range': [start_date, end_date]}
        filter_field_new = {'slum_id__in': keys, 'date_of_activity__range': [start_date, end_date]}
        # count_field = {key_for_datatable: len('household_number')}

        y = x.communitymobilization_set.filter(**filter_field) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name','household_number')
            # .annotate(**count_field).order_by('city_name')

        for data in y:
            data.update({key_for_datatable : len(data['household_number'])})
            data.pop('household_number')
            level_id = data['level_id']
            if str(level_id) in report_table_data_cm.keys() and key_for_datatable in report_table_data_cm[
                str(level_id)].keys():
                report_table_data_cm[str(level_id)][key_for_datatable] += data[key_for_datatable]
            else:
                report_table_data_cm[str(level_id)].update(data)

        new = x.communitymobilizationactivityattendance_set.filter(**filter_field_new)
        a = new.annotate(**level_data[tag]).values('level', 'level_id', 'city_name').order_by('city_name')
        household_count = {key_for_datatable: a.count()}
        for k,v in household_count.items():
            if v >0:
                all_activities.append(household_count)

        if len(a)>0:
            for i in a[0:1]:
                level_id = i['level_id']
                i.update(household_count)
                data = i
            new_dict ={str(level_id):data}
            for j in all_activities:
                data.update(j)
            report_table_data_cm.update(new_dict)

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

    keys = Slum.objects.filter(id__in=keys, electoral_ward__administrative_ward__city__name__city_name__in=group_perm).values_list('id', flat=True)

    start_date = tag_key_dict['startDate']
    end_date = tag_key_dict['endDate']

    if start_date == None or end_date == None:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(tag_key_dict['startDate'], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(tag_key_dict['endDate'], "%Y-%m-%d").date()

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
                'level_id': F('slum__id'),

            }
    }
    report_table_data_cm_activity_count = defaultdict(dict)
    activity_type = ActivityType.objects.all()

    for x in activity_type:
        key_for_datatable = "total_" + (x.name).replace(" ", "")
        filter_field = {'slum__id__in': keys, 'activity_date__range': [start_date, end_date]}
        filter_field_new = {'slum_id__in': keys, 'date_of_activity__range': [start_date, end_date]}
        count_field = {key_for_datatable: Count('activity_type')}

        y = x.communitymobilization_set.filter(**filter_field) \
            .annotate(**level_data[tag]).values('level','level_id','city_name') \
            .annotate(**count_field).order_by('city_name')

        for data in y:
            level_id = data['level_id']
            if str(level_id) in report_table_data_cm_activity_count.keys() and key_for_datatable in \
                    report_table_data_cm_activity_count[str(level_id)].keys():
                report_table_data_cm_activity_count[str(level_id)][key_for_datatable] += data[key_for_datatable]
            else:
                report_table_data_cm_activity_count[str(level_id)].update(data)

        new = x.communitymobilizationactivityattendance_set.filter(**filter_field_new)\
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name')\
            .annotate(**count_field).order_by('city_name')
        for i in new:
            i.update({key_for_datatable : 1})

        for data in new:
            level_id = data['level_id']
            if str(level_id) in report_table_data_cm_activity_count.keys() and key_for_datatable in \
                    report_table_data_cm_activity_count[str(level_id)].keys():
                report_table_data_cm_activity_count[str(level_id)][key_for_datatable] += data[key_for_datatable]
            else:
                report_table_data_cm_activity_count[str(level_id)].update(data)

    return HttpResponse(json.dumps(list(map(lambda x: report_table_data_cm_activity_count[x], report_table_data_cm_activity_count))),
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

    query_on = {'phase_one_material_date': 'total_p1',
                'phase_two_material_date': 'total_p2',
                'phase_three_material_date': 'total_p3',
                }

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
    report_table_accounts_data = defaultdict(dict)
    for query_field in query_on.keys():
        filter_field = {'slum__id__in': keys, query_field + '__range': [start_date, end_date]}
        count_field = {query_on[query_field]: Count('level_id')}
        tc = ToiletConstruction.objects.filter(**filter_field) \
            .exclude(agreement_cancelled=True) \
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name') \
            .annotate(**count_field).order_by('city_name')
        tc = {obj_ad['level_id']: obj_ad for obj_ad in tc}

        for level_id, data in tc.items():
            report_table_accounts_data[level_id].update(data)

    filter_field = {'slum__id__in': keys, 'invoice__invoice_date__range': [start_date, end_date]}

    invoiceItems = InvoiceItems.objects.filter(**filter_field) \
        .annotate(**level_data[tag]).values('level', 'level_id', 'city_name', 'phase', 'household_numbers',
                                            'material_type__name') \
        .order_by('city_name')

    invoiceItems = itertools.groupby(sorted(invoiceItems, key=lambda x: x['level_id']), key=lambda x: x['level_id'])

    for level, level_wise_list in invoiceItems:

        new_phase_wise_list = itertools.groupby(sorted(level_wise_list, key=lambda x: x['phase']),
                                                key=lambda x: x['phase'])

        for key_phase, values_list in new_phase_wise_list:

            values_list_temp = itertools.groupby(
                list(sorted(list(values_list), key=lambda x: x['material_type__name'])),
                key=lambda x: x['material_type__name'])
            temp_material_type_count_dict = defaultdict(int)
            for material_type_name, material_type_list in values_list_temp:
                material_type_list_temp = list(material_type_list)
                if len(material_type_list_temp) > 0:
                    temp_material_type_count_dict[str(material_type_name)] = len(
                        json.loads(str(material_type_list_temp[0]['household_numbers'])))
            str_tmp = ''
            for k, v in temp_material_type_count_dict.items():
                str_tmp = str_tmp + k + ':' + str(v) + '<br/>'
            report_table_accounts_data[level].update({'total_p' + str(key_phase) + '_accounts': str_tmp})

    return HttpResponse(json.dumps(list(map(lambda x: report_table_accounts_data[x], report_table_accounts_data))),
                        content_type="application/json")


@user_passes_test(lambda u: u.groups.filter(name="Account").exists() or u.is_superuser)
def accounts_excel_generation(request):
    account_form = account_find_slum(request.POST)
    # print account_form.cleaned_data.get('account_start_date')

    city_id = request.POST.get('account_cityname')
    slum_id = request.POST.get('account_slumname')
    # end_date = request.POST.get('account_end_date')
    if len(request.POST.get('account_start_date')) == 0 or len(request.POST.get('account_end_date')) == 0:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(request.POST.get('account_start_date'), "%d-%m-%Y").date()
        end_date = datetime.datetime.strptime(request.POST.get('account_end_date'), "%d-%m-%Y").date()
    wb = Workbook()
    print(slum_id)
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

    if len(city_id) == 0:
        invoiceItems = InvoiceItems.objects.filter(slum__id=int(slum_id),
                                                   invoice__invoice_date__range=[start_date, end_date])
        fname = str(Slum.objects.get(id=int(slum_id))) + '.xls'
    else:
        invoiceItems = InvoiceItems.objects.filter(slum__electoral_ward__administrative_ward__city__id=int(city_id),
                                                   invoice__invoice_date__range=[start_date, end_date])
        fname = str(City.objects.get(id=int(city_id))) + '.xls'
    dict_of_dict = defaultdict(dict)
    sponsor = SponsorProjectDetails.objects.all()

    for i in invoiceItems:
        for j in i.household_numbers:
            try:
                dict_of_dict[(j, i.slum)].update({i.material_type: i})
            except:
                dict_of_dict[(j, i.slum)] = {i.material_type: i}

    i = 1
    for k, v in dict_of_dict.items():
        try:
            s = str(sponsor.filter(slum__id=1094, household_code__contains=k[0]).exclude(
                sponsor__organization_name='SBM Toilets')[0].sponsor.organization_name)
        except Exception as e:
            s = 'Sponsor Error'
        for inner_k, inner_v in v.items():
            sheet1.write(i, 0, str(inner_v.invoice.invoice_date))
            sheet1.write(i, 1, inner_v.invoice.invoice_number)
            sheet1.write(i, 2, inner_v.invoice.vendor.name)
            sheet1.write(i, 3, s)
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
            i = i + 1

    # wb.save(fname)
    response = HttpResponse(content_type="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=%s' % str(fname).replace(' ', '_')
    wb.save(response)
    return response
