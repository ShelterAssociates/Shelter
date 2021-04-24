import json
from urllib import request as urllib2
from django.conf import settings
import copy
from collections import OrderedDict
from itertools import chain
from collections import Counter
from master.models import SURVEYTYPE_CHOICES, Survey
from django.shortcuts import get_object_or_404
from graphs.models import *
import itertools

def survey_mapping(survey_type):
    def real_decorator(function):
        def wrapper(*args, **kwargs):
            city_id = args[0]
            try:
                survey = Survey.objects.filter(city__id=city_id, survey_type=survey_type)
            except:
                survey = None
            kwargs['kobo_survey'] = ''
            if survey:
                kwargs['kobo_survey'] =  survey[0].kobotool_survey_id
            return function(*args, **kwargs)
        return wrapper
    return real_decorator

#@survey_mapping(SURVEYTYPE_CHOICES[1][0])
def get_household_analysis_data(city, slum_code, fields, kobo_survey=''):
    '''Gets the kobotoolbox RHS data for selected questions
    '''
    household_field = 'Household_number'
    output = {}
    slum = get_object_or_404(Slum, id=slum_code)
    household_data = HouseholdData.objects.filter(slum=slum)
    records = map(lambda x:x.rhs_data, household_data)
    records = filter(lambda x: x!=None, records)
    grouped_records = itertools.groupby(sorted(records, key=lambda x:int(x['Household_number'])), key=lambda x:int(x["Household_number"]))

    for household, list_record in grouped_records:
        record_sorted = list(list_record) #sorted(list(list_record), key=lambda x:x['_submission_time'], reverse=False)
        household_no = int(household)
        if len(record_sorted)>0:
            record = record_sorted[0]
        for field in fields:
            if field != "" and field in record:
                if field == 'group_el9cl08/Ownership_status_of_the_house' in record and record['Type_of_structure_occupancy'] == 'Shop': pass
                elif 'group_el9cl08/Type_of_structure_of_the_house' in record and record['Type_of_structure_occupancy'] == 'Shop':pass
                elif 'Type_of_structure_occupancy' in record and record['Type_of_structure_occupancy'] == 'Shop':pass
                else:
                    data = record[field]
                    for val in data.split():
                        if field not in output:
                            output[field] = {}
                        if data not in output[field]:
                            output[field][data]=[]
                        if household_no not in output[field][data]:
                            output[field][data].append(str(household_no))
                
    return output

def format_data(rhs_data):
    new_rhs = {}
    remove_list = ['Name_s_of_the_surveyor_s', 'Date_of_survey', '_xform_id_string', 'meta/instanceID', 'end', 'start',
    'Enter_household_number_again','_geolocation', 'meta/deprecatedID', '_uuid', '_submitted_by', 'admin_ward', '_status',
    'formhub/uuid', '__version__','_submission_time', '_id', '_notes', '_bamboo_dataset_id', '_tags', 'slum_name', '_attachments',
    'OD1', 'C1', 'C2', 'C3','Household_number', '_validation_status']

    seq = {'group_el9cl08/Number_of_household_members': 'Number of household members',
     'group_oi8ts04/Have_you_applied_for_individua': 'Have you applied for an individual toilet under SBM?',
     'group_oi8ts04/Current_place_of_defecation': 'Current place of defecation',
     'group_el9cl08/Type_of_structure_of_the_house': 'Type of structure of the house',
     'group_oi8ts04/What_is_the_toilet_connected_to': 'What is the toilet connected to',
     'Household_number': 'Household number',
     'group_el9cl08/Type_of_water_connection': 'Type of water connection',
     'group_el9cl08/Facility_of_solid_waste_collection': 'Facility of solid waste collection',
     'group_el9cl08/Ownership_status_of_the_house': 'Ownership status of the house',
     'group_el9cl08/Does_any_household_m_n_skills_given_below': 'Does any household member have any of the construction skills given below?',
     'group_el9cl08/Enter_the_10_digit_mobile_number':'Mobile number',
     'group_el9cl08/House_area_in_sq_ft': 'House area in sq. ft.','group_og5bx85/Type_of_survey': 'Type of survey',
     'group_og5bx85/Full_name_of_the_head_of_the_household': 'Full name of the head of the household',
     'group_el9cl08/Do_you_have_any_girl_child_chi': 'Do you have any girl child/children under the age of 18?',
     'Type_of_structure_occupancy': 'Type of structure of the house',
     'group_oi8ts04/Are_you_interested_in_an_indiv': 'Are you interested in an individual toilet?'
     }
    for i in remove_list:
        if i in rhs_data:
            rhs_data.pop(i)
    for k, v in seq.items():
        try:
            new_rhs[v] = rhs_data[k]
        except Exception as e:pass
    return new_rhs

