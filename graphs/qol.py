from __future__ import division
from graphs.models import  *
import json
from scipy import stats
from django.http import HttpResponse, HttpResponseForbidden

waste_coll_to_type = {'frequency_of_waste_collection_001':'ulb ghantagadi','frequency_of_waste_collection':'mla sponsored tempo',
              'frequency_of_waste_collection_':'ulb Van','frequency_of_waste_collection__002':'door to door waste collection',
              'frequency_of_waste_collection__001':'garbage bin'}

all_slum_ids = set()

def score_calculation(section_key):
    '''function calculates the score for single and multiselect questions'''
    all_slums_list=[]
    json_data = json.loads(open('graphs/reference_file.json').read())  # json reference data from json file
    slum_data = SlumData.objects.all().values('slum_id','rim_data')
    for i in slum_data:
        slum__id = i['slum_id']
        all_slum_ids.add(slum__id)
        db_data = json.loads( i['rim_data'])
        for k, v in json_data.items():
            if k == section_key:                   # checks sction key like water, toilet etc
                if k in db_data.keys():
                    ques = db_data[k]
                    score_list = []                 #score list for every type of questions (single select , multi select etc)
                    num_dict = {}
                    if type(ques) == dict:
                        ques = [ques]
                    all_ctb_data =[]
                    for i in ques:
                        ques_score = {}
                        freq_waste_coll_type = {}
                        road_list =[]
                        for k1, v1 in v.items():
                            if k1 in i:
                                dummy_list = []
                                if v1['calculate']['type'] == 's':
                                    score = single_select(i, k1, v1)
                                    if k == 'Toilet':
                                        score = single_select(i, k1, v1)
                                        if score != None:
                                            ques_score[k1] = score
                                        else:
                                            ques_score[k1] = 0
                                        dummy_list.append(ques_score)
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
                                                score_for = v1['choices'][db_data[k][k1].lower()]
                                                freq_waste_coll_type[keyy]= score_for
                                        except Exception as e:
                                            print 'single select waste exception is', e
                                        ques_score[k1] = score

                                if v1['calculate']['type'] == 'M':
                                    score = multiselect(i,k1,v1)
                                    if score != None:
                                        ques_score[k1] = score
                                    else:
                                        ques_score[k1] = 0
                                    dummy_list.append(ques_score)
                                    if k == 'Waste':
                                        ques_score[k1] = score
                                        if k1 == 'facility_of_waste_collection':
                                            waste_coll_choices = v1['choices']
                                    if k == 'Road':
                                        if k1 != 'average_width_of_internal_road':
                                            road_list.append(score)
                                        else:
                                            score_list.append(score)
                                    else:
                                        score_list.append(score)
                                if v1['calculate']['type'] == 'N':
                                    data = i[k1]
                                    num_dict[k1] = data
                                if v1['calculate']['type'] == 'C':
                                    pass
                        all_ctb_data.append([dummy_list, num_dict])
                else:
                    print 'k not in sction key', k
        for_each_slum = []
        if section_key == "Toilet":
            all_slums_list.append([all_ctb_data, slum__id])

        if section_key == 'Structure':
            all_slums_list.append(slum__id)

        if section_key == 'General':
            for_each_slum.append([score_list,num_dict, slum__id])
            all_slums_list.append(for_each_slum)

        if section_key == 'Drainage':
            for_each_slum.append([score_list,slum__id])
            all_slums_list.append(for_each_slum)

        if section_key == 'Gutter':
            for_each_slum.append([score_list,slum__id])
            all_slums_list.append(for_each_slum)

        if section_key == 'Waste':
            for_each_slum.append([freq_waste_coll_type, waste_coll_choices , ques_score ,slum__id])
            all_slums_list.append(for_each_slum)

        if section_key == 'Water':
            for_each_slum.append([score_list, num_dict, slum__id])
            all_slums_list.append(for_each_slum)

        if section_key == 'Road':
            for_each_slum.append([score_list, road_list, slum__id])
            all_slums_list.append(for_each_slum)
    return all_slums_list

