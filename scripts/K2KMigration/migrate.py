''''
    Script to transfer data from one form to other.
     format.json - JSON format that is accepted by the new form.
     direct_mapping.json - JSON format - Fields that are directly mapped from new form to old form
     
    To run include the folder in sys path

    import sys
    sys.path.insert(0, 'scripts/K2KMigration/')
'''

import uuid
from django.conf import settings
import json
import urllib2
import itertools
import os
import dicttoxml
import xml.etree.ElementTree as ET

kobo_survey = '87'
root_folder_path = os.path.dirname(os.path.abspath(__file__))
root_output_folder = os.path.join(root_folder_path, 'xml_output')
output_folder_path = os.path.join(root_output_folder, 'KMC', 'RHS')

format = open(os.path.join(root_folder_path, 'format.json'),'r')
direct_mapping = open(os.path.join(root_folder_path, 'direct_mapping.json'), 'r')

def rhs_form():
    return json.loads(format.read())

def queryToFetchRecords(kobo_survey, slum_code):
    print "Start fetching the details"
    rec=[]
    slum_code = ''
    url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?format=json&query={"group_ce0hf58/slum_name":"' + slum_code + '"}'
    kobotoolbox_request = urllib2.Request(url)
    kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
    kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
    res = urllib2.urlopen(kobotoolbox_request)
    html = res.read()
    json_records = json.loads(html)
    grouped_records = itertools.groupby(sorted(json_records, key=lambda x: x['group_ce0hf58/slum_name']),
                                        key=lambda x: x["group_ce0hf58/slum_name"])
    records = {}
    for list_record in grouped_records:
        slum_house = list(list_record[1])
        grouped_house_records = itertools.groupby(sorted(slum_house, key=lambda x: int(x['group_ce0hf58/house_no'])),
                                            key=lambda x: int(x["group_ce0hf58/house_no"]))
        house = {}
        for list_house in grouped_house_records:
            house[list_house[0]] = list(list_house[1])

        records[list_record[0]] = house
    for k,v in records.iteritems():
      slum_code = k
      folder_path = os.path.join(output_folder_path, "slum_" + str(slum_code.replace('/', '')))
      for key,val in v.iteritems():
        record_sorted = sorted(val, key=lambda x: x['end'], reverse=True)
        record = record_sorted[0]
        create_data = rhs_xml_create(record)
        print create_data
        status, replace_data = kmc_rhs_xml_replace(create_data, record)

        if status:
            xml_string = create_xml_string(replace_data, [], record['_xform_id_string'], record['_xform_id_string'],
                                           record['__version__'])
            file_name = 'RHS_Survey_Slum_Id_' + str(slum_code.replace('/', '')) + '_House_code_' + str(key)

            create_xml_file(xml_string, file_name, folder_path)
    return rec

def rhs_xml_create(xml_record):
    gl_rhs_xml_dict = rhs_form()
    mapping =  json.loads(direct_mapping.read())
    for key, val in xml_record.iteritems():
        key = str(key)
        if not key.startswith('_'):
            split_ky = key.split('/')
            if split_ky[len(split_ky)-1] in mapping.keys():
                split_key = mapping[split_ky[len(split_ky)-1]].split('/')
                if len(split_key) == 1:
                    gl_rhs_xml_dict[split_key[0]] = val
                if len(split_key) == 2:
                    gl_rhs_xml_dict[split_key[0]][split_key[1]] = val
                if len(split_key) == 3:
                    gl_rhs_xml_dict[split_key[0]][split_key[1]][split_key[2]] = val
                if len(split_key) == 4:
                    gl_rhs_xml_dict[split_key[0]][split_key[1]][split_key[2]][split_key[3]] = val

    return gl_rhs_xml_dict

UNOCCUPIED_HOUSE = {'03' : '021', '04':'022', '05':'023', '06':'024', '07':'025'}
FACILITY_OF_SOLID_WASTE = {'01':'04', '02':'01', '03':'02', '04':'03', '05':'04', '06':'05', '07':'06'}
def kmc_rhs_xml_replace(rhs_record, record):
    flag=False
    '''Replacement for the records
    '''
    #rhs_record['meta']['deprecatedID'] = rhs_record['meta']['instanceID']
    rhs_record['meta']['instanceID'] = 'uuid:' + str(uuid.uuid4())
    if record['group_ce0hf58/Type_of_structure_occupancy'] in ['03','04','05','06','07']:
        rhs_record['Type_of_structure_occupancy'] = '02'
        rhs_record['Type_of_unoccupied_house'] = UNOCCUPIED_HOUSE[record['group_ce0hf58/Type_of_structure_occupancy']]
    else:
        rhs_record['Type_of_structure_occupancy'] = '03' if record['group_ce0hf58/Type_of_structure_occupancy']=='02' else '01'

    if rhs_record['Type_of_unoccupied_house'] and rhs_record['Type_of_unoccupied_house'] == '021':
        rhs_record['Parent_household_number'] = record['group_ye18c77/group_ud4em45/what_is_the_full_name_of_the_family_head_']

    if record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] < 100:
        rhs_record['group_el9cl08']['House_area_in_sq_ft'] = '01'
    elif 100 >= record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] < 200 :
        rhs_record['group_el9cl08']['House_area_in_sq_ft'] = '02'
    elif 200 >= record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] < 300:
        rhs_record['group_el9cl08']['House_area_in_sq_ft'] = '03'
    elif 300 >= record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] < 400:
        rhs_record['group_el9cl08']['House_area_in_sq_ft'] = '04'
    elif record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] >= 400:
        rhs_record['group_el9cl08']['House_area_in_sq_ft'] = '05'

    rhs_record['group_el9cl08']['Facility_of_solid_waste_collection'] = FACILITY_OF_SOLID_WASTE[record['group_ye18c77/group_yw8pj39/facility_of_waste_collection']]
    rhs_record['group_og5bx85']['Type_of_survey'] = '01'

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