@survey_mapping(SURVEYTYPE_CHOICES[1][0])
def get_kobo_RHS_list(city, slum, house_number, kobo_survey=''):
    """Method which fetches RHS data using the Kobo Toolbox API. Data contains question and answer decrypted. """
    output=OrderedDict()
    household_data = HouseholdData.objects.filter(slum=slum,household_number=house_number).order_by('submission_date')
    if len(household_data)>0:
        output = format_data(household_data[0].rhs_data)
    #if kobo_survey:
        #try:
        #    url = settings.KOBOCAT_FORM_URL+'data/'+kobo_survey+'?format=json&query={"slum_name":"'+slum_code+'","Household_number":{"$in":["'+str(house_number)+'","'+('000'+str(house_number))[-4:]+'"]}}'
        #except Exception as e:
        #    print(e)
        #req = urllib2.Request(url)
        #req.add_header('Authorization', settings.KOBOCAT_TOKEN)
        #resp = urllib2.urlopen(req)
        #content = resp.read()
        #submission = json.loads(content)

        #url1 = settings.KOBOCAT_FORM_URL+'forms/'+kobo_survey+'/form.json'
        #req1 = urllib2.Request(url1)
        #req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
        #resp1 = urllib2.urlopen(req1)
        #content1 = resp1.read()
        #data1 = json.loads(content1)

        #output = OrderedDict()
        #if len(submission) > 0:
        #    for data in data1['children']:
        #        if data['type'] == "group":
        #            sect_form_data = trav(data)
        #            sub_key = [ str(k) for k in submission[0].keys() if data['name'] in k]
        #            for sect_form in sect_form_data:
        #                key = [x for x in sub_key if x.endswith(sect_form['name'])]
        #                if len(key)>0 and 'label' in sect_form:
        #                    ans = fetch_answer(sect_form, key, submission[0])
        #                    output[sect_form['label']]  = ans
    return output

@survey_mapping(SURVEYTYPE_CHOICES[0][0])
def get_kobo_RIM_detail(city, slum_code, kobo_survey=''):
    """Method to get RIM data from kobotoolbox using the API. Data contains question and answer decrypted.
    """
    output=OrderedDict()
    if kobo_survey:
        url = settings.KOBOCAT_FORM_URL+'data/'+kobo_survey+'?format=json&query={"group_zl6oo94/group_uj8eg07/slum_name":"'+slum_code+'"}'
        req = urllib2.Request(url)
        req.add_header('Authorization', settings.KOBOCAT_TOKEN)
        resp = urllib2.urlopen(req)
        content = resp.read()
        submission = json.loads(content)

        url1 = settings.KOBOCAT_FORM_URL+'forms/'+kobo_survey+'/form.json'
        req1 = urllib2.Request(url1)
        req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
        resp1 = urllib2.urlopen(req1)
        content1 = resp1.read()
        form_data = json.loads(content1)
        #To maintain the order in which questions are displayed we iterate through the form data
        if len(submission) > 0:
            output = parse_RIM_data(submission, form_data)
    return output

