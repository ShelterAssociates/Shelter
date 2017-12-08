''''
    Script to update PCMC RHS records for current place of defecation. 
    To run include the folder in sys path
    
    import sys
    sys.path.insert(0, 'scripts/update_kobo_records/')
'''

import uuid
import traceback
import copy
from sponsor.models import *
from django.conf import settings
import json
import urllib2
import itertools
import os
from time import gmtime, strftime
import xlrd
import openpyxl
import psycopg2
import datetime
import dicttoxml
import xml.etree.ElementTree as ET
import requests
import shutil
import traceback

kobo_survey = '54'
root_folder_path = os.path.dirname(os.path.abspath(__file__))
root_output_folder = os.path.join(root_folder_path, 'xml_output')
output_folder_path = os.path.join(root_output_folder, 'PCMC', 'RHS')


def rhs_form():
    gl_rhs_xml_dict = {
        'formhub' : {
            'uuid' : None
        },
        'start' : None,
        'end' : None,
        'group_ce0hf58' : {
            'city' : None,
            'admin_ward' : None,
            'slum_name' : None,
            'date_of_rhs' : None,
            'name_of_surveyor_who_collected_rhs_data' : None,
            'house_no' : None,
            'Type_of_structure_occupancy' : None
        },
        'group_ye18c77' : {
            'group_ud4em45' : {
                'what_is_the_full_name_of_the_family_head_' : None,
                'mobile_number' : None,
                'adhar_card_number' : None
            },
            'group_yw8pj39' : {
                'what_is_the_structure_of_the_house' : None,
                'what_is_the_ownership_status_of_the_house' : None,
                'number_of_family_members' : None,
                'Do_you_have_a_girl_child_under' : None,
                'if_yes_how_many_' : None,
                'house_area_in_sq_ft' : None,
                'Current_place_of_defecation_toilet' : None,
                'does_any_member_of_your_family_go_for_open_defecation_' : None,
                'where_the_individual_toilet_is_connected_to_' : None,
                'type_of_water_connection' : None,
                'facility_of_waste_collection' : None,
                'Are_you_interested_in_individu' : None,
                'if_yes_why_' : None,
                'if_no_why_' : None,
                'type_of_toilet_preference' : None,
                'Have_you_applied_for_indiviual' : None,
                'How_many_installements_have_yo' : None,
                'when_did_you_receive_the_first_installment_date' : None,
                'when_did_you_receive_the_second_installment_date' : None,
                'what_is_the_status_of_toilet_under_sbm_' : None,
                'Does_any_family_members_has_co' : None
            },
        },
        '__version__' : None,
        'meta' : {
            'instanceID' : None
        }
    }

    return gl_rhs_xml_dict

def sbmUpdate():
    print "Start fetching the details"
    sponsored_households = SponsorProjectDetails.objects.filter(sponsor__organization_name = "SBM Toilets")
    for sponsored_household in sponsored_households:
        slum_code = sponsored_household.slum.shelter_slum_code
        url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?format=json&query={"group_ce0hf58/slum_name":"' + slum_code + '"}'
        kobotoolbox_request = urllib2.Request(url)
        kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
        kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
        res = urllib2.urlopen(kobotoolbox_request)
        html = res.read()
        json_records = json.loads(html)
        grouped_records = itertools.groupby(sorted(json_records, key=lambda x: int(x['group_ce0hf58/house_no'])), key=lambda x: int(x["group_ce0hf58/house_no"]))
        records={}
        for list_record in grouped_records:
            records[list_record[0]] = list(list_record[1])
        slum = sponsored_household.slum.name
        print slum
        folder_path = os.path.join(output_folder_path, "slum_" + str(slum.replace('/','')))
        rec = []
        for house in sponsored_household.household_code:
            #house = '000'.join(str(house))[-4:]
            if house in records:
                record_sorted = sorted(records[house], key=lambda x: x['end'], reverse=True)
                record = record_sorted[0]
                if 'group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet' in record and record['group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet'] in ['01', '02']:
                    #rec.append(str(house) +' :: '+ str(len(record_sorted)) + ' :: '+str(record['_id']))
                    create_data = rhs_xml_create(record)

                    status, replace_data = pcmc_rhs_xml_replace(create_data)
                    if status:
                        replace_data['__version__'] = record['__version__']
                        xml_string = create_xml_string(replace_data, [], record['_xform_id_string'], record['_xform_id_string'], record['__version__'])
                        file_name = 'RHS_Survey_Slum_Id_' + str(slum.replace('/','')) + '_House_code_' + str(house)


                        create_xml_file(xml_string, file_name, folder_path)
            else:
                rec.append(str(house))#print "Not found" + str(house)
        print rec