def waste_final(z):
    '''calculation of final score for waste section,
      Waste Collection Facility Score = SUM ((Number of households using one facility/Total Number of households)
    * Weight of that particular facility * Frequency of Waste Collection of that facility) for all facilities individually
    * Coverage of Waste Collection + Community Dump Sites + Dump in Drains'''
    waste_all_scores=[]
    dumy_di={}
    waste_coverage_list =['coverage_of_waste_collection_a','coverage_of_waste_collection_a_001','frequency_of_waste_collection__001'
                     'coverage_of_waste_collection_a_002','coverage_of_waste_collection_a_003']
    score_data = score_calculation('Waste')
    for i in score_data:
        scr = []
        id = i[0][3]
        scores = i[0][2]
        frequncies_of_waste_coll_facility =  i[0][0]
        available_facility = i[0][1]
        waste_coverage = 1

        waste_info = Rhs_data(id)
        if 'Waste' in waste_info.keys():
            data = waste_info['Waste']
            HC = data[0]
            Count_of_facility = data[1]

        for i in scores.keys():
            if i in waste_coverage_list:
                waste_coverage = scores[i] if i in waste_coverage_list else 1
                scores.pop(i)
            if i == 'facility_of_waste_collection': scores.pop('facility_of_waste_collection')
            if i in waste_coll_to_type.keys(): scores.pop(i)

        for i in Count_of_facility:
            if i in ['ulb ghantagadi', 'ulb van']:
                i = 'ULB service'
            count_of_fac_by_HC = Count_of_facility[i]/HC
            weight_of_facility = available_facility[i] if i in available_facility else 1
            frequency_of_1waste_coll = frequncies_of_waste_coll_facility[i]  if i in frequncies_of_waste_coll_facility else 0
            scr.append(count_of_fac_by_HC*weight_of_facility*frequency_of_1waste_coll*waste_coverage)
        pre_score = sum(scr)
        final_score = pre_score + sum(scores.values())
        dumy_di[id] = final_score
    waste_all_scores.append(dumy_di)
    return waste_all_scores

def gutter_final(z):
    '''calculation of final score for gutter section
    Drainage and Gutter Score = Presence of Drains + Coverage + Drains Blockage+Drains Gradient + Gutters Flooding + Gutter Gradient'''
    gutter_all_scores = []
    dumy_di = {}
    score_data = score_calculation('Gutter')
    for i in score_data:
        id = i[0][1]
        scores = i[0][0]
        final_score = sum(scores)
        dumy_di[id] = final_score
    gutter_all_scores.append(dumy_di)
    return gutter_all_scores

def drainage_final(z):
    '''calculation of final score for drainage section
    Drainage and Gutter Score = Presence of Drains + Coverage + Drains Blockage + Drains Gradient +Gutters Flooding + Gutter Gradient'''
    drainage_all_scores = []
    dumy_di = {}
    score_data = score_calculation('Drainage')
    for i in score_data:
        id = i[0][1]
        scores = i[0][0]
        final_score = sum(scores)
        dumy_di[id] = final_score
    drainage_all_scores.append(dumy_di)
    return drainage_all_scores

