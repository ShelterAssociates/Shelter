import json
import urllib2
from django.conf import settings
import copy
from collections import OrderedDict

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
    data = json.loads(content)

    for val in data:
        for k,v in val.items():
            temp_arr[k]= v

    url1 = settings.KOBOCAT_FORM_URL+'forms/'+settings.KOBOCAT_RHS_SURVEY+'/form.json'
    req1 = urllib2.Request(url1)
    req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
    resp1 = urllib2.urlopen(req1)
    content1 = resp1.read()
    data1 = json.loads(content1)
    values=dictdata(data1)
    ans=""
    for k1,v1 in temp_arr.items():
        if 'group' in k1:
            c_split=k1.split('/')
            maindata=values.copy()
            for n in c_split:
                maindata=maindata['children'][n]
            try:
                ans=""
                if 'select' in maindata['type']:
                    for vall in v1.split():
                        ans+=str(maindata['children'][vall]['label']) +', '
                    ans = ans[:-2]
                else:
                    ans=v1
            except:
                ans=""
                pass

        if ans != "":
            output[maindata['label']]= ans
    return output


def get_kobo_RIM_detail(slum_code):
    url = settings.KOBOCAT_FORM_URL+'data/'+settings.KOBOCAT_RIM_SURVEY+'?query={"group_zl6oo94/group_uj8eg07/slum_name":"'+slum_code+'"}'

    req = urllib2.Request(url)
    req.add_header('Authorization', settings.KOBOCAT_TOKEN)
    resp = urllib2.urlopen(req)
    content = resp.read()
    data = json.loads(content)

    temp_arr = OrderedDict()
    temp_arr['General']=OrderedDict()
    temp_arr['Toilet']=OrderedDict()
    temp_arr['Water']=OrderedDict()
    temp_arr['Waste']=OrderedDict()
    temp_arr['Drainage']=OrderedDict()
    temp_arr['Gutter']=OrderedDict()
    temp_arr['Road']=OrderedDict()
    output=OrderedDict()

    RIM_GENERAL="group_zl6oo94"
    RIM_TOILET="group_te3dx03"
    RIM_WATER="group_zj8tc43"
    RIM_WASTE="group_ks0wh10"
    RIM_DRAINAGE="group_kk5gz02"
    RIM_GUTTER="group_bv7hf31"
    RIM_ROAD="group_xy9hz30"

    for val in data:
        for k,v in val.items():
            if RIM_GENERAL==k.split('/')[0]:
             temp_arr['General'][k]=v
            elif RIM_TOILET==k.split('/')[0]:
             temp_arr['Toilet'][k]=v
            elif RIM_WATER==k.split('/')[0]:
             temp_arr['Water'][k]=v
            elif RIM_WASTE==k.split('/')[0]:
             temp_arr['Waste'][k]=v
            elif RIM_DRAINAGE==k.split('/')[0]:
             temp_arr['Drainage'][k]=v
            elif RIM_GUTTER==k.split('/')[0]:
             temp_arr['Gutter'][k]=v
            elif RIM_ROAD==k.split('/')[0]:
             temp_arr['Road'][k]=v


    url1 = settings.KOBOCAT_FORM_URL+'forms/'+settings.KOBOCAT_RIM_SURVEY+'/form.json'
    req1 = urllib2.Request(url1)
    req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
    resp1 = urllib2.urlopen(req1)
    content1 = resp1.read()
    data1 = json.loads(content1)
    values=dictdata(data1)

    #*****************************************/

    ans=""
    for key,section_list in temp_arr.items():
        output[key]={}
        for k1,v1 in section_list.items():
            if 'group' in k1:
                c_split=k1.split('/')
                maindata=values.copy()
                for n in c_split:
                    maindata=maindata['children'][n]

                try:
                    ans=""
                    que=""
                    if 'select' in maindata['type']:
                        for vall in v1.split():
                            ans+=str(maindata['children'][vall]['label']) +', '
                        ans = ans[:-2]
                        que= maindata['label']
                    elif 'repeat' in maindata['type']:
                        que=[]

                        for val1 in v1:
                            que_dict={}
                            for kn1,vn1 in val1.items():
                                arr_kn1=kn1.split('/')
                                if 'select' in maindata['children'][arr_kn1[len(arr_kn1)-1]]['type']:
                                    ans=""
                                    for vall in vn1.split():
                                        ans+=str(maindata['children'][arr_kn1[len(arr_kn1)-1]]['children'][vall]['label']) +', '
                                    vn1 = ans[:-2]
                                    que_dict[maindata['children'][arr_kn1[len(arr_kn1)-1]]['label']]= vn1
                                else:
                                    que_dict[maindata['children'][arr_kn1[len(arr_kn1)-1]]['label']]= vn1

                            que.append(que_dict)

                    else:
                        ans=v1
                        que= maindata['label']
                    if type(que)==list:
                        output[key]=que
                    else:
                        output[key][que]=ans
                except:
                    ans=""
                    pass

    return output



def dictdata(data):

    data['children'] = dict((str(topic['name']), topic) for topic in data['children'])

    for k,v in data['children'].items():
        if 'children' in v:
            if isinstance(v['children'], list):
                v = dictdata(v)
    return data