def parse_RIM_data(submission, form_data):
    """
    parse RIM data function used in get_kobo_RIM_detail(function above)
    :param submission: 
    :param form_data: 
    :return: 
    """
    output = OrderedDict()
    RIM_GENERAL = "group_zl6oo94"
    RIM_TOILET = "group_te3dx03"
    RIM_WATER = "group_zj8tc43"
    RIM_WASTE = "group_ks0wh10"
    RIM_DRAINAGE = "group_kk5gz02"
    RIM_GUTTER = "group_bv7hf31"
    RIM_ROAD = "group_xy9hz30"
    section = {RIM_GENERAL: "General", RIM_TOILET: "Toilet", RIM_WATER: "Water",
               RIM_WASTE: "Waste", RIM_DRAINAGE: "Drainage", RIM_GUTTER: "Gutter", RIM_ROAD: "Road"}

    for data in form_data['children']:
        if data['type'] == "group" and data['name'] in section.keys():
            #Group wise get the entire list for questions
            sect_form_data = trav(data)
            #Find the list of keys available in the submission data
            toil_keys = [ str(k) for k in submission[0].keys() if data['name'] in k]
            count = 0
            sub_key = []
            sub = []
            # Needed for toilet section which has repeat section
            for sub_k in toil_keys:
                if type(submission[0][sub_k]) == list:
                    count = len(submission[0][sub_k])
                    sub = submission[0][sub_k]
                    sub_key.extend(sum([list(k.keys()) for k in submission[0][sub_k]], []))
                else:
                    sub_key.append(sub_k)
            #Default values
            if data['name'] != RIM_TOILET:
                output[section[data['name']]] = OrderedDict()
            else:
                output[section[data['name']]] = []
                [output[section[data['name']]].append(OrderedDict()) for i in range(count)]
            #Iterate through the list of questions for the group
            for sect_form in sect_form_data:
                key = [x for x in sub_key if x.endswith(sect_form['name'])]
                #Check if the question has answer in the submission then only proceed further
                if len(key)>0 and 'label' in sect_form:
                    if data['name'] != RIM_TOILET:
                        #Fetch the answer for select one/text/select multiple type question
                        ans = fetch_answer(sect_form, key, submission[0])
                        output[section[data['name']]][sect_form['label']]  = ans
                    else:
                        #For toilet repeative section append the set of questions for all the CTB's if available
                        for ind in range(count):
                            output[section[data['name']]][ind][sect_form['label']] = ""
                            if key[0] in sub[ind].keys():
                                ans = fetch_answer(sect_form, key, sub[ind])
                                output[section[data['name']]][ind][sect_form['label']] = ans
    return output

@survey_mapping(SURVEYTYPE_CHOICES[0][0])
def get_kobo_RIM_report_detail(city, slum_code, kobo_survey=''):
    """Method to get RIM data from kobotoolbox using the API. Data contain only answers decrypted.
    """
    output=OrderedDict()
    RIM_TOILET="group_te3dx03"
    if kobo_survey:
        url = settings.KOBOCAT_FORM_URL+'data/'+kobo_survey+'?format=json&query={"group_zl6oo94/group_uj8eg07/slum_name":"'+slum_code+'"}'
        req = urllib2.Request(url)
        req.add_header('Authorization', settings.KOBOCAT_TOKEN)
        resp = urllib2.urlopen(req)
        content = resp.read()
        submission = json.loads(content)

        url1 = settings.KOBOCAT_FORM_URL+'forms/'+kobo_survey+'/form.json'
        req1 = urllib2.Request(url1)
        req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
        resp1 = urllib2.urlopen(req1)
        content1 = resp1.read()
        data1 = json.loads(content1)
        #To maintain the order in which questions are displayed we iterate through the form data
        if len(submission) > 0:
            output = parse_RIM_answer(submission, data1)
    return output

