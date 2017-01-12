import json
import urllib2
from django.conf import settings

def get_household_analysis_data(slum_code, fields):
    '''Gets the kobotoolbox RHS data for selected questions
    '''
    household_field = 'group_ce0hf58/house_no'

    #Setting up API call and header data
    url = settings.KOBOCAT_FORM_URL + 'data/'+ settings.KOBOCAT_RHS_SURVEY +'?query={"group_ce0hf58/slum_name":"'+slum_code+'"}&fields="'+ str(fields + [household_field] )+ '"'

    kobotoolbox_request = urllib2.Request(url)
    kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
    kobotoolbox_request.add_header('Authorization', 'Token ' + settings.KOBOCAT_TOKEN.split()[1])

    res = urllib2.urlopen(kobotoolbox_request)
    #Read json data from kobotoolbox API
    html = res.read()
    records = json.loads(html)

    output = {}
    #Process received data
    for record in records:
        household_no = record[household_field]
        for field in fields:
            if field != "":
                data = record[field]
                for val in data.split():
                    if field not in output:
                        output[field] = {}
                    if data not in output[field]:
                        output[field][data]=[]
                    if household_no not in output[field][data]:
                        output[field][data].append(household_no)
    return output
