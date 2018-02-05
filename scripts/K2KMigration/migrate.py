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
import commentjson
from bs4 import BeautifulSoup
import re
import datetime

kobo_survey = "73"
root_folder_path = os.path.dirname(os.path.abspath(__file__))
root_output_folder = os.path.join(root_folder_path, 'xml_output')
output_folder_path = os.path.join(root_output_folder, 'KMC', 'RHS')

def rhs_form():
    format = open(os.path.join(root_folder_path, 'format.json'), 'rw')
    return commentjson.loads(format.read())

def mapping_form():
    direct_mapping = open(os.path.join(root_folder_path, 'direct_mapping.json'), 'rw')
    return commentjson.loads(direct_mapping.read())

def queryToFetchRecords(kobo_survey):
    print "Start fetching the details"
    date_now = datetime.datetime.now()
    rec=[]
    #slum_code = '273425262402'
    #url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?format=json&query={"group_ce0hf58/slum_name":"' + slum_code + '"}'
    url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?format=json'
    kobotoolbox_request = urllib2.Request(url)
    kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
    kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
    res = urllib2.urlopen(kobotoolbox_request)
    html = res.read()
    json_records = json.loads(html)
    print (url)
    print ("Total count :- "+str(len(json_records)))
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
      print ("Slum - "+str(k) + "("+str(len(v.keys()))+")")
      date_slum = datetime.datetime.now()
      folder_path = os.path.join(output_folder_path, "slum_" + str(slum_code.replace('/', '')))
      for key,val in v.iteritems():
        #print ("\t" + str(key))
        record_sorted = sorted(val, key=lambda x: x['end'], reverse=True)
        flag=True
        for record_sort in record_sorted:
            if record_sort['group_ce0hf58/Type_of_structure_occupancy'] == "01" or (record_sort['group_ce0hf58/Type_of_structure_occupancy']!= "01" and flag):
                flag = False
                record = record_sort
                #record = record_sorted[0]
                create_data = rhs_xml_create(record)

                status, replace_data = kmc_rhs_xml_replace(create_data, record)

                if status:
                    xml_string = create_xml_string(replace_data, [], replace_data['_xform_id_string'], replace_data['_xform_id_string'],
                                                   replace_data['__version__'])
                    file_name = 'RHS_Survey_Slum_Id_' + str(slum_code.replace('/', '')) + '_House_code_' + str(key) +'_'+str(record['_id'])

                    create_xml_file(xml_string, file_name, folder_path)
      print "Slum time" + str(datetime.datetime.now() - date_slum)
    print "Total time" + str(datetime.datetime.now() - date_now)
    return rec

def rhs_xml_create(xml_record):
    gl_rhs_xml_dict = rhs_form()
    mapping =  mapping_form()
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