def parse_RIM_answer(submission, data1):
    """
    parse RIM answer function used in get_kobo_RIM_report_detail(function above).
    :param submission:
    :param form_data:
    :return:
    """
    RIM_TOILET = "group_te3dx03"
    output = OrderedDict()
    for data in data1['children']:
        if data['type'] == "group":
            # Group wise get the entire list for questions
            sect_form_data = trav(data)
            # Find the list of keys available in the submission data
            toil_keys = [str(k) for k in submission[0].keys() if data['name'] in k]
            count = 0
            sub_key = []
            sub = []
            # Needed for toilet section which has repeat section
            for sub_k in toil_keys:
                if type(submission[0][sub_k]) == list:
                    count = len(submission[0][sub_k])
                    sub = submission[0][sub_k]
                    sub_key.extend(sum([list(k.keys()) for k in submission[0][sub_k]], []))
                else:
                    sub_key.append(sub_k)

            # Iterate through the list of questions for the group
            for sect_form in sect_form_data:
                output[sect_form['name']] = ""
                key = [x for x in sub_key if x.endswith(sect_form['name'])]
                # Check if the question has answer in the submission then only proceed further
                if len(key) > 0 and 'label' in sect_form:
                    if data['name'] != RIM_TOILET:
                        # Fetch the answer for select one/text/select multiple type question
                        ans = fetch_answer(sect_form, key, submission[0])
                        output[sect_form['name']] = ans
                    else:
                        # For toilet repeative section append the set of questions for all the CTB's if available
                        if key[0] in submission[0].keys():
                            ans = fetch_answer(sect_form, key, submission[0])
                            output[sect_form['name']] = ans
                        else:
                            arr_ans = []
                            for ind in range(count):
                                if key[0] in sub[ind].keys():
                                    ans = fetch_answer(sect_form, key, sub[ind])
                                    if ans:
                                        arr_ans.extend(ans.split(','))

                            ans = ""
                            if 'integer' in sect_form['type']:
                                ans = sum(map(int, arr_ans))
                            else:
                                c = Counter(arr_ans)
                                ans = ', '.join(["{}({})".format(x, y) for x, y in c.items()])
                            output[sect_form['name']] = ans
    return output

def parse_RIM_answer_with_toilet(submission, data1):
    """
    parse RIM answer function used in sync record in graphs sync data. This gives array of toilet and does not aggregates it.
    :param submission:
    :param form_data:
    :return:
    """
    RIM_ADMIN = "group_ws5ux48"
    output = OrderedDict()
    RIM_GENERAL = "group_zl6oo94"
    RIM_TOILET = "group_te3dx03"
    RIM_WATER = "group_zj8tc43"
    RIM_WASTE = "group_ks0wh10"
    RIM_DRAINAGE = "group_kk5gz02"
    RIM_GUTTER = "group_bv7hf31"
    RIM_ROAD = "group_xy9hz30"
    section = { RIM_GENERAL: "General", RIM_TOILET: "Toilet", RIM_WATER: "Water",
               RIM_WASTE: "Waste", RIM_DRAINAGE: "Drainage", RIM_GUTTER: "Gutter", RIM_ROAD: "Road"}

    output = OrderedDict()
    for data in data1['children']:
        if data['type'] == "group" and data['name'] in section.keys():
            # Group wise get the entire list for questions
            sect_form_data = trav(data)
            # Find the list of keys available in the submission data
            toil_keys = [str(k) for k in submission[0].keys() if data['name'] in k]
            count = 0
            sub_key = []
            sub = []
            # Needed for toilet section which has repeat section
            for sub_k in toil_keys:
                if type(submission[0][sub_k]) == list:
                    count = len(submission[0][sub_k])
                    sub = submission[0][sub_k]
                    sub_key.extend(sum([k.keys() for k in submission[0][sub_k]], []))
                else:
                    sub_key.append(sub_k)

            if data['name'] != RIM_TOILET:
                output[section[data['name']]] = OrderedDict()
            else:
                output[section[data['name']]] = []
                [output[section[data['name']]].append(OrderedDict()) for i in range(count)]

            # Iterate through the list of questions for the group
            for sect_form in sect_form_data:
                key = [x for x in sub_key if x.endswith(sect_form['name'])]
                # Check if the question has answer in the submission then only proceed further
                if len(key) > 0 and 'label' in sect_form:
                    if data['name'] != RIM_TOILET:
                        # Fetch the answer for select one/text/select multiple type question
                        ans = fetch_answer(sect_form, key, submission[0])
                        output[section[data['name']]][sect_form['name']]  = ans
                    else:
                        for ind in range(count):
                            #output[data['name']][ind][sect_form['label']] = ""
                            if key[0] in sub[ind].keys():
                                ans = fetch_answer(sect_form, key, sub[ind])
                                output[section[data['name']]][ind][sect_form['name']] = ans
    return output


