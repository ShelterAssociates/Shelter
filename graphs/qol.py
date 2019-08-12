from __future__ import division
from django.shortcuts import render
from graphs.models import  *
import json
from django.http import HttpResponse, HttpResponseForbidden

waste_coll_to_type = {'frequency_of_waste_collection_001':'ulb ghantagadi','frequency_of_waste_collection':'mla sponsored tempo',
              'frequency_of_waste_collection_':'ulb Van','frequency_of_waste_collection__002':'door to door waste collection',
              'frequency_of_waste_collection__001':'garbage bin'}
# waste_all_scores = []
def score_calculation(section_key ):
    all_slums_list=[]
    json_data = json.loads(open('graphs/reference_file.json').read())  # {u'Waste': {u'facility_of_wa...},u'Road':{.....}}

    # section_key = 'Road'
    slum_data = SlumData.objects.all().values('slum_id','rim_data')
    for i in slum_data[0:10]:
        slum__id = i['slum_id']
        db_data = json.loads( i['rim_data'])
        for k, v in json_data.items():
            if k == section_key:                      #section_key
                if k in db_data.keys():
                    score_list = []
                    ques = db_data[k]
                    # print ques
                    num_dict = {}
                    if type(ques) == dict:
                        ques = [ques]
                    for i in ques:
                        ques_score = []
                        waste_coll = {}
                        road_list =[]
                        for k1, v1 in v.items():
                            if k1 in i:
                                # print k1
                                if v1['calculate']['type'] == 's':
                                    score = single_select(i,k1, v1)
                                    if score != None:
                                        ques_score.append(score)
                                    else:
                                        ques_score.append(0)
                                    if k1 == 'presence_of_roads_within_the_s':
                                        road_list.append({'presence' : score})
                                    elif k1 == 'type_of_roads_within_the_settl':
                                        road_list.append({'road_type': score})
                                    else:
                                        score_list.append(score)
                                    if k == 'Waste':
                                        try:
                                            if k1 in waste_coll_to_type.keys():
                                                keyy = waste_coll_to_type[k1]
                                                # dat = [db_data[k][k1].lower()]
                                                score_for = v1['choices'][db_data[k][k1].lower()]
                                                waste_coll[keyy]= score_for
                                            else:
                                                coverage = v1['choices'][db_data[k][k1].lower()]
                                                cov_freq = [waste_coll, coverage]
                                        except Exception as e:
                                            print 'exception is', e

                                if v1['calculate']['type'] == 'M':
                                    score = multiselect(i,k1,v1)
                                    if score != None:
                                        ques_score.append(score)
                                    else:
                                        ques_score.append(0)
                                    if k == 'Waste':
                                        if k1 == 'facility_of_waste_collection':
                                            choices = v1['choices']
                                            ans = db_data[k][k1]
                                            ans = list(ans.split(','))
                                            ans =[ans,choices]
                                    if k == 'Road':
                                        if k1 != 'average_width_of_internal_road':
                                            road_list.append(score)
                                        else:
                                            score_list.append(score)
                                    else:
                                        score_list.append(score)

                                if v1['calculate']['type'] == 'N':
                                    data = i[k1]
                                    num_dict[k1]= data
                                    # print 'num_dict', num_dict
                                if v1['calculate']['type'] == 'C':
                                    pass
                                   # print 'calculate type ques'
                else:
                    pass
        for_each_slum = []
        if section_key == 'Waste':
            for_each_slum.append([score_list, num_dict, ans, cov_freq,slum__id])
            all_slums_list.append(for_each_slum)

        if section_key == 'Water':
            for_each_slum.append([score_list, num_dict, slum__id])
            all_slums_list.append(for_each_slum)

        if section_key == 'Road':
            for_each_slum.append([score_list, road_list, slum__id])
            all_slums_list.append(for_each_slum)
    return all_slums_list
    # return HttpResponse(json.dumps(all_slums_list), content_type="application/json")

def multiselect(db_data,k1,v1):
    avg=[]
    ans = db_data[k1]      # pucca
    ans = ans.split(',')
    try:
        for i in ans:
            i = (i.lower()).strip()
            if i in v1['choices']:
                score = v1['choices'][i]
                avg.append(score)
        score = sum(avg)/len(avg)
        if k1 == 'finish_of_the_road':
            score = { k1 : score}
    except Exception as e:
        print 'multi', ans, k1
        score = 0
    return score

def road_final(z):
    road_all_scores = []
    dumy_di = {}
    prsn_of_rd = 0
    road_type =0
    finish_of_road=0
    score_data =score_calculation('Road')
    for i in score_data:
        scores = i[0][0]
        a = i[0][1]
        id = i[0][2]
        for i in a:
            if 'presence' in i.keys():
                prsn_of_rd = i['presence']
            if 'road_type' in i.keys():
                road_type = i['road_type']
            if 'finish_of_the_road' in i.keys():
                finish_of_road = i.values()
                a = road_type * finish_of_road          # O/P IS LIST
        final_score = prsn_of_rd * ( a[0] + sum(scores))
        dumy_di[id]=final_score
    road_all_scores.append(dumy_di)
    return road_all_scores
    # return HttpResponse(json.dumps(road_all_scores), content_type="application/json")