UNOCCUPIED_HOUSE = {"03" : "021", "04":"022", "05":"023", "06":"024", "07":"025"}
FACILITY_OF_SOLID_WASTE = {"01":"04", "02":"01", "03":"02", "04":"03", "05":"04", "06":"05", "07":"06"}
def kmc_rhs_xml_replace(rhs_record, record):
    flag=False
    '''Replacement for the records
    '''
    #rhs_record['meta']['deprecatedID'] = rhs_record['meta']['instanceID']

    rhs_record['Enter_household_number_again'] = record['group_ce0hf58/house_no']
    rhs_record['meta']['instanceID'] = 'uuid:' + str(uuid.uuid4())
    # RHS section
    if record['group_ce0hf58/Type_of_structure_occupancy'] in ["03","04","05","06","07"]:
        rhs_record['Type_of_structure_occupancy'] = "02"
        rhs_record['Type_of_unoccupied_house'] = UNOCCUPIED_HOUSE[record['group_ce0hf58/Type_of_structure_occupancy']]
    else:
        rhs_record['Type_of_structure_occupancy'] = "03" if record['group_ce0hf58/Type_of_structure_occupancy']=="02" else "01"

    if rhs_record['Type_of_unoccupied_house'] and rhs_record['Type_of_unoccupied_house'] == "021":

        parent_house = (record['group_ye18c77/group_ud4em45/what_is_the_full_name_of_the_family_head_'].strip())#.split(' ')
        #print record['group_ye18c77/group_ud4em45/what_is_the_full_name_of_the_family_head_']
        if re.search('[0-9]+',parent_house) != None:
            rhs_record['Parent_household_number'] = int(re.search('[0-9]+',parent_house).group(0))

    if rhs_record['Type_of_structure_occupancy'] != "01":
        rhs_record['group_el9cl08']['Type_of_water_connection'] =""
        rhs_record['group_og5bx85']['Full_name_of_the_head_of_the_household'] = ""

    if rhs_record['group_el9cl08']['Enter_the_10_digit_mobile_number'] and not re.search('^[0-9]{10}$|^[0-9]{12}$',
                                                                                         rhs_record[
                                                                                             'group_el9cl08'][
                                                                                             'Enter_the_10_digit_mobile_number']):
        rhs_record['group_el9cl08']['Enter_the_10_digit_mobile_number'] = ""

    if rhs_record['group_el9cl08']['Aadhar_number'] and not re.search('^[0-9]{12}$',
                                                                      rhs_record['group_el9cl08']['Aadhar_number']):
        #print "Aadhar"+ rhs_record['group_el9cl08']['Aadhar_number']
        rhs_record['group_el9cl08']['Aadhar_number'] = ""

    if rhs_record['Type_of_structure_occupancy'] == "01":
        rhs_record['group_og5bx85']['Type_of_survey'] = "01"

        if rhs_record['group_el9cl08']['Number_of_household_members'] and int(
                rhs_record['group_el9cl08']['Number_of_household_members']) > 20:
            print "Number of members" + rhs_record['group_el9cl08']['Number_of_household_members']
            rhs_record['group_el9cl08']['Number_of_household_members'] = 5

        if 'group_ye18c77/group_yw8pj39/house_area_in_sq_ft' in record:
            if record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] < 100:
                rhs_record['group_el9cl08']['House_area_in_sq_ft'] = "01"
            elif 100 <= record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] < 200 :
                rhs_record['group_el9cl08']['House_area_in_sq_ft'] = "02"
            elif 200 <= record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] < 300:
                rhs_record['group_el9cl08']['House_area_in_sq_ft'] = "03"
            elif 300 <= record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] < 400:
                rhs_record['group_el9cl08']['House_area_in_sq_ft'] = "04"
            elif record['group_ye18c77/group_yw8pj39/house_area_in_sq_ft'] >= 400:
                rhs_record['group_el9cl08']['House_area_in_sq_ft'] = "05"
        waste_facility =[]

        if 'group_ye18c77/group_yw8pj39/facility_of_waste_collection' in record and len(record['group_ye18c77/group_yw8pj39/facility_of_waste_collection'].split(' ')) > 0:
            #for waste_collection in record['group_ye18c77/group_yw8pj39/facility_of_waste_collection'].split(' '):
            #    waste_facility.append(FACILITY_OF_SOLID_WASTE[waste_collection])
            rhs_record['group_el9cl08']['Facility_of_solid_waste_collection'] = FACILITY_OF_SOLID_WASTE[record['group_ye18c77/group_yw8pj39/facility_of_waste_collection'].split(' ')[0]]#' '.join(waste_facility)


        # RHS and follow up survey data
        if 'group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet' in record:
            # if record['group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet'] == "01":
            #     if 'group_ye18c77/group_yw8pj39/Have_you_applied_for_indiviual' in record and record[
            #         'group_ye18c77/group_yw8pj39/Have_you_applied_for_indiviual'] == "01":
            #         if 'group_ye18c77/group_yw8pj39/what_is_the_status_of_toilet_under_sbm_' in record and record[
            #             'group_ye18c77/group_yw8pj39/what_is_the_status_of_toilet_under_sbm_'] == "01":
            #             rhs_record['group_oi8ts04']['C1'] = "01"
            #     elif 'group_ye18c77/group_yw8pj39/Have_you_applied_for_indiviual' in record and record[
            #         'group_ye18c77/group_yw8pj39/Have_you_applied_for_indiviual'] == "02":
            #         rhs_record['group_oi8ts04']['C2'] = "01"
            # elif record['group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet'] != "01":
            DEFECATION = {"01":"01","03": "09", "04": "10", "05": "11", "07": "12"}
            if record['group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet'] in DEFECATION.keys():
                rhs_record['group_oi8ts04']['C3'] = DEFECATION[
                    record['group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet']]
            else:
                print "ERRORRRRR :  "+record['group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet']

        if 'group_ye18c77/group_yw8pj39/If_Own_household_Toilet_type_' in record and record[
            'group_ye18c77/group_yw8pj39/If_Own_household_Toilet_type_'] == "01":
            rhs_record['group_oi8ts04']['Type_of_SBM_toilets'] = "01"

        TOILET_UNDER_SBM = {"01": "01", "02": "03", "03": "04", "04": "05"}
        if 'group_ye18c77/group_yw8pj39/what_is_the_status_of_toilet_under_sbm_' in record:
            rhs_record['group_oi8ts04']['Status_of_toilet_under_SBM'] = TOILET_UNDER_SBM[
                record['group_ye18c77/group_yw8pj39/what_is_the_status_of_toilet_under_sbm_']]

        TOILET_PREFERENCE = {"01": "01", "02": "02", "03": "02", "04": "02"}
        if 'group_ye18c77/group_yw8pj39/type_of_toilet_preference' in record:
            rhs_record['group_oi8ts04']['What_kind_of_toilet_would_you_like'] = TOILET_PREFERENCE[record[
                'group_ye18c77/group_yw8pj39/type_of_toilet_preference']]

        TOILET_CONNECTED_TO = {"01": "01", "02": "02", "03": "03", "04": "04", "05": "05", "06": "06", "07": "08",
                               "08": "08", "09": "07"}
        if 'group_ye18c77/group_yw8pj39/where_the_individual_toilet_is_connected_to_' in record:
            rhs_record['group_oi8ts04']['What_is_the_toilet_connected_to'] = TOILET_CONNECTED_TO[
                record['group_ye18c77/group_yw8pj39/where_the_individual_toilet_is_connected_to_']]

        OPEN_DEFECATION = {"01": "01", "02": "02", "03": "04", "04": "05"}
        if 'group_ye18c77/group_yw8pj39/does_any_member_of_your_family_go_for_open_defecation_' in record:
            rhs_record['group_oi8ts04']['OD1'] = OPEN_DEFECATION[
                record['group_ye18c77/group_yw8pj39/does_any_member_of_your_family_go_for_open_defecation_']]

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

    # fp_read = open(xml_file, 'r')
    # soup = BeautifulSoup((fp_read.read().replace('\n','')), 'xml')
    # fp_read.close()
    # try:
    #     d = soup.prettify()
    #     #print soup.prettify()
    #     fp_write = open(xml_file, 'w')
    #     fp_write.write(d)
    #     fp_write.close()
    # except Exception as e:
    #     print "Error"
    #     print e
    #     print xml_file


    log_msg = "created xml file : " + xml_file
    # write_log(log_msg)
    # print(log_msg)

    return;