def queryToFetchRecords(kobo_survey, slum_code):
    print "Start fetching the details"
    rec=[]
    folder_path = os.path.join(output_folder_path, "slum_" + str(slum_code.replace('/', '')))
    url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?format=json&query={"group_ce0hf58/slum_name":"' + slum_code + '"}'
    kobotoolbox_request = urllib2.Request(url)
    kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
    kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
    res = urllib2.urlopen(kobotoolbox_request)
    html = res.read()
    json_records = json.loads(html)
    grouped_records = itertools.groupby(sorted(json_records, key=lambda x: int(x['group_ce0hf58/house_no'])),
                                        key=lambda x: int(x["group_ce0hf58/house_no"]))
    records = {}
    for list_record in grouped_records:
        records[list_record[0]] = list(list_record[1])
    for key,val in records.iteritems():
        record_sorted = sorted(val, key=lambda x: x['end'], reverse=True)
        record = record_sorted[0]
        create_data = rhs_xml_create(record)
        status, replace_data = kmc_rhs_xml_replace(create_data)

        if status:
            replace_data['__version__'] = record['__version__']
            xml_string = create_xml_string(replace_data, [], record['_xform_id_string'], record['_xform_id_string'],
                                           record['__version__'])
            file_name = 'RHS_Survey_Slum_Id_' + str(slum_code.replace('/', '')) + '_House_code_' + str(key)

            create_xml_file(xml_string, file_name, folder_path)
    return rec

def rhs_xml_create(xml_record):
    gl_rhs_xml_dict = rhs_form()
    for key, val in xml_record.iteritems():
        key = str(key)
        if not key.startswith( '_' ):
            split_key = key.split('/')
            if len(split_key) == 1:
                gl_rhs_xml_dict[split_key[0]] = val
            if len(split_key) == 2:
                gl_rhs_xml_dict[split_key[0]][split_key[1]] = val
            if len(split_key) == 3:
                gl_rhs_xml_dict[split_key[0]][split_key[1]][split_key[2]] = val
            if len(split_key) == 4:
                gl_rhs_xml_dict[split_key[0]][split_key[1]][split_key[2]][split_key[3]] = val

    return gl_rhs_xml_dict

def pcmc_rhs_xml_replace(rhs_record):
    flag=False
    if rhs_record['group_ce0hf58']['Type_of_structure_occupancy'] == '01' :
        rhs_record['group_ye18c77']['group_yw8pj39']['Current_place_of_defecation_toilet'] = "03"
        rhs_record['meta']['deprecatedID'] = rhs_record['meta']['instanceID']
        rhs_record['meta']['instanceID'] = 'uuid:' + str(uuid.uuid4())
        flag = True
        # if rhs_record['group_ye18c77']['group_yw8pj39']['Are_you_interested_in_individu'] == "02":
        #     print "Not interested"
    else:
        flag = False
        print "ERROR"
    return flag, rhs_record

def kmc_rhs_xml_replace(rhs_record):
    flag=False
    '''Replacement for the records
    '''
    rhs_record['meta']['deprecatedID'] = rhs_record['meta']['instanceID']
    rhs_record['meta']['instanceID'] = 'uuid:' + str(uuid.uuid4())
    flag=True
    return flag, rhs_record

def create_xml_string(xml_dict, repeat_dict, xml_root, xml_root_attr_id, xml_root_attr_version):
    xml_string = dicttoxml.dicttoxml(xml_dict, attr_type=False, custom_root=xml_root)
    # print(xml_string)
    # print("\n")
    root = ET.fromstring(xml_string)
    root.set('id', xml_root_attr_id)
    root.set('version', xml_root_attr_version)

    # repeat_dict = {'group_te3dx03' : { 'append_index' : 1, 'list' : toilet_info}}
    if repeat_dict:
        for key, val in repeat_dict.items():
            if val['list']:
                sub_ele = root.find(key)
                index = val['append_index']
                # create xml to be appened and append
                for sub_xml_dict in val['list']:
                    sub_xml_string = dicttoxml.dicttoxml(sub_xml_dict, attr_type=False, root=False)
                    # print('\n sub xml - %s -- '%index ,sub_xml_string)

                    sub_root = ET.fromstring(sub_xml_string)

                    sub_ele.insert(index, sub_root)
                    index = index + 1

    xml_string = ET.tostring(root, encoding="utf8", method='xml')
    # print('\n final xml -- ', xml_string)
    # write_log('created xml string to write')

    return root;


def create_xml_file(xml_root, filename, folderpath):
    file = filename + ".xml"
    xml_file = os.path.join(folderpath, file)

    directory = os.path.dirname(xml_file)

    if not os.path.exists(directory):
        os.makedirs(directory)

    xml_tree = ET.ElementTree(xml_root)

    xml_tree.write(xml_file, xml_declaration=True, encoding='utf-8', method="xml")

    log_msg = "created xml file : " + xml_file
    # write_log(log_msg)
    # print(log_msg)

    return;