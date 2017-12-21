''''
    Script to update PCMC RHS records for current place of defecation. 
    To run include the folder in sys path

    import sys
    sys.path.insert(0, 'scripts/update_kobo_records/')
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
output_folder_path = os.path.join(root_output_folder, 'PCMC', 'RHS')


def rhs_form():
    pass

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