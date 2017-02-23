import json
import urllib2
from django.conf import settings
import copy
from collections import OrderedDict
from itertools import chain

def get_household_analysis_data(slum_code, fields):
    '''Gets the kobotoolbox RHS data for selected questions
    '''
    household_field = 'group_ce0hf58/house_no'

    #Setting up API call and header data
    url = settings.KOBOCAT_FORM_URL + 'data/'+ settings.KOBOCAT_RHS_SURVEY +'?query={"group_ce0hf58/slum_name":"'+slum_code+'"}&fields="'+ str(fields + [household_field] )+ '"'

    kobotoolbox_request = urllib2.Request(url)
    kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
    kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)

    res = urllib2.urlopen(kobotoolbox_request)
    #Read json data from kobotoolbox API
    html = res.read()
    records = json.loads(html)

    output = {}
    #Process received data
    for record in records:
        household_no = record[household_field]
        for field in fields:
            if field != "" and field in record:

                data = record[field]
                for val in data.split():
                    if field not in output:
                        output[field] = {}
                    if data not in output[field]:
                        output[field][data]=[]
                    if household_no not in output[field][data]:
                        output[field][data].append(household_no)
    return output

def get_kobo_RHS_list(slum_code,house_number):

    # url="http://kc.shelter-associates.org/api/v1/forms?format=json"
    """Method which fetches the KoboCat ID's and URL's from the Kobo Toolbox API"""

    temp_arr={}
    output=OrderedDict()
    try:
        url = settings.KOBOCAT_FORM_URL+'data/'+settings.KOBOCAT_RHS_SURVEY+'?query={"group_ce0hf58/slum_name":"'+slum_code+'","group_ce0hf58/house_no":"'+house_number+'"}'
    except Exception as e:
        print e

    req = urllib2.Request(url)
    req.add_header('Authorization', settings.KOBOCAT_TOKEN)
    resp = urllib2.urlopen(req)
    content = resp.read()
    submission = json.loads(content)

    url1 = settings.KOBOCAT_FORM_URL+'forms/'+settings.KOBOCAT_RHS_SURVEY+'/form.json'
    req1 = urllib2.Request(url1)
    req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
    resp1 = urllib2.urlopen(req1)
    content1 = resp1.read()
    data1 = json.loads(content1)

    output = OrderedDict()
    for data in data1['children']:
        if data['type'] == "group":
            sect_form_data = trav(data)
            sub_key = [ str(k) for k in submission[0].keys() if data['name'] in k]
            for sect_form in sect_form_data:
                key = [x for x in sub_key if sect_form['name'] in x]
                if len(key)>0 and 'label' in sect_form:
                    ans = fetch_answer(sect_form, key, submission[0])
                    output[sect_form['label']]  = ans
    return output


def get_kobo_RIM_detail(slum_code):
    url = settings.KOBOCAT_FORM_URL+'data/'+settings.KOBOCAT_RIM_SURVEY+'?query={"group_zl6oo94/group_uj8eg07/slum_name":"'+slum_code+'"}'

    req = urllib2.Request(url)
    req.add_header('Authorization', settings.KOBOCAT_TOKEN)
    resp = urllib2.urlopen(req)
    content = resp.read()
    submission = json.loads(content)

    output=OrderedDict()

    RIM_GENERAL="group_zl6oo94"
    RIM_TOILET="group_te3dx03"
    RIM_WATER="group_zj8tc43"
    RIM_WASTE="group_ks0wh10"
    RIM_DRAINAGE="group_kk5gz02"
    RIM_GUTTER="group_bv7hf31"
    RIM_ROAD="group_xy9hz30"
    section = {RIM_GENERAL:"General", RIM_TOILET:"Toilet", RIM_WATER:"Water",
               RIM_WASTE:"Waste", RIM_DRAINAGE:"Drainage", RIM_GUTTER:"Gutter", RIM_ROAD:"Road"}

    url1 = settings.KOBOCAT_FORM_URL+'forms/'+settings.KOBOCAT_RIM_SURVEY+'/form.json'
    req1 = urllib2.Request(url1)
    req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
    resp1 = urllib2.urlopen(req1)
    content1 = resp1.read()
    data1 = json.loads(content1)
    #To maintain the order in which questions are displayed we iterate through the form data
    for data in data1['children']:
        if data['type'] == "group" and data['name'] in section.keys():
            #Group wise get the entire list for questions
            sect_form_data = trav(data)
            #Find the list of keys available in the submission data
            toil_keys = [ str(k) for k in submission[0].keys() if data['name'] in k]
            count = 1
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
            #Default values
            if data['name'] != RIM_TOILET:
                output[section[data['name']]] = OrderedDict()
            else:
                output[section[data['name']]] = []
                [output[section[data['name']]].append(OrderedDict()) for i in range(count)]
            #Iterate through the list of questions for the group
            for sect_form in sect_form_data:
                key = [x for x in sub_key if sect_form['name'] in x]
                #Check if the question has answer in the submission then only proceed further
                if len(key)>0 and 'label' in sect_form:
                    if data['name'] != RIM_TOILET:
                        #Fetch the answer for select one/text/select multiple type question
                        ans = fetch_answer(sect_form, key, submission[0])
                        output[data['label']][sect_form['label']]  = ans
                    else:
                        #For toilet repeative section append the set of questions for all the CTB's if available
                        for ind in range(count):
                            if key[0] in sub[ind].keys():
                                ans = fetch_answer(sect_form, key, sub[ind])
                                output[section[data['name']]][ind][sect_form['label']] = ans

    return output

def fetch_answer(sect_form, key, submission):
    #Fetch answer and convert it to label
    val = ""
    if 'select' in sect_form['type'] and type(key[0]) != list and 'children' in sect_form:
        options = dict((opt['name'], opt['label']) for opt in sect_form['children'])
        sub_option = submission[key[0]].split(' ')
        val = options[sub_option[0]]
        if len(sub_option) > 1:
            val = reduce(lambda x,y: options[x] +',' + options[y], sub_option)
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