def toilet_final(z):
    '''calculation of final score for toilet section'''
    toilet_all_scores =[]
    dummy_dict={}
    cost = []
    id_list =[]
    score_data = score_calculation('Toilet')
    for i in score_data:
        id = i[1]
        id_list.append(id)
        other_data = i[0]
        men_seats = ['number_of_seats_allotted_to_me','number_of_seats_allotted_to_me_001']
        wm_seats = ['number_of_seats_allotted_to_wo','number_of_seats_allotted_to_wo_001']
        mix_seats =['total_number_of_mixed_seats_al','number_of_mixed_seats_allotted']
        toilet_scores = []
        for j in other_data:
            numeric_data = j[1]
            if len(j[0]) >= 1 :
                one_ctb_data = j[0][0]
                ctb_in_use = one_ctb_data['is_the_CTB_in_use']
                one_ctb_data.pop('is_the_CTB_in_use')
            else:
                ctb_in_use =0
            for i in numeric_data.keys():
                mix_fun =0
                men_fun=0
                wm_fun=0
                if i in men_seats:
                    men_fun = int(numeric_data[men_seats[0]]) -int(numeric_data[men_seats[1]])
                if i in wm_seats:
                    wm_fun = int(numeric_data[wm_seats[0]]) - int(numeric_data[wm_seats[1]])
                if i in mix_seats:
                    mix_fun = int(numeric_data[mix_seats[0]]) - int(numeric_data[mix_seats[1]])
                if i in ['fee_for_use_of_ctb_per_family', 'cost_of_pay_and_use_toilet_pe']:
                    cost.append(int(numeric_data[i]))
                    total_cost = 0 if len(cost) <= 0 else sum(cost) / len(cost)
                    total_wrk_seats =  men_fun + wm_fun + mix_fun
                    final_score_of_1_toilet = ctb_in_use * sum(one_ctb_data.values()) + total_cost + total_wrk_seats
                    toilet_scores.append(final_score_of_1_toilet)
                    final_score = sum(toilet_scores)/len(toilet_scores)
                    dummy_dict[id]= final_score
    toilet_all_scores.append(dummy_dict)
    return toilet_all_scores

def Rhs_data(slumid):
    '''collection of rhs data required for every section'''
    waste_data = []
    WCT=[]
    unoccupide_house ={}
    hh_no =[]                           # household_number
    owner_state=[]
    gen_data =[]
    rhs_data = HouseholdData.objects.filter(slum__id=slumid)
    db_data = (map(lambda x: x.rhs_data, rhs_data))
    SHC = len(rhs_data)                  # Slums_Household_count  = SHC
    for i in db_data:
        if  i['Type_of_structure_occupancy']  == 'Occupied house':
            if 'group_el9cl08/Facility_of_solid_waste_collection' in i:
                waste_data.append(i['group_el9cl08/Facility_of_solid_waste_collection'].lower())
            else:
                waste_data.append('None')
            if 'group_el9cl08/Type_of_water_connection' in i:
                WCT.append(i['group_el9cl08/Type_of_water_connection'])
            else:
                WCT.append('None')
            if 'group_el9cl08/Ownership_status_of_the_house'in i:
                owner_state.append(i['group_el9cl08/Ownership_status_of_the_house'])
            else:
                owner_state.append('Own house')

            if 'group_el9cl08/House_area_in_sq_ft' in i:
                data = i['group_el9cl08/House_area_in_sq_ft']
                if data in (0, 99):
                    data = 1
                elif data in (100,200):
                    data = 2
                elif data in (200,300 ):
                    data = 3
                elif data in (300,399):
                    data = 4
                else:
                    data = 5
                gen_data.append(data)
        else:
            hh_no.append( i['Household_number'])
        unoccupide_house[slumid] = hh_no
    avg_house_area = 0 if (len(gen_data)<=0) else (sum(gen_data)/len(gen_data))
    owner_count = {i:owner_state.count(i) for i in owner_state}
    WCT_count = {i: WCT.count(i) for i in WCT}
    waste_counter = {i: waste_data.count(i) for i in waste_data}
    rhs_fields ={'Waste':[SHC,waste_counter],'Water':[SHC,WCT_count],'General':avg_house_area, 'Structure':owner_count}
    return rhs_fields

