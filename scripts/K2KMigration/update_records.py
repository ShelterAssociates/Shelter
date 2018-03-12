''''
Update script to add current place of defecation by populating the calculate field in kobo.
import sys
sys.path.insert(0, 'scripts/K2KMigration/')
from update_records import *
fetch_data()
'''

from bs4 import BeautifulSoup
import os
import uuid
from django.conf import settings
import urllib2
import json
import dicttoxml
import xml.etree.ElementTree as ET
import commentjson

root_folder_path = os.path.dirname(os.path.abspath(__file__))
root_output_folder = os.path.join(root_folder_path, 'xml_output')
output_folder_path = os.path.join(root_output_folder, 'KMC', 'RHS_NEW')

kobo_survey = '130'

def rhs_form():
    format = open(os.path.join(root_folder_path, 'format.json'), 'rw')
    return commentjson.loads(format.read())

def fetch_data():
    url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?format=json'
    kobotoolbox_request = urllib2.Request(url)
    kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
    kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
    res = urllib2.urlopen(kobotoolbox_request)
    html = res.read()
    json_records = json.loads(html)
    print ("Total count : ",str(len(json_records)))
    count = 0
    for record in json_records:
        print(str(count))
        if record['Type_of_structure_occupancy'] == "01":
            create_data = rhs_xml_create(record)
            status, replace_data = replace_val(create_data)
            if status:
                count += 1
                #replace_data['__version__'] = record['__version__']
                xml_string = create_xml_string(replace_data, [], record['_xform_id_string'], record['_xform_id_string'], record['__version__'])
                file_name = replace_data['slum_name'] + '_'+ replace_data['Household_number'] + '_' +replace_data['meta']['instanceID']

                folder_path = os.path.join(output_folder_path, "slum_" + replace_data['slum_name'])
                create_xml_file(xml_string, file_name, folder_path)
    print (str(count))

def rhs_xml_create(xml_record):
    gl_rhs_xml_dict = rhs_form()
    for key, val in xml_record.iteritems():
        key = str(key)
        if not key.startswith('_'):
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

def replace_val(rhs_record):
    val =''
    flag = False
    if rhs_record['group_oi8ts04']['Have_you_applied_for_individua']=="01":
        if rhs_record['group_oi8ts04']['Status_of_toilet_under_SBM'] == "01":
            val = rhs_record['group_oi8ts04']['C1']
        elif rhs_record['group_oi8ts04']['Status_of_toilet_under_SBM'] in ['02','03','04']:
            val = rhs_record['group_oi8ts04']['C4']
        elif rhs_record['group_oi8ts04']['Status_of_toilet_under_SBM'] =="05":
            val = rhs_record['group_oi8ts04']['C5']
    elif rhs_record['group_oi8ts04']['Have_you_applied_for_individua']=="02":
        if rhs_record['group_oi8ts04']['C2']:
            if rhs_record['group_oi8ts04']['C2'] == "08":
                val = rhs_record['group_oi8ts04']['C3']
            else:
                val = rhs_record['group_oi8ts04']['C2']

    if val:
        if not rhs_record['group_oi8ts04']['Current_place_of_defecation']:
            flag = True
            rhs_record['group_oi8ts04']['Current_place_of_defecation'] = val
            rhs_record['meta']['deprecatedID'] = rhs_record['meta']['instanceID']
            rhs_record['meta']['instanceID'] = 'uuid:' + str(uuid.uuid4())

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
