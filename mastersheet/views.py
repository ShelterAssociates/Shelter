
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, JsonResponse
from mastersheet.forms import find_slum
from mastersheet.models import *
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
import itertools

from django import forms


from sponsor.models import *
from master.models import *
from django.views.decorators.csrf import csrf_exempt

import json

import urllib2


@csrf_exempt
def masterSheet(request, slum_code = 0 ):
    print "$$$$$$ In masterSheet view.... $$$$$$$$$$$"

    print request.POST.get('data')



    urlv = 'http://kc.shelter-associates.org/api/v1/data/130?query={"slum_name":"273425265502"}'
    url_family_factsheet = 'https://kc.shelter-associates.org/api/v1/data/68?format=json&query={"group_vq77l17/slum_name":"273425267703"}&fields=["OnfieldFactsheet","group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet","group_ne3ao98/Cost_of_upgradation_in_Rs","group_ne3ao98/Where_the_individual_ilet_is_connected_to","group_ne3ao98/Use_of_toilet","group_vq77l17/Household_number"]'
    #print ("Sending Request to", url_family_factsheet)
    kobotoolbox_request = urllib2.Request(urlv)
    kobotoolbox_request_family_factsheet = urllib2.Request(url_family_factsheet)
    kobotoolbox_request.add_header('Authorization', "OAuth2 c213f2e7a3221171e8dd501f0fd8153ad95ecd93 ")
    kobotoolbox_request_family_factsheet.add_header('Authorization', "OAuth2 c213f2e7a3221171e8dd501f0fd8153ad95ecd93 ")
    res = urllib2.urlopen(kobotoolbox_request)
    res_family_factsheet = urllib2.urlopen(kobotoolbox_request_family_factsheet)
    html = res.read()
    html_family_factsheet = res_family_factsheet.read()
    formdict = json.loads(html)
    formdict_family_factsheet =json.loads(html_family_factsheet)


    temp_FF={obj_FF['group_vq77l17/Household_number'] : obj_FF for obj_FF in formdict_family_factsheet}

    temp_FF_keys = temp_FF.keys()
    for x in formdict:
        if x['Household_number'] in temp_FF_keys:
            x.update(temp_FF[x['Household_number']])
            x['OnfieldFactsheet'] = 'Yes'

    toilet_reconstruction_fields = ['slum', 'household_number','agreement_date_str','agreement_cancelled','septic_tank_date_str','phase_one_material_date_str','phase_two_material_date_str','phase_three_material_date_str','completion_date_str','status','comment','material_shifted_to']
    daily_reporting_data = ToiletConstruction.objects.extra(select={'phase_one_material_date_str':"to_char(phase_one_material_date, 'YYYY-MM-DD HH24:MI:SS')",
                                                                    'phase_two_material_date_str': "to_char(phase_two_material_date, 'YYYY-MM-DD HH24:MI:SS')",
                                                                    'phase_three_material_date_str': "to_char(phase_three_material_date, 'YYYY-MM-DD HH24:MI:SS')",
                                                                    'septic_tank_date_str': "to_char(septic_tank_date, 'YYYY-MM-DD HH24:MI:SS')",
                                                                    'agreement_date_str': "to_char(agreement_date, 'YYYY-MM-DD HH24:MI:SS')",
                                                                    'completion_date_str': "to_char(completion_date, 'YYYY-MM-DD HH24:MI:SS')"}).filter(slum__shelter_slum_code=273425265502)
    daily_reporting_data = daily_reporting_data.values(*toilet_reconstruction_fields)

    temp_daily_reporting = {obj_DR['household_number']: obj_DR for obj_DR in daily_reporting_data}
    temp_DR_keys = temp_daily_reporting.keys()


    try:
        for x in formdict:
            if x['Household_number'] in temp_DR_keys:
                x.update(temp_daily_reporting[x['Household_number']])
    except Exception as err:
        print err

    sbm_fields = ['slum', 'household_number', 'name', 'application_id', 'photo_uploaded', 'created_date_str']
    sbm_data = SBMUpload.objects.extra(select={'created_date_str': "to_char(created_date, 'YYYY-MM-DD HH24:MI:SS')"}).filter(slum__shelter_slum_code=273425265502)
    sbm_data = sbm_data.values(*sbm_fields)

    temp_sbm = {obj_DR['household_number']: obj_DR for obj_DR in sbm_data}
    temp_sbm_keys = temp_sbm.keys()
    try:
        for x in formdict:
            if x['Household_number'] in temp_sbm_keys:
                x.update(temp_sbm[x['Household_number']])
    except Exception as err:
        print err

    community_mobilization_fields = ['slum', 'household_number','activity_type','activity_date_str']
    community_mobilization_data = CommunityMobilization.objects.extra(select={'activity_date_str': "to_char(activity_date, 'YYYY-MM-DD HH24:MI:SS')"}).filter(slum__shelter_slum_code=273425265502)
    community_mobilization_data = community_mobilization_data.values(*community_mobilization_fields)
    community_mobilization_data_list = list(community_mobilization_data)

    for x in community_mobilization_data_list:
        HH_list_flat=[]
        HH_list_flat.append(json.loads(x['household_number']))
        x['household_number'] = HH_list_flat[0]

    for y in community_mobilization_data_list:
        for z in y['household_number']:
            for x in formdict:
                if int(x['Household_number']) == int(z):
                    #print x
                    a = y.copy()
                    activity_type = a['activity_type']
                    new_activity_type = list(a.keys())[3]
                    new_activity_type = new_activity_type + '_' + str(activity_type)
                    a['activity_type'] = a['activity_date_str']
                    a[new_activity_type] = a.pop('activity_type')
                    x.update({new_activity_type : a['activity_date_str']})

    return HttpResponse(json.dumps(formdict),  content_type = "application/json")



def renderMastersheet(request):
    print "########### In renderMastersheet ###########"
    slum_search_field = find_slum()
    if request.method == 'POST':
        slum_code = Slum.objects.filter(pk = request.POST.get('slumname')).values_list("shelter_slum_code", flat = True)
        return render(request, 'masterSheet.html', {'form': slum_search_field,'slum_code':slum_code})

    return render(request, 'masterSheet.html', {'form': slum_search_field})