def general_final(z):
    '''calculation of final score for general section
    General Information Score = Legal Status + Average (Land Owner) + Average (Topography) + Tenement Density
            + Mode of House Area + Status of Defecation Score'''
    general_all_scores = []
    dumy_di = {}
    place_of_defecation =[]
    score_data = score_calculation('General')
    for i in score_data:
        id = i[0][2]
        scores = i[0][0]
        other_data = i[0][1]
        followup_data = FollowupData.objects.filter(slum__id=id)
        data_followup = map(lambda x: x.followup_data, followup_data)
        for i in data_followup:
            if 'group_oi8ts04/Current_place_of_defecation' in i:
                place_of_defecation.append(int(i['group_oi8ts04/Current_place_of_defecation']))
            else:
                place_of_defecation.append(0)
        if len(place_of_defecation)<=0:
            status_of_defecation =0
        else:
            status_of_defecation = sum(place_of_defecation)/len(place_of_defecation)
        rhs = Rhs_data(id)
        if 'General' in rhs.keys():
            house_area = rhs['General']
        for i in other_data:
            if i == 'number_of_huts_in_settlement':
                slum_population = 4 * int(other_data[i])        #calculating population of slum
            if i == 'approximate_area_of_the_settle':           # area of slun in hectors(originally obtained is in square meters)
                area_in_hector = int(other_data[i])/10000 if int(other_data[i])/10000 != 0 else 1
                t_d = slum_population / area_in_hector  #Tenement Density
                if t_d in (0,200):
                    t_d =1
                elif t_d in (200,300):
                    t_d =2
                elif t_d in (301, 400):
                    t_d =3
                elif t_d in (401,500):
                    t_d =4
                else:
                    t_d =5
                final_score = sum(scores) + t_d + house_area + status_of_defecation
                dumy_di[id] = final_score
    general_all_scores.append(dumy_di)
    return general_all_scores

def final_section_score(w):
    '''final score calculation of data for each slum '''
    one_slum_score_dict = {}
    d0 = road_final(w)[0]
    d1 = water_final(w)[0]
    d2 = waste_final(w)[0]
    d3 = drainage_final(w)[0]
    d4 = gutter_final(w)[0]
    d5 = general_final(w)[0]
    d6 = structure_occupancy(w)
    d7 = toilet_final(w)[0]

    uncommom_keys = all_slum_ids - set(d0.keys() and d1.keys() and d2.keys() and d3.keys() and d4.keys() and d5.keys() and d6.keys()and d7.keys())
    common_keys = all_slum_ids - uncommom_keys
    for i in common_keys:
        slum_total_score = d0[i] + d1[i] + d2[i] + d3[i] + d4[i] + d5[i] + d6[i]+ d7[i]
        one_slum_score_dict[i]={'Road':d0[i],'Water': d1[i],'Waste':d2[i],'Drainage':d3[i],'Gutter':d4[i],'General':d5[i],'Str_n_occup':d6[i],'Total_score':slum_total_score,'Toilet':d7[i]}

    for i in uncommom_keys:
        if d1.has_key(i):
            pass
        else:
            d1[i] = None
        if d2.has_key(i):
            pass
        else:
            d2[i] = None
        if d3.has_key(i):
            pass
        else:
            d3[i] = None
        if d4.has_key(i):
            pass
        else:
            d4[i] = None
        if d5.has_key(i):
            pass
        else:
            d5[i] = None
        if d6.has_key(i):
            pass
        else:
            d6[i] = None
        if d7.has_key(i):
            pass
        else:
            d7[i] = None
        if d1[i] and d2[i] and d3[i] and d4[i] and d5[i] and d6[i] and d7[i]:
            slum_total_score = d0[i] + d1[i] + d2[i] + d3[i] + d4[i] + d5[i] + d6[i] + d7[i]
        else:
            slum_total_score = None
        one_slum_score_dict[i] = {'Road': d0[i], 'Water': d1[i], 'Waste': d2[i], 'Drainage': d3[i], 'Gutter': d4[i],
                                  'General': d5[i], 'Str_n_occup': d6[i], 'Total_score':slum_total_score,'Toilet':d7[i]}
    return one_slum_score_dict