def water_final(z):
    num_score=[]
    lst = []
    water_all_scores = []
    dumy_di = {}
    connection_score ={'Individual connection':5,'Shared connection':4,'Hand Pump':2,'Well':2,'Water Tanker':2,
                       'Water standpost':2,'From other settlements':-2,'No Service':-5,'None':0}
    Wc_in_use =['total_number_of_handpumps_in_u','total_number_of_taps_in_use_n','Total_number_of_standposts_in_']

    score_data = score_calculation('Water')
    for i in score_data:
        numeric_data = i[0][1]
        c = sum(i[0][0])                              #single_select_scores
        id = i[0][2]
        for i in Wc_in_use:
            if i in numeric_data.keys():
                num_score.append(int(numeric_data[i]))
        b = sum(num_score)                          #SUM(Type of Water Collection Weights)

        water_info = Rhs_data(id)
        if 'Water' in water_info.keys():
            data = water_info['Water']  #count of working facilities = {u'Water standpost': 28, 'None': 182, u'Shared connection': 123, u'Individual connection': 1332}
            # print  data
        for i in data:
            if i in connection_score.keys():
                s = connection_score[i] * data[i]       #Count of Working Water Facilities*Type of Connection
                lst.append(s)
        a = sum(lst)/len(lst)                               # s/b
        try:
            # print 'a=',a,'b=',b,'c=',c
            final_score = (a/b)+c
        except Exception as e:
            print e
            final_score = 0
        # print final_score
        dumy_di[id]= final_score
        water_all_scores.append(dumy_di)
    return water_all_scores
    # return HttpResponse(json.dumps('l'), content_type="application/json")

def waste_final(z):
    scr = []
    waste_all_scores=[]
    dumy_di={}
    score_data = score_calculation('Waste')
    for i in score_data:
        scores = i[0][0]
        numeric_data = i[0][1]
        facility_available = i[0][2]
        wst_coll_type = i[0][3]
        id = i[0][4]
        waste_info = Rhs_data(id)
        if 'Waste' in waste_info.keys():
            data = waste_info['Waste']
            HC = data[0]
            Count_of_facility = data[1]
            for i in facility_available[0]:
                i = i.strip()
                if i.lower() in wst_coll_type[0]:
                    freqq = wst_coll_type[0][i.lower()]

                if i.lower() in facility_available[1].keys():
                    weight = facility_available[1][i.lower()]

                    if i in ['ULB ghantagadi','ULB van']:
                        i = 'ULB service'
                    if i in Count_of_facility:
                        scr.append((Count_of_facility[i]/HC)*weight*freqq*wst_coll_type[1])
        #formula = avg(Count of Each Facility * Type of Facility * Frequency of Collection * Coverage of Collection)
        final_score = sum(scr)/len(scr)
        dumy_di[id] = final_score
        waste_all_scores.append(dumy_di)
    return waste_all_scores
    # return HttpResponse(json.dumps(wst_coll_type), content_type="application/json")

def Rhs_data(slumid):
    waste_data = []
    WCT=[]
    rhs_data = HouseholdData.objects.filter(slum__id=slumid)
    db_data = (map(lambda x: x.rhs_data, rhs_data))
    # data = {x['Household_number']: x for x in db_data}  # dictionary with Household number as key
    # print 'Household no to data dict', data
    SHC = len(rhs_data)                  # Slums_Household_count
    for i in db_data:
        if 'group_el9cl08/Facility_of_solid_waste_collection' in i:
            waste_data.append(i['group_el9cl08/Facility_of_solid_waste_collection'])
        else:
            waste_data.append('None')
    waste_counter ={i : waste_data.count(i) for i in waste_data}
    for i in db_data:
        if 'group_el9cl08/Type_of_water_connection' in i:
            WCT.append(i['group_el9cl08/Type_of_water_connection']) #water connection type
        else:
            WCT.append('None')
    WCT_count = {i: WCT.count(i) for i in WCT}
    rhs_fields ={'Waste':[SHC,waste_counter],'Water':WCT_count}
    return rhs_fields

def final_section_score(w):
    d0 = road_final(w)[0]
    d1 = water_final(w)[0]
    d2 = waste_final(w)[0]
    final_score_dict ={}
    for i in d1.keys():
            final_score_dict[i]={'Road':d0[i],'Water': d1[i], 'Waste':d2[i]}
    return final_score_dict
    # return HttpResponse(json.dumps(final_score_dict), content_type="application/json")

def single_select(db_data,k1, v1):
    score = None
    ans = db_data[k1]  # pucca
    ans = ans.lower()
    if k1 == 'average_width_of_arterial_road':
        pass
    if ans.lower() in v1['choices']:
        score = v1['choices'][ans.strip()]
    else:
        # pass
        print k1, ans
    return score