@survey_mapping(SURVEYTYPE_CHOICES[3][0])
def get_kobo_FF_report_detail(city, slum_code,house_number, kobo_survey=''):
    """Method which fetches family factsheet data from kobotoolbox using the API's. Data contain only answers decrypted."""
    output=OrderedDict()
    if kobo_survey:
        householdData = HouseholdData.objects.filter(slum__shelter_slum_code = slum_code, household_number = str(house_number)).exclude(ff_data=None)
        if len(householdData) > 0 and householdData[0].ff_data:
            output = householdData[0].ff_data
            for key in list(output):
                split_key = key.split('/')
                if len(split_key) > 1:
                    output[split_key[-1:][0]] = output[key]
                    output.pop(key)
            if "_attachments" in output:
                for photo in output["_attachments"]:
                    if 'Toilet_Photo' in output and output["Toilet_Photo"] in photo["filename"]:
                        output["Toilet_Photo"] = settings.BASE_URL +'media/original?media_file=' + photo["filename"]
                    if 'Family_Photo' in output and output["Family_Photo"] in photo["filename"]:
                        output["Family_Photo"] = settings.BASE_URL +'media/original?media_file=' + photo["filename"]
    return output

@survey_mapping(SURVEYTYPE_CHOICES[3][0])
def get_kobo_FF_report_detail1(city, slum_code,house_number, kobo_survey=''):
    """Method which fetches family factsheet data from kobotoolbox using the API's. Data contain only answers decrypted."""
    output=OrderedDict()
    if kobo_survey:
        try:
            url = settings.KOBOCAT_FORM_URL+'data/'+kobo_survey+'?format=json&query={"group_vq77l17/slum_name":"'+slum_code+'","group_vq77l17/Household_number":{"$in":["'+house_number+'","'+('000'+house_number)[-4:]+'"]}}'
        except Exception as e:
            print(e)

        req = urllib2.Request(url)
        req.add_header('Authorization', settings.KOBOCAT_TOKEN)
        resp = urllib2.urlopen(req)
        content = resp.read()
        submission = json.loads(content)

        url1 = settings.KOBOCAT_FORM_URL+'forms/'+kobo_survey+'/form.json'
        req1 = urllib2.Request(url1)
        req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
        resp1 = urllib2.urlopen(req1)
        content1 = resp1.read()
        data1 = json.loads(content1)

        output = OrderedDict()
        if len(submission) > 0:
            for data in data1['children']:
                if data['type'] == "group" or data['type'] == "photo" or data['type'] == "text":
                    sect_form_data = trav(data)
                    sub_key = [ str(k) for k in submission[0].keys() if data['name'] in k] + ['_attachments']
                    for sect_form in sect_form_data:
                        output[sect_form['name']] = ""
                        key = [x for x in sub_key if x.endswith(sect_form['name'])]
                        if len(key)>0 and 'name' in sect_form:
                            ans = fetch_answer(sect_form, key, submission[0])
                            output[sect_form['name']]  = ans

    return output

def fetch_answer(sect_form, key, submission):
    #Fetch answer and convert it to label
    val = ""
    if 'select' in sect_form['type'] and type(key[0]) != list and 'children' in sect_form:
        options = dict((str(opt['name']), str(opt['label'])) for opt in sect_form['children'])
        sub_option = submission[key[0]].split(' ')
        val = []
        if len(sub_option) > 0:
            for sub in sub_option:
                if sub in options:
                    val.append(str(options[sub]))
        val = ', '.join(val)
    elif 'photo' in sect_form['type']:
        photos = submission['_attachments']
        val = [photo['download_url'] for photo in photos if submission[key[0]] in photo['filename']]
        if val and len(val)>0:
            val = val[0]
    else:
        val = submission[key[0]]
    return val

def trav(node):
    #Traverse uptill the child node and add to list
    if 'type' in node and node['type'] == "group" or node['type'] == "repeat":
        return list(chain.from_iterable([trav(child) for child in node['children']]))
    else:
        return [node]

def dictdata(data):
    #convert childrens to dictionary for parsing
    data['children'] = dict((str(topic['name']), topic) for topic in data['children'])

    for k,v in data['children'].items():
        if 'children' in v:
            if isinstance(v['children'], list):
                v = dictdata(v)
    return data