def percentile_function():
    # calculate and save percentile for only modified slum not for all
    percentile_one_slum = {}
    road_dict = {}
    water_dict = {}
    waste_dict = {}
    drainage_dict = {}
    gutter_dict = {}
    general_dict = {}
    toilet_dict = {}
    stru_n_ocup_dict = {}
    total_score_dict = {}
    slum_percentile_sectionwise = {}
    slum_id_list = []

    def set_none_to_neg(score_dict):
        for i in score_dict.keys():
            if score_dict[i] == None:
                score_dict[i] = -100
        return score_dict

    from_db = QOLScoreData.objects.all().values()  # for percentile calculations nedd all data
    for i in from_db:
        slum_id_list.append({'slumid': i['slum_id'],'id': i['id']})
        road_dict[i['slum_id']] = i['road']
        water_dict[i['slum_id']] = i['water']
        waste_dict[i['slum_id']] = i['waste']
        drainage_dict[i['slum_id']] = i['drainage']
        gutter_dict[i['slum_id']] = i['gutter']
        general_dict[i['slum_id']] = i['general']
        stru_n_ocup_dict[i['slum_id']] = i['str_n_occup']
        toilet_dict[i['slum_id']] = i['toilet']
        total_score_dict[i['slum_id']] = i['total_score']

    total_score_dict = set_none_to_neg(total_score_dict)
    toilet_dict = set_none_to_neg(toilet_dict)
    road_dict = set_none_to_neg(road_dict)
    water_dict = set_none_to_neg(water_dict)
    waste_dict = set_none_to_neg(waste_dict)
    drainage_dict = set_none_to_neg(drainage_dict)
    gutter_dict = set_none_to_neg(gutter_dict)
    general_dict = set_none_to_neg(general_dict)
    stru_n_ocup_dict= set_none_to_neg(stru_n_ocup_dict)

    try:
        total_score_pert = {i: stats.percentileofscore(total_score_dict.values(),total_score_dict[i])for i in total_score_dict.keys()}
        toilet_pert = {i: stats.percentileofscore(toilet_dict.values(),toilet_dict[i])for i in toilet_dict.keys()}
        road_pert = {i: stats.percentileofscore(road_dict.values(), road_dict[i]) for i in road_dict.keys()}
        water_pert = {i: stats.percentileofscore(water_dict.values(), water_dict[i]) for i in water_dict.keys()}
        waste_pert = {i: stats.percentileofscore(waste_dict.values(), waste_dict[i]) for i in waste_dict.keys()}
        drainage_pert = {i: stats.percentileofscore(drainage_dict.values(), drainage_dict[i]) for i in drainage_dict.keys()}
        gutter_pert = {i: stats.percentileofscore(gutter_dict.values(), gutter_dict[i]) for i in gutter_dict.keys()}
        general_pert = {i: stats.percentileofscore(general_dict.values(), general_dict[i]) for i in general_dict.keys()}
        stru_n_ocup_pert = {i: stats.percentileofscore(stru_n_ocup_dict.values(), stru_n_ocup_dict[i])
                            for i in stru_n_ocup_dict.keys()}

        for i in slum_id_list:
            if i['slumid'] in road_pert.keys() and waste_pert.keys() and water_pert.keys() and gutter_pert.keys() \
                    and general_pert.keys() and stru_n_ocup_pert.keys() and toilet_pert.keys() and total_score_pert.keys() \
                    and drainage_pert.keys():
                slum_percentile_sectionwise[i['slumid']] = {'Waste': waste_pert[i['slumid']],'Road': road_pert[i['slumid']],
                        'Water': water_pert[i['slumid']],'Gutter': gutter_pert[i['slumid']],'General': general_pert[i['slumid']],
                        'Str_n_occup': stru_n_ocup_pert[i['slumid']],'Drainage': drainage_pert[i['slumid']],
                        'Total_score': total_score_pert[i['slumid']],'Toilet': toilet_pert[i['slumid']]}

            for k, v in slum_percentile_sectionwise.items():
                    if i['slumid'] == k:
                        trial = QOLScoreData.objects.filter(id = i['id'],slum_id = k).update(totalscore_percentile= v['Total_score'],
                            toilet_percentile =v['Toilet'],str_n_ocup_percentile= v['Str_n_occup'],road_percentile = v['Road'],
                            drainage_percentile=v['Drainage'],general_percentile = v['General'],gutter_percentile=v['Gutter'],
                            waste_percentile=v['Waste'],water_percentile=v['Water'])
                    else:
                        pass
    except Exception as e:
        print 'Exception in percentile function', e

