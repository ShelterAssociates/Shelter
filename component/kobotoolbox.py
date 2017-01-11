import json
import urllib2
from django.conf import settings

def get_household_analysis_data(survey_id, slum_code):
    '''Gets the kobotoolbox RHS data for selected questions
    '''
    household_field = 'group_ce0hf58/house_no'
    #List of fields required for analysis
    fields = { 'group_ye18c77/group_yw8pj39/type_of_water_connection': 'type_of_water',
                'group_ye18c77/group_yw8pj39/facility_of_waste_collection': 'facility_of_waste'}

    #Setting up API call and header data
    url = settings.KOBOCAT_FORM_URL + 'data/'+ survey_id +'?query={"group_ce0hf58/slum_name":"'+slum_code+'"}&fields="'+ str(fields.keys() + [household_field] )+ '"'

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
        for key, field in fields.items():
            data = record[key]
            for val in data.split():
                if field not in output:
                    output[field] = {}
                if data not in output[field]:
                    output[field][data]=[]
                output[field][data].append(household_no)
    return output