def QOL_save_data(request):
    '''saving data to db'''
    result = final_section_score(request)
    for i in result.items():
        data = i[1]
        try:
            to_save = QOLScoreData.objects.get_or_create(slum_id = i[0],water =data['Water'], waste =data['Waste'],
                            road =data['Road'],str_n_occup = data['Str_n_occup'],drainage =data['Drainage'],
                            gutter =data['Gutter'],toilet =data['Toilet'],general =data['General'],
                            total_score = data['Total_score'])
        except Exception as e:
            print e
    percentile_function()
    return HttpResponse(json.dumps(result), content_type="application/json")

def single_select(db_data,k1, v1):
    '''scores for single select questions from reference json file'''
    score = None
    ans = db_data[k1]
    ans = ans.lower()
    if k1 == 'average_width_of_arterial_road':
        pass
    if ans.lower() in v1['choices']:
        score = v1['choices'][ans.strip()]
    else:
        print 'single select v1[choices]',k1, ans
    return score

def multiselect(db_data,k1,v1):
    '''scores for multi-select questions from reference json file'''
    avg=[]
    ans = db_data[k1]
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
        print 'exception in multi select ', ans, k1
        score = {k1: 0}
    return score

def structure_occupancy(z):
    '''calculation of final score for structure and occupancy section
    Structure and Occupancy Score = Ownership Status '''
    sno_all_scores = []
    dumy_di = {}
    score_data = score_calculation('Structure')
    for i in score_data:
        id = i
        data = Rhs_data(id)
        if 'Structure' in data.keys():
            owner_status = data['Structure']
            try:
                if len(owner_status) == 0:
                    score = -1
                elif len(owner_status) == 1:
                    if owner_status['Own house'] != None :
                        score = 1
                else:
                    score = 1 if (owner_status['Own house'] >= owner_status['Tenant']) else -1
                dumy_di[id] = score
            except Exception as e:
                print 'exception in structure n occup',e, owner_status
    return  dumy_di

def road_final(z):
    '''calculation of final score for road section
    Road Information = Presence of roads * (Type of Road *  Finish of Road + Coverage of Road +  Average Width of Internal Roads
+ Average width of arterial roads + Point of vehicular access + Settlement above/below arterial road + Huts below/above internal roads)'''
    road_all_scores = []
    dumy_di = {}
    prsn_of_rd = 0
    road_type =0
    score_data =score_calculation('Road')
    for i in score_data:
        scores = i[0][0]
        data = i[0][1]
        id = i[0][2]
        for j in data:
            if 'presence' in j.keys():
                prsn_of_rd = j['presence']
            if 'road_type' in j.keys():
                road_type = j['road_type']
            if 'finish_of_the_road' in j.keys():
                finish_of_road = j['finish_of_the_road']
                road_type_n_finish = road_type * finish_of_road
                all_scores = sum(scores)
                road_n_all_scores = road_type_n_finish + all_scores
        final_score = prsn_of_rd * road_n_all_scores
        dumy_di[id]=final_score
    road_all_scores.append(dumy_di)
    return road_all_scores

def water_final(z):
    '''calculation of final score for water section
    Water Score = SUM ((Number of households using one facility/Total Number of households)
    * Weight of that particular facility) for all facilities individually
    + Availability of Water + Pressure of Water + Coverage of Water + Quality of Water'''
    water_all_scores = []
    dumy_di = {}
    weight_of_facility ={'Individual connection':5,'Shared connection':4,'Hand Pump':2,'Well':2,'Water Tanker':2,
                       'Water standpost':2,'From other settlements':-2,'No Service':-5,'None':0}
    score_data = score_calculation('Water')
    for i in score_data:
        lst = []
        scores = sum(i[0][0])
        id = i[0][2]
        water_info = Rhs_data(id)
        if 'Water' in water_info.keys():
            data = water_info['Water']              # count of working water facilities
            total_household = data[0]
            water_conn_facility_count = data[1]
            for i in water_conn_facility_count:
                if i in weight_of_facility.keys():
                    wwf_count = (water_conn_facility_count[i] /total_household)* weight_of_facility[i] #wwf=working water facility count
                    lst.append(wwf_count)
        final_score = scores + sum(lst)
        dumy_di[id]= final_score
    water_all_scores.append(dumy_di)
    return water_all_scores