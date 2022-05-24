from __future__ import division
from re import S
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse 
from itertools import groupby
from django.db.models import Avg,Sum,Count
from collections import OrderedDict
from graphs.models import *
from master.models import *
import json

from django.db.models import Q

import csv


from sponsor.models import *

from django.views.decorators.csrf import csrf_exempt
from utils.utils_permission import apply_permissions_ajax
from django.db.models import Count, F
from django.contrib.auth.models import Group
from collections import defaultdict
from mastersheet.models import *




CARDS = {'Cards': {'General':[{'slum_count':'Slum count'},{'gen_avg_household_size':"Avg Household size"}, {'gen_tenement_density':"Tenement density (Huts/Hector)"},
                    {'household_owners_count':'Superstructure Ownership'}],
         'Waste': [{'waste_no_collection_facility_percentile':'Garbage Bin'},
                   {'waste_door_to_door_collection_facility_percentile':'Door to door waste collection'},
                   {'waste_dump_in_open_percent':'Dump in open'},{'drains_coverage':'ULB Service'},{'waste_other_services':'Other services'}],
         'Water': [{'water_individual_connection_percentile':'Individual water connection'},{'water_shared_service_percentile':'Shared Water Connection'},
                   {'waterstandpost_percentile':'Water Standposts'},{'water_other_services':'Other sources'}],
         'Toilet': [{'toilet_seat_to_person_ratio':'Toilet seat to person ratio'},
                    {'toilet_men_women_seats_ratio':'Men|Women|Mix toilet seats'},
                    {'individual_toilet_coverage':'Individual Toilet Coverage'},{'ctb_coverage':'CTB usage'}],
         'Road': [{'road_with_no_vehicle_access':'No. of slums with no vehicle access'},
                  {'pucca_road_coverage':'Pucca Road Coverage'},{'kutcha_road_coverage':'Kutcha Road Coverage'}],
         'Drainage':[{'drainage_coverage':'Drain coverage'}]},
         'Keytakeaways' :
         {'General':[ [" <b>value</b> slum/s with <b>undeclared</b> land status",],
                      [" <b>value</b> slum/s with <b>private</b> land ownership",],
                      [" <b>value</b> slum/s likely to be affected by flooding, drainage and gutter problems due to <b>reasonable slope</b> of land topography"]],
         'Water': [['<b>value</b> slum/s where water availability  is <b>less than 2 hours</b>, '],
                  [' <b>value</b> slum/s with <b>24/7 water availability </b>'],
                  [' <b>value</b> slum/s with <b>poor</b> quality of water'],
                  [' <b>value</b> slum/s with <b>good</b> quality of water'],
                  [' <b>value</b> slum/s with <b>full water coverage</b>'],
                  [' <b>value</b> slum/s with <b>partial water coverage</b>'],
                  [' <b>value</b> slum/s where alternate water sources are <b>tanker</b>'],
                  [' <b>value</b> slum/s with <b>water standposts</b>']],
         'Waste': [[' <b>value open community dumping sites</b> present in slum/s'],
                   [' <b>value</b> slum/s practice <b> dumping in drains</b>'],
                   [' Total <b>value waste containers</b> available in slum/s'],
                   [' <b>value</b> slum/s with <b>full waste collection coverage</b> facility'],
                   [' <b>value</b> slum/s with <b>partial waste collection coverage</b> facility' ],
                   [' <b>value</b> slum/s with <b> no waste collection coverage</b> facility'],
                   [' <b>value </b> slum/s have <b>daily </b>waste collection frequency'],
                   [' <b>value</b> slum/s have <b>twice a week </b> waste collection frequency']],
         'Road': [[' <b>value</b> slum/s having <b>more than one</b> vehicular access'],
                  [' <b>value</b> slum/s where settlement is <b> below</b> access road'],
                  [' <b>value</b> slum/s where huts are <b>above</b> internal roads']],
         'Drainage':[[' <b>value</b> slum/s where drains <b> get blocked </b>'],
                    [' <b>value</b> slum/s with <b>adequete</b> drain gradient, '],
                    # [' <b>value</b> slum/s with<b> inadequete </b>drain gradient'],
                    [' <b>value</b>  slum/s where gutter gets <b>flooded</b>'],
                    [' <b>value</b> slum/s with<b> adequete</b> gutter gradient, ']],
                    # [' <b>value</b> slum/s with <b> inadequete</b> gutter gradient']],
         'Toilet':[[' <b>value</b>  slum/s where CTB structure is in <b> poor </b> condition'],
                   [' <b>value</b>  CTB seats out of total <b>are in good condition </b>'],
                   [' <b>value</b>  slum/s where <b> no availability of water</b> in CTB'],
                   [' <b>value</b>  slum/s where sewage is <b> laid in open</b>'],
                   [' <b>value</b>  slum/s where <b>no electricity in CTB at night</b>'],
                   [' <b>value</b>  slum/s where CTB is <b>not available at night</b>'],
                   [' <b>value</b> slum/s where cleanliness is <b> good</b> , '],
                   [' <b>value</b> slum/s where cleanliness is <b> poor </b>in condition']]
         }}

@login_required(login_url='/accounts/login/')
def graphs_display(request, graph_type):
    custom_url = settings.GRAPHS_BUILD_URL % settings.GRAPH_DETAILS[graph_type][1::-1]
    return render(request, 'graphs.html', {'custom_url':custom_url})

def get_dashboard_card(request, key):
    output_data = {'city':{}, 'administrative_ward':{}, 'electoral_ward':{}, 'slum':{}}
    select_clause = ['totalscore_percentile', 'general_percentile', 'drainage_percentile',
                     'road_percentile', 'toilet_percentile', 'water_percentile', 'waste_percentile']

    city = get_object_or_404(City, pk=key)

    #City level
    output_data['city'][city.name.city_name] = {'scores':{}, 'cards':{}}#,'key_takeaways':{} }
    list_associated_with_SA_city = Slum.objects.filter(associated_with_SA=True, electoral_ward__administrative_ward__city__name__city_name=city)
    qol_scores = QOLScoreData.objects.filter(city=city)
    for clause in select_clause:
        output_data['city'][city.name.city_name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
    cities = DashboardData.objects.filter(slum__in=list_associated_with_SA_city)
    city_keyTakeaways = SlumDataSplit.objects.filter(city=city)
    city_keyTakeaways_ctb = SlumCTBdataSplit.objects.filter(city=city)
    cards = score_cards(cities)
    key_takeaway = key_takeaways(city_keyTakeaways)
    key_takeaway.update(key_takeaways_toilet(city_keyTakeaways_ctb))
    output_data['city'][city.name.city_name]['cards'] = cards
    output_data['city'][city.name.city_name]['key_takeaways'] = key_takeaway

    # Administrative ward calculations
    for admin_ward in AdministrativeWard.objects.filter(city=city):
        output_data['administrative_ward'][admin_ward.name] = {'scores': {}, 'cards':{}}#, 'key_takeaways':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        list_associated_with_SA_admins = Slum.objects.filter(associated_with_SA=True,electoral_ward__administrative_ward = admin_ward)
        for clause in select_clause:
            output_data['administrative_ward'][admin_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        # admin_wards = DashboardData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        admin_wards = DashboardData.objects.filter(slum__in = list_associated_with_SA_admins)
        admin_keyTakeaways = SlumDataSplit.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        admin_keyTakeaways_ctb = SlumCTBdataSplit.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        cards = score_cards(admin_wards)
        key_takeaway = key_takeaways(admin_keyTakeaways)
        key_takeaway.update(key_takeaways_toilet(admin_keyTakeaways_ctb))
        output_data['administrative_ward'][admin_ward.name]['cards'] = cards
        output_data['administrative_ward'][admin_ward.name]['key_takeaways'] = key_takeaway

    #Electoral ward calculations
    for electoral_ward in ElectoralWard.objects.filter(administrative_ward__city=city):
        output_data['electoral_ward'][electoral_ward.name] = {'scores': {}, 'cards':{} }#, 'key_takeaways':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward=electoral_ward)
        list_associated_with_SA_electorals = Slum.objects.filter(associated_with_SA=True,electoral_ward = electoral_ward)
        for clause in select_clause:
            output_data['electoral_ward'][electoral_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        ele_wards = DashboardData.objects.filter(slum__in =list_associated_with_SA_electorals)
        ele_keyTakeaways_other = SlumDataSplit.objects.filter(slum__electoral_ward=electoral_ward)
        ele_keyTakeaways_ctb = SlumCTBdataSplit.objects.filter(slum__electoral_ward=electoral_ward)
        if ele_wards.count() > 0:
            cards = score_cards(ele_wards)
            key_takeaway = key_takeaways(ele_keyTakeaways_other)
            key_takeaway.update(key_takeaways_toilet(ele_keyTakeaways_ctb))
            output_data['electoral_ward'][electoral_ward.name]['cards'] = cards
            output_data['electoral_ward'][electoral_ward.name]['key_takeaways'] = key_takeaway

    #Slum level calculations
    output_data['slum'] = {'scores':{},'cards':{}}#,'key_takeaways':{} }
    select_clause.append('slum__name')
    qol_scores = QOLScoreData.objects.filter(slum__in = list_associated_with_SA_city).values(*select_clause)
    qol_scores = groupby(qol_scores, key=lambda x: x['slum__name'])
    qol_scores = {key: {'scores': list(values)[0], 'cards': score_cards(DashboardData.objects.filter(slum__name=key)),
                        'key_takeaways': all_key_takeaways(key)} for key, values in qol_scores}
    output_data['slum'] = qol_scores
    output_data['metadata'] = CARDS

    return HttpResponse(json.dumps(output_data),content_type='application/json')

def all_key_takeaways(slum):
    ''' collecting key take aways for all sections '''
    ctb_data = key_takeaways_toilet(SlumCTBdataSplit.objects.filter(slum__name=slum))
    other_sections = key_takeaways(SlumDataSplit.objects.filter(slum__name=slum))
    ctb_data.update(other_sections)
    return ctb_data

def score_cards(ele):
    """To calculate aggregate level data for electoral, admin and city"""
    all_cards ={ }
    slum_count = ele.values_list('slum_id', flat=True)
    aggrgated_data = ele.aggregate(Sum('occupied_household_count'),Sum('household_count'),
        Sum('total_road_area'),Sum('road_with_no_vehicle_access'),Sum('pucca_road_coverage'),Sum('kutcha_road_coverage'),
        Sum('gen_avg_household_size'),Sum('gen_tenement_density'),Sum('household_owners_count'),
        Sum('waste_no_collection_facility_percentile'),Sum('waste_door_to_door_collection_facility_percentile'),
        Sum('waste_dump_in_open_percent'),Sum('water_other_services'),Sum('waste_other_services'),
        Sum('water_individual_connection_percentile'),Sum('water_shared_service_percentile'),Sum('waterstandpost_percentile'),
        Sum('toilet_seat_to_person_ratio'),Sum('individual_toilet_coverage'),Sum('fun_male_seats'),Sum('fun_fmale_seats'),
        Sum('toilet_men_women_seats_ratio'),Sum('ctb_coverage'),Sum('get_shops_count'), Sum('drains_coverage'))

    #drainage_card data
    slum_ids_hh = ele.filter( household_count__gt = 0.0).values_list('slum_id',flat=True)
    total_drain_count = 0
    data = Rapid_Slum_Appraisal.objects.filter(slum_name__id__in = slum_ids_hh).aggregate(Sum('drainage_coverage'))
    total_drain_count += data['drainage_coverage__sum'] if data['drainage_coverage__sum'] !=None else 0

    for k1,v1 in CARDS.items():
        cards = {}
        if k1 == 'Cards':
            for k,v in v1.items():
                cards[k] = []
                if k == 'Drainage':
                    drain_coverage = str(round((total_drain_count / aggrgated_data['household_count__sum'])*100 if aggrgated_data['household_count__sum'] else 0, 2)) + ' %'
                    cards[k]= [drain_coverage]
                    all_cards.update(cards)
                elif k =='Road':
                    cards[k].append(str(int(aggrgated_data['road_with_no_vehicle_access__sum'] if aggrgated_data['road_with_no_vehicle_access__sum'] else 0 )))
                    cards[k].append(str(round((aggrgated_data['pucca_road_coverage__sum']/aggrgated_data['total_road_area__sum'])*100 if aggrgated_data['total_road_area__sum'] else 0,2))+' %')
                    cards[k].append(str(round((aggrgated_data['kutcha_road_coverage__sum']/aggrgated_data['total_road_area__sum'])*100 if aggrgated_data['total_road_area__sum'] else 0,2))+' %')
                    all_cards.update(cards)
                elif k == 'Toilet':
                    all_users = aggrgated_data['occupied_household_count__sum'] if aggrgated_data['occupied_household_count__sum'] else 0
                    own_toilet = aggrgated_data['individual_toilet_coverage__sum'] if aggrgated_data['individual_toilet_coverage__sum'] else 0
                    only_ctb_user = all_users - own_toilet
                    ctb_seat_ratio = ("1:" + str(int((only_ctb_user * 5) / aggrgated_data['toilet_seat_to_person_ratio__sum'] if aggrgated_data['toilet_seat_to_person_ratio__sum'] else 0)))
                    if ctb_seat_ratio == '1:0':
                        cards[k].append('NO CTB')
                    else : cards[k].append(ctb_seat_ratio)
                    mix = str(int(aggrgated_data['toilet_men_women_seats_ratio__sum'])) if aggrgated_data['toilet_men_women_seats_ratio__sum'] else '0'
                    men_wmn_seats_ratio = str(aggrgated_data['fun_male_seats__sum'])+'|'+str(aggrgated_data['fun_fmale_seats__sum'])+ '|'+ mix
                    if men_wmn_seats_ratio == '0|0|0':
                        cards[k].append('NO CTB')
                    else : cards[k].append(men_wmn_seats_ratio)
                    cards[k].append(str(round((aggrgated_data['individual_toilet_coverage__sum']/aggrgated_data['occupied_household_count__sum'])*100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    cards[k].append(str(round((aggrgated_data['ctb_coverage__sum']/aggrgated_data['occupied_household_count__sum'])*100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    all_cards.update(cards)
                elif k == 'General':
                    cards[k].append(str(len(slum_count)))
                    houses = aggrgated_data['household_count__sum'] if aggrgated_data['household_count__sum']  else 0
                    shops = aggrgated_data['get_shops_count__sum'] if aggrgated_data['get_shops_count__sum'] else 0 #this column contains shops count for slum
                    cards[k].append(str(round(aggrgated_data['gen_avg_household_size__sum']/aggrgated_data['occupied_household_count__sum']\
                                              if aggrgated_data['occupied_household_count__sum'] else 0,2)))
                    cards[k].append(str(int( (houses+shops) / aggrgated_data['gen_tenement_density__sum'] if aggrgated_data['gen_tenement_density__sum'] else 0)))
                    cards[k].append(str(round((aggrgated_data['household_owners_count__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    all_cards.update(cards)
                elif k =='Water':
                    cards[k].append(str(round((aggrgated_data['water_individual_connection_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    cards[k].append(str(round((aggrgated_data['water_shared_service_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    cards[k].append(str(round((aggrgated_data['waterstandpost_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    water_data = aggrgated_data['water_other_services__sum'] if aggrgated_data['water_other_services__sum'] else 0
                    cards[k].append(str(round((water_data/ aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    all_cards.update(cards)
                else:
                    cards[k].append(str(round((aggrgated_data['waste_no_collection_facility_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0, 2)) + " %")
                    cards[k].append(str(round((aggrgated_data['waste_door_to_door_collection_facility_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0, 2)) + " %")
                    cards[k].append(str(round((aggrgated_data['waste_dump_in_open_percent__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0, 2)) + " %")
                    ulb = aggrgated_data['drains_coverage__sum'] if aggrgated_data['drains_coverage__sum'] else 0
                    cards[k].append(str(round((ulb / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0, 2)) + " %")
                    waste_data = aggrgated_data['waste_other_services__sum'] if aggrgated_data['waste_other_services__sum'] else 0
                    cards[k].append(str(round((waste_data / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0, 2)) + " %")
                    all_cards.update(cards)
        else :
            pass
    return all_cards

def key_takeaways_toilet(slum):
    '''calculating count of toilet sections' key take aways'''
    all_cards={}
    safe_m1 = 0
    safe_m2 = 0
    water =0
    electricity =0
    sewage =0
    ctb_at_night =0
    ctb_cleaning_good =0
    ctb_cleaning_poor =0
    for i in slum:
        safe_m1 += 1 if i.ctb_structure_condition == 'Poor' else 0
        safe_m2 += int(i.seats_in_good_condtn) if type(i.seats_in_good_condtn) == int else 0
        water += 1 if i.water_availability == ' Not available' else 0
        electricity += 1 if i.electricity_in_ctb == 'No' else 0
        sewage += 1 if i.sewage_disposal_system == 'Laid in the open' else 0
        ctb_at_night += 1 if i.ctb_available_at_night in ['No','Yes, but Not all night'] else 0
        ctb_cleaning_poor += 1 if i.cleanliness_of_the_ctb == 'Poor' else 0
        ctb_cleaning_good += 1 if i.cleanliness_of_the_ctb == 'Good' else 0
    all_cards['Toilet']=[safe_m1,safe_m2,water,sewage,electricity,ctb_at_night,ctb_cleaning_good,ctb_cleaning_poor]
    return all_cards

def key_takeaways(slum_name):
    '''count of key take aways, section wise'''
    all_cards = {}

   #general data
    gen_land_status =slum_name.filter(land_status='Undeclared').count()
    gen_land_owner =slum_name.filter(land_ownership='Private').count()
    gen_land_topography =slum_name.filter(land_topography='Depression Slope').count()

    #water data
    water_availability ={}
    water_quality ={}
    water_coverage ={}
    water_source ={}

    availability = slum_name.values('availability_of_water').annotate(count=Count('availability_of_water'))
    for i in availability:
        water_availability[i['availability_of_water']]= i['count']
    water_availability_2hrs = water_availability['Less than 2 hrs']  if 'Less than 2 hrs' in water_availability.keys() else 0
    water_availability_24_7 = water_availability['24/7']  if 'Daily' in water_availability.keys() else 0

    quality = slum_name.values('quality_of_water').annotate(count=Count('quality_of_water'))
    for i in quality:
        water_quality[i['quality_of_water']]= i['count']
    quality_poor = water_quality['Poor']  if 'Poor' in water_quality.keys() else 0
    qualiyt_good = water_quality['Good']  if 'Good' in water_quality.keys() else 0

    coverage = slum_name.values('coverage_of_water').annotate(count=Count('coverage_of_water'))
    for i in coverage:
        water_coverage[i['coverage_of_water']]= i['count']
    coverage_full = water_coverage["Full coverage"]  if 'Full coverage' in water_coverage.keys() else 0
    prtial_coverage = water_coverage['Partial coverage']  if 'Partial coverage' in water_coverage.keys() else 0

    source = slum_name.values('alternative_source_of_water').annotate(count=Count('alternative_source_of_water'))
    for i in source:
        water_source[i['alternative_source_of_water']]= i['count']
    tanker = water_source['Tanker']  if 'Tanker' in water_source.keys() else 0
    standpost = water_source['Water standpost']  if 'Water standpost' in water_source.keys() else 0

    #waste data
    waste_coverage_door ={}
    waste_coverage_tempo = {}
    waste_coverage_van = {}
    waste_coverage_ghantagadi = {}
    waste_freq_door = {}
    waste_freq_tempo = {}
    waste_freq_van = {}
    waste_freq_ghantagadi = {}

    count_waste_container = 0
    dump_sites = slum_name.filter(~Q(community_dump_sites = 'None')).count()
    dump_in_drain = slum_name.filter(dump_in_drains ='Yes').count()
    try:
      container = int(slum_name.values_list('number_of_waste_container',flat=True)[0])
    except :
      container = 0
    count_waste_container += container

    cvrg_door_t_door = slum_name.values('waste_coverage_door_to_door').annotate(count=Count('waste_coverage_door_to_door'))
    for i in cvrg_door_t_door:
        waste_coverage_door[i['waste_coverage_door_to_door']] = i['count']
    full_coverage = waste_coverage_door['Full coverage'] if 'Full coverage' in waste_coverage_door.keys() else 0
    partial_coverage = waste_coverage_door['Partial coverage'] if 'Partial coverage' in waste_coverage_door.keys() else 0
    no_coverage = waste_coverage_door['0'] if '0' in waste_coverage_door.keys() else 0

    # cvrg_mla_tempo = slum_name.values('waste_coverage_by_mla_tempo').annotate(count=Count('waste_coverage_by_mla_tempo'))
    # for i in cvrg_mla_tempo:
    #     waste_coverage_tempo[i['waste_coverage_by_mla_tempo']] = i['count']
    # mla_full = waste_coverage_tempo['Full coverage'] if 'Full coverage' in waste_coverage_tempo.keys() else 0
    # mla_part = waste_coverage_tempo['Partial coverage'] if 'Partial coverage' in waste_coverage_tempo.keys() else 0
    # mla_no = waste_coverage_tempo['0'] if '0' in waste_coverage_tempo.keys() else 0

    # cvrg_van = slum_name.values('waste_coverage_by_ulb_van').annotate(count=Count('waste_coverage_by_ulb_van'))
    # for i in cvrg_van:
    #     waste_coverage_van[i['waste_coverage_by_ulb_van']]= i['count']
    # van_full = waste_coverage_van['Full coverage'] if 'Full coverage' in waste_coverage_van.keys() else 0
    # van_part = waste_coverage_van['Partial coverage'] if 'Partial coverage' in waste_coverage_van.keys() else 0
    # van_no = waste_coverage_van['0'] if '0' in waste_coverage_van.keys() else 0
    #
    # cvrg_ghantagadi = slum_name.values('waste_coverage_by_ghantagadi').annotate(count=Count('waste_coverage_by_ghantagadi'))
    # for i in cvrg_ghantagadi:
    #     waste_coverage_ghantagadi[i['waste_coverage_by_ghantagadi']] = i['count']
    # gadi_full = waste_coverage_ghantagadi['Full coverage']  if 'Full coverage' in waste_coverage_ghantagadi.keys() else 0
    # gadi_part = waste_coverage_ghantagadi['Partial coverage']  if 'Partial coverage' in waste_coverage_ghantagadi.keys() else 0
    # gado_no = waste_coverage_ghantagadi['0'] if '0' in waste_coverage_ghantagadi.keys() else 0

    # full_coverage = gadi_full+van_full+dtd_full+mla_full
    # partial_coverage =gadi_part+van_part+dtd_part+mla_part
    # no_coverage = gado_no + van_no+ mla_no+ dtd_no

    freq_door = slum_name.values('waste_coll_freq_door_to_door').annotate(count=Count('waste_coll_freq_door_to_door'))
    for i in freq_door:
        waste_freq_door[i['waste_coll_freq_door_to_door']] = i['count']
    door_freq = waste_freq_door['Less than twice a week'] if 'Less than twice a week' in waste_freq_door.keys() else 0
    door_freq_daily = waste_freq_door['Daily'] if 'Daily' in waste_freq_door.keys() else 0

    freq_van = slum_name.values('waste_coll_freq_by_ulb_van').annotate(count=Count('waste_coll_freq_by_ulb_van'))
    for i in freq_van:
        waste_freq_van[i['waste_coll_freq_by_ulb_van']] = i['count']
    van_freq = waste_freq_van['Less than twice a week'] if 'Less than twice a week' in waste_freq_van.keys() else 0
    van_freq_daily = waste_freq_van['Daily'] if 'Daily' in waste_freq_van.keys() else 0

    freq_tempo= slum_name.values('waste_coll_freq_by_mla_tempo').annotate(count=Count('waste_coll_freq_by_mla_tempo'))
    for i in freq_tempo:
        waste_freq_tempo[i['waste_coll_freq_by_mla_tempo']] = i['count']
    tempo_freq = waste_freq_tempo['Less than twice a week'] if 'Less than twice a week' in waste_freq_tempo.keys() else 0
    tempo_freq_daily = waste_freq_tempo['Daily'] if 'Daily' in waste_freq_tempo.keys() else 0

    freq_ghantagadi = slum_name.values('waste_coll_freq_by_ghantagadi').annotate(count=Count('waste_coll_freq_by_ghantagadi'))
    for i in freq_ghantagadi:
        waste_freq_ghantagadi[i['waste_coll_freq_by_ghantagadi']] = i['count']
    gadi_freq = waste_freq_ghantagadi['Less than twice a week'] if 'Less than twice a week' in waste_freq_ghantagadi.keys() else 0
    gadi_freq_daily = waste_freq_ghantagadi['Daily'] if 'Daily' in waste_freq_ghantagadi.keys() else 0

    freq_colln_twice = door_freq+van_freq+gadi_freq+tempo_freq
    freq_colln_daily = gadi_freq_daily+tempo_freq_daily+door_freq_daily+van_freq_daily

    #road data
    slum_level = slum_name.filter(is_the_settlement_below_or_above='Below').count()
    huts_level = slum_name.filter(are_the_huts_below_or_above='Above').count()
    vehicle_access = slum_name.filter(point_of_vehicular_access='More than one').count()
    #drainage data
    drain_gradient_adequete = slum_name.filter(is_the_drainage_gradient_adequ='Yes').count()
    # drain_gradient_inadequet = slum_name.filter(is_the_drainage_gradient_adequ='No').count()
    drain_block = slum_name.filter(do_the_drains_get_blocked='Yes').count()
    #gutter data
    gutter_grd_adequete = slum_name.filter(do_gutters_flood='Yes').count()
    # gutter_grd_inadequet = slum_name.filter(do_gutters_flood='No').count()
    gutter_flood = slum_name.filter(is_gutter_gradient_adequate='Yes').count()

    for k1,v1 in CARDS.items():
        cards = {}
        if k1 == 'Keytakeaways':
            for k,v in v1.items():
                cards[k] = []
                if k == 'General':
                    cards[k]= [gen_land_status,gen_land_owner,gen_land_topography]
                    all_cards.update(cards)
                elif k == 'Water':
                    cards[k]= [water_availability_2hrs,water_availability_24_7,quality_poor,qualiyt_good,
                               coverage_full,prtial_coverage,tanker,standpost]
                    all_cards.update(cards)
                elif k == 'Waste':
                    cards[k] = [dump_sites,dump_in_drain,count_waste_container,full_coverage, partial_coverage, no_coverage,freq_colln_twice,freq_colln_daily]
                    all_cards.update(cards)
                elif k == 'Road':
                    cards[k]= [slum_level,huts_level,vehicle_access]
                    all_cards.update(cards)
                else:
                    cards[k]= [drain_block,drain_gradient_adequete,gutter_flood,gutter_grd_adequete]
                    all_cards.update(cards)
    return all_cards

def dashboard_all_cards(request,key):
    '''dashboard all cities card data'''
    def get_data(key):
        dict_filter = {}
        output_data = {'city': OrderedDict()}
        if key != 'all':
            dict_filter['id'] = key
        cities = City.objects.filter(**dict_filter).order_by('name__city_name')
        for city in cities:
            dashboard_data = DashboardData.objects.filter(city=city).aggregate(Sum('slum_population'),
                                                                                       Sum('household_count'),
                                                                                       Sum('count_of_toilets_completed'),
                                                                                       Sum('people_impacted'))
            slum_count = Slum.objects.filter(electoral_ward__administrative_ward__city=city, associated_with_SA=True).count()
            total_slum_count = Slum.objects.filter(electoral_ward__administrative_ward__city=city).exclude(status=False).count()
            qol_scores = QOLScoreData.objects.filter(city=city).aggregate(Avg('totalscore_percentile'))
            city_name = city.name.city_name
            output_data['city'][city_name] = dashboard_data
            output_data['city'][city_name]['city_id'] = "city::" + city_name
            #output_data['city'][city_name]['city_id'] = "city::" + city_name
            output_data['city'][city_name].update(qol_scores)
            output_data['city'][city_name]['slum_count'] = slum_count
            output_data['city'][city_name]['total_slum_count'] = total_slum_count
        return output_data

    result = get_data(key)
    return HttpResponse(json.dumps(result), content_type='application/json')



def covid_data(request):
    
    return render(request, 'covid_data.html')


@csrf_exempt
@apply_permissions_ajax('mastersheet.can_view_mastersheet_report')
def give_report_covid_data(request):  # view for covid data
    tag_key_dict = json.loads(request.body)
 
    tag = tag_key_dict['tag']     # tag => city
    
    keys = tag_key_dict['keys']    # key => slum_id
  
    group_perm = request.user.groups.values_list('name', flat=True)
    if request.user.is_superuser:
        group_perm = Group.objects.all().values_list('name', flat=True)
    group_perm = map(lambda x: x.split(':')[-1], group_perm)

    keys = Slum.objects.filter(id__in=keys,
                                electoral_ward__administrative_ward__city__name__city_name__in=group_perm).values_list('id', flat=True) # keys => slum_id
    
    start_date = tag_key_dict['startDate']
    end_date = tag_key_dict['endDate']

    if start_date == None or end_date == None:
        start_date = datetime.datetime(2001, 1, 1).date()
        end_date = datetime.datetime.today().date()
    else:
        start_date = datetime.datetime.strptime(tag_key_dict['startDate'], "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(tag_key_dict['endDate'], "%Y-%m-%d").date()


    query_on = {'household_number': 'total_hh_m'}
 
    level_data = {
        'city':
            {
                'city_name': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level_id': F('slum__electoral_ward__administrative_ward__city__id')
            },
        'admin_ward':
            {
                'city_name': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level': F('slum__electoral_ward__administrative_ward__name'),
                'level_id': F('slum__electoral_ward__administrative_ward__id')
            },
        'electoral_ward':
            {
                'city_name': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level': F('slum__electoral_ward__name'),
                'level_id': F('slum__electoral_ward__id')
            },
        'slum':
            {
                'city_name': F('slum__electoral_ward__administrative_ward__city__name__city_name'),
                'level': F('slum__name'),
                'level_id': F('slum__id')
            }
    }

    report_table_data = defaultdict(dict)
    
    for query_field in query_on.keys():
        if query_field in ['household_number']:
            filter_field = {'slum__id__in': keys, 'last_modified_date__range': [start_date, end_date],
                            query_field + '__isnull': False}
        else:
            filter_field = {'slum__id__in': keys, query_field + '__range': [start_date, end_date]}
        count_field = {query_on[query_field]: Count('level_id')}
        
        tc = CovidData.objects.filter(**filter_field)\
            .exclude(household_number = 9999).distinct()\
            .annotate(**level_data[tag]).values('level', 'level_id', 'city_name', 'city')\
            .annotate(**count_field).order_by('city_name')
        
        

        tc = {obj_ad['level_id']: obj_ad for obj_ad in tc}

        for level_id, data in tc.items():
            report_table_data[level_id].update(data)
        

        
        tm = CovidData.objects.filter(**filter_field) \
            .exclude(household_number = 9999) \
            .annotate(**level_data[tag]).values('level_id','household_number', 'slum', 'city').distinct()

        house_data = HouseholdData.objects.all()
        covid_data = CovidData.objects.all()

        house_dict = {}
        sw_cnt = {}
        for i in tm:
            slum_= i['slum']
            if i['level_id'] in house_dict:
                if slum_ in house_dict[i['level_id']]:
                    temp = house_dict[i['level_id']][slum_]
                    temp.append(i['household_number'])
                    house_dict[i['level_id']][slum_] = temp
                else:
                    temp_dict = {}
                    temp_dict[slum_] = [i['household_number']]
                    house_dict[i['level_id']].update(temp_dict)                    
                sw_cnt[i['level_id']] += 1 
            else:
                temp_dict = {}
                temp_dict[slum_] = [i['household_number']]
                house_dict[i['level_id']] = temp_dict
                sw_cnt[i['level_id']] = 1

        level_ids = list(report_table_data.keys())

        for id_ in level_ids:
            if tag  == 'city':

                # for total surveyed Members
                th_ = house_data.filter(slum__electoral_ward__administrative_ward__city__id = id_, rhs_data__isnull = False).count()
                blw_18 = covid_data.filter(age__lt = 12, slum__electoral_ward__administrative_ward__city__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_0_11'] = blw_18
                btw_12_17 = covid_data.filter(age__range = [12, 17], slum__electoral_ward__administrative_ward__city__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_btw_12_17'] = btw_12_17
                ppl_abv_17 = covid_data.filter(age__gt = 17, slum__electoral_ward__administrative_ward__city__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_abv_17'] = ppl_abv_17

                # For age group 12 to 17
                #for both dose
                dose_both = covid_data.filter(age__range = [12, 17], slum__electoral_ward__administrative_ward__city__id = id_, take_first_dose = 'Yes', take_second_dose = 'Yes', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['2_dose_done_12_17'] = dose_both
                # for first dose only
                dose_one = covid_data.filter(age__range = [12, 17], slum__electoral_ward__administrative_ward__city__id = id_, take_first_dose = 'Yes', take_second_dose = 'No', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['1_dose_done_12_17'] = dose_one
                report_table_data[id_]['total_2_dose_elg_abv_17'] = dose_one
                # for No dose
                dose_no = covid_data.filter(Q(age__range = [12, 17]) & Q(slum__electoral_ward__administrative_ward__city__id = id_) & (Q(take_first_dose = 'No') | Q(take_first_dose__isnull = True)) & Q(last_modified_date__range = [start_date, end_date])).exclude(household_number = 9999).count()
                report_table_data[id_]['not_vaccinated_12_17'] = dose_no
                report_table_data[id_]['total_1_dose_elg_abv_17'] = dose_no

                # For age group above 17
                #for both dose
                dose_both = covid_data.filter(age__gt = 17, slum__electoral_ward__administrative_ward__city__id = id_, take_first_dose = 'Yes', take_second_dose = 'Yes', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['2_dose_done_abv_17'] = dose_both
                # for first dose only
                dose_one = covid_data.filter(age__gt = 17, slum__electoral_ward__administrative_ward__city__id = id_, take_first_dose = 'Yes', take_second_dose = 'No', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['1_dose_done_abv_17'] = dose_one
                report_table_data[id_]['total_2_dose_elg_abv_17'] = dose_one
                # for No dose
                dose_no = covid_data.filter(Q(age__gt = 17) & Q(slum__electoral_ward__administrative_ward__city__id = id_) & (Q(take_first_dose = 'No') | Q(take_first_dose__isnull = True)) & Q(last_modified_date__range = [start_date, end_date])).exclude(household_number = 9999).count()
                report_table_data[id_]['not_vaccinated_abv_18'] = dose_no
                report_table_data[id_]['total_1_dose_elg_abv_17'] = dose_no

                report_table_data[id_]['total_hh'] = th_
                report_table_data[id_]['total_sw_hh'] = sw_cnt[id_]

                # Total Reach percentage.

                total_structure = house_data.filter(slum__electoral_ward__administrative_ward__city__id = id_, rhs_data__isnull = False).values_list('rhs_data', flat = True)
                total_struc = [data['Type_of_structure_occupancy'] for data in total_structure if 'Type_of_structure_occupancy' in data and  data['Type_of_structure_occupancy'] != 'Shop']
                total_structure = len(total_struc)
                total_surveyed = report_table_data[id_]['total_sw_hh']
                per = (total_surveyed/total_structure)*100
                pr = "{:.3f}".format(per)
                report_table_data[id_]['pr'] = pr

                hh_list = house_dict[id_]
                occ_cnt = 0
                for k, v in hh_list.items():
                    hh_data1 = house_data.filter(household_number__in = v, slum__id = k, rhs_data__isnull = False).values_list('rhs_data', flat = True)
                    occ_data = [occ_cnt for i in hh_data1 if (i['Type_of_structure_occupancy'] and i['Type_of_structure_occupancy'] == 'Occupied house')]
                    occ_cnt += len(occ_data)
                report_table_data[id_]['total_oc_hh'] = occ_cnt

            elif tag == 'admin_ward':
                # For Total Surveyed Members
                th_ = house_data.filter(slum__electoral_ward__administrative_ward__id = id_).count()
                blw_18 = covid_data.filter(age__lt = 12, slum__electoral_ward__administrative_ward__id = id_).exclude(household_number = 9999, last_modified_date__range = [start_date, end_date]).count()
                report_table_data[id_]['total_ppl_0_11'] = blw_18
                btw_12_17 = covid_data.filter(age__range = [12, 17], slum__electoral_ward__administrative_ward__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_btw_12_17'] = btw_12_17
                ppl_abv_17 = covid_data.filter(age__gt = 17, slum__electoral_ward__administrative_ward__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_abv_17'] = ppl_abv_17

                # For age group 12 to 17
                #for both dose
                dose_both = covid_data.filter(age__range = [12, 17], slum__electoral_ward__administrative_ward__id = id_, take_first_dose = 'Yes', take_second_dose = 'Yes', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['2_dose_done_12_17'] = dose_both
                # for first dose only
                dose_one = covid_data.filter(age__range = [12, 17], slum__electoral_ward__administrative_ward__id = id_, take_first_dose = 'Yes', take_second_dose = 'No', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['1_dose_done_12_17'] = dose_one
                report_table_data[id_]['total_2_dose_elg_abv_17'] = dose_one
                # for No dose
                dose_no = covid_data.filter(Q(age__range = [12, 17]) & Q(slum__electoral_ward__administrative_ward__id = id_) & (Q(take_first_dose = 'No') | Q(take_first_dose__isnull = True)) & Q(last_modified_date__range = [start_date, end_date])).exclude(household_number = 9999).count()
                report_table_data[id_]['not_vaccinated_12_17'] = dose_no
                report_table_data[id_]['total_1_dose_elg_abv_17'] = dose_no

                # For age group above 17
                #for both dose
                dose_both = covid_data.filter(age__gt = 17, slum__electoral_ward__administrative_ward__id = id_, take_first_dose = 'Yes', take_second_dose = 'Yes', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['2_dose_done_abv_17'] = dose_both
                # for first dose only
                dose_one = covid_data.filter(age__gt = 17, slum__electoral_ward__administrative_ward__id = id_, take_first_dose = 'Yes', take_second_dose = 'No', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['1_dose_done_abv_17'] = dose_one
                report_table_data[id_]['total_2_dose_elg_abv_17'] = dose_one
                # for No dose
                dose_no = covid_data.filter(Q(age__gt = 17) & Q(slum__electoral_ward__administrative_ward__id = id_) & (Q(take_first_dose = 'No') | Q(take_first_dose__isnull = True)) & Q(last_modified_date__range = [start_date, end_date])).exclude(household_number = 9999).count()
                report_table_data[id_]['not_vaccinated_abv_18'] = dose_no
                report_table_data[id_]['total_1_dose_elg_abv_17'] = dose_no

                report_table_data[id_]['total_hh'] = th_
                report_table_data[id_]['total_sw_hh'] = sw_cnt[id_]

                # Total Reach percentage.

                total_structure = house_data.filter(slum__electoral_ward__administrative_ward__id = id_, rhs_data__isnull = False).values_list('rhs_data', flat = True)
                total_struc = [data['Type_of_structure_occupancy'] for data in total_structure if 'Type_of_structure_occupancy' in data and  data['Type_of_structure_occupancy'] != 'Shop']
                total_structure = len(total_struc)
                total_surveyed = report_table_data[id_]['total_sw_hh']
                per = (total_surveyed/total_structure)*100
                pr = "{:.3f}".format(per)
                report_table_data[id_]['pr'] = pr

                hh_list = house_dict[id_]
                occ_cnt = 0
                for k, v in hh_list.items():
                    hh_data1 = house_data.filter(household_number__in = v, slum__id = k, rhs_data__isnull = False).values_list('rhs_data', flat = True)
                    occ_data = [occ_cnt for i in hh_data1 if (i['Type_of_structure_occupancy'] and i['Type_of_structure_occupancy'] == 'Occupied house')]
                    occ_cnt += len(occ_data)
                report_table_data[id_]['total_oc_hh'] = occ_cnt

            elif tag == 'electoral_ward':
                # For Total Surveyed Members
                th_ = house_data.filter(slum__electoral_ward__id = id_).count()
                blw_18 = covid_data.filter(age__lt = 12, slum__electoral_ward__id = id_).exclude(household_number = 9999, last_modified_date__range = [start_date, end_date]).count()
                report_table_data[id_]['total_ppl_0_11'] = blw_18
                btw_12_17 = covid_data.filter(age__range = [12, 17], slum__electoral_ward__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_btw_12_17'] = btw_12_17
                ppl_abv_17 = covid_data.filter(age__gt = 17, slum__electoral_ward__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_abv_17'] = ppl_abv_17

                # For age group 12 to 17
                #for both dose
                dose_both = covid_data.filter(age__range = [12, 17], slum__electoral_ward__id = id_, take_first_dose = 'Yes', take_second_dose = 'Yes', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['2_dose_done_12_17'] = dose_both
                # for first dose only
                dose_one = covid_data.filter(age__range = [12, 17], slum__electoral_ward__id = id_, take_first_dose = 'Yes', take_second_dose = 'No', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['1_dose_done_12_17'] = dose_one
                report_table_data[id_]['total_2_dose_elg_abv_17'] = dose_one
                # for No dose
                dose_no = covid_data.filter(Q(age__range = [12, 17]) & Q(slum__electoral_ward__id = id_) & (Q(take_first_dose = 'No') | Q(take_first_dose__isnull = True)) & Q(last_modified_date__range = [start_date, end_date])).exclude(household_number = 9999).count()
                report_table_data[id_]['not_vaccinated_12_17'] = dose_no
                report_table_data[id_]['total_1_dose_elg_abv_17'] = dose_no

                # For age group above 17
                #for both dose
                dose_both = covid_data.filter(age__gt = 17, slum__electoral_ward__id = id_, take_first_dose = 'Yes', take_second_dose = 'Yes', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['2_dose_done_abv_17'] = dose_both
                # for first dose only
                dose_one = covid_data.filter(age__gt = 17, slum__electoral_ward__id = id_, take_first_dose = 'Yes', take_second_dose = 'No', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['1_dose_done_abv_17'] = dose_one
                report_table_data[id_]['total_2_dose_elg_abv_17'] = dose_one
                # for No dose
                dose_no = covid_data.filter(Q(age__gt = 17) & Q(slum__electoral_ward__id = id_) & (Q(take_first_dose = 'No') | Q(take_first_dose__isnull = True) & Q(last_modified_date__range = [start_date, end_date]))).exclude(household_number = 9999).count()
                report_table_data[id_]['not_vaccinated_abv_18'] = dose_no
                report_table_data[id_]['total_1_dose_elg_abv_17'] = dose_no

                report_table_data[id_]['total_hh'] = th_
                report_table_data[id_]['total_sw_hh'] = sw_cnt[id_]

                # Total Reach percentage.

                total_structure = house_data.filter(slum__electoral_ward__id = id_, rhs_data__isnull = False).values_list('rhs_data', flat = True)
                total_struc = [data['Type_of_structure_occupancy'] for data in total_structure if 'Type_of_structure_occupancy' in data and  data['Type_of_structure_occupancy'] != 'Shop']
                total_structure = len(total_struc)
                total_surveyed = report_table_data[id_]['total_sw_hh']
                per = (total_surveyed/total_structure)*100
                pr = "{:.3f}".format(per)
                report_table_data[id_]['pr'] = pr

                hh_list = house_dict[id_]
                occ_cnt = 0
                for k, v in hh_list.items():
                    hh_data1 = house_data.filter(household_number__in = v, slum__id = k, rhs_data__isnull = False).values_list('rhs_data', flat = True)
                    occ_data = [occ_cnt for i in hh_data1 if (i['Type_of_structure_occupancy'] and i['Type_of_structure_occupancy'] == 'Occupied house')]
                    occ_cnt += len(occ_data)
                report_table_data[id_]['total_oc_hh'] = occ_cnt

            elif tag == 'slum':
                # For Total Surveyed Members
                th_ = house_data.filter(slum__id = id_).count()
                blw_18 = covid_data.filter(age__lt = 12, slum__id = id_).exclude(household_number = 9999, last_modified_date__range = [start_date, end_date]).count()
                report_table_data[id_]['total_ppl_0_11'] = blw_18
                btw_12_17 = covid_data.filter(age__range = [12, 17], slum__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_btw_12_17'] = btw_12_17
                ppl_abv_17 = covid_data.filter(age__gt = 17, slum__id = id_, last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['total_ppl_abv_17'] = ppl_abv_17

                # For age group 12 to 17
                #for both dose
                dose_both = covid_data.filter(age__range = [12, 17], slum__id = id_, take_first_dose = 'Yes', take_second_dose = 'Yes', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['2_dose_done_12_17'] = dose_both
                # for first dose only
                dose_one = covid_data.filter(age__range = [12, 17], slum__id = id_, take_first_dose = 'Yes', take_second_dose = 'No', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['1_dose_done_12_17'] = dose_one
                report_table_data[id_]['total_2_dose_elg_abv_17'] = dose_one
                # for No dose
                dose_no = covid_data.filter(Q(age__range = [12, 17]) & Q(slum__id = id_) & (Q(take_first_dose = 'No') | Q(take_first_dose__isnull = True)) & Q(last_modified_date__range = [start_date, end_date])).exclude(household_number = 9999).count()
                report_table_data[id_]['not_vaccinated_12_17'] = dose_no
                report_table_data[id_]['total_1_dose_elg_abv_17'] = dose_no

                # For age group above 17
                #for both dose
                dose_both = covid_data.filter(age__gt = 17, slum__id = id_, take_first_dose = 'Yes', take_second_dose = 'Yes', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['2_dose_done_abv_17'] = dose_both
                # for first dose only
                dose_one = covid_data.filter(age__gt = 17, slum__id = id_, take_first_dose = 'Yes', take_second_dose = 'No', last_modified_date__range = [start_date, end_date]).exclude(household_number = 9999).count()
                report_table_data[id_]['1_dose_done_abv_17'] = dose_one
                report_table_data[id_]['total_2_dose_elg_abv_17'] = dose_one
                # for No dose
                dose_no = covid_data.filter(Q(age__gt = 17) & Q(slum__id = id_) & (Q(take_first_dose = 'No') | Q(take_first_dose__isnull = True)) & Q(last_modified_date__range = [start_date, end_date])).exclude(household_number = 9999).count()
                report_table_data[id_]['not_vaccinated_abv_18'] = dose_no
                report_table_data[id_]['total_1_dose_elg_abv_17'] = dose_no

                report_table_data[id_]['total_hh'] = th_
                report_table_data[id_]['total_sw_hh'] = sw_cnt[id_]

                # Total Reach percentage.
                total_structure = house_data.filter(slum__id = id_, rhs_data__isnull = False).values_list('rhs_data', flat = True)
                total_struc = [data['Type_of_structure_occupancy'] for data in total_structure if 'Type_of_structure_occupancy' in data and  data['Type_of_structure_occupancy'] != 'Shop']
                total_structure = len(total_struc)
                total_surveyed = report_table_data[id_]['total_sw_hh']
                per = (total_surveyed/total_structure)*100
                pr = "{:.3f}".format(per)
                report_table_data[id_]['pr'] = pr

                # Total Occupied Households.
                hh_list = house_dict[id_]
                occ_cnt = 0
                for k, v in hh_list.items():
                    hh_data1 = house_data.filter(household_number__in = v, slum__id = k, rhs_data__isnull = False).values_list('rhs_data', flat = True)
                    occ_data = [occ_cnt for i in hh_data1 if (i['Type_of_structure_occupancy'] and i['Type_of_structure_occupancy'] == 'Occupied house')]
                    occ_cnt += len(occ_data)
                report_table_data[id_]['total_oc_hh'] = occ_cnt

    return HttpResponse(json.dumps(list(map(lambda x: report_table_data[x], report_table_data))),
                        content_type="application/json")


# for tase to generate csv file

def factsheetData(request):

    return render(request, 'factsheet_data.html')

def factsheetDataDownload(request):         #     function for city wise factsheet data download.
    
    if request.method == 'POST':
        c_id = request.POST.get('City')
        startdate = request.POST.get('startdate')
        enddate = request.POST.get('enddate')
    
    a, city_name = cityWiseQuery(c_id, startdate, enddate)

    filename = city_name+'.csv'
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition']  =  'attachment; filename='+filename

    writer = csv.DictWriter(response, ['Slum Name', 'Household_number', 'Name As Per RHS',  'Name As Per Factsheet', 'Ownership Status As Per Factsheet', 'Application id', 'Aadhar Number', 'Phone Number', 'Total_family_members', 'Male_members', 'Female_members', 'Below 5 years', 'Between_0_to_18', 'Above 60 years', 'disable_members', 'Toilet Connected To.', 'Have You Upgraded ?', 'Cost Of Upgradetion?', 'Sponsor Name'])
    writer.writeheader()
    writer.writerows(a)

    return response

def cityWiseQuery(city_id, startdate, enddate):
    all=[]
    city = CityReference.objects.filter(id = City.objects.filter(id = city_id).values_list('name_id')[0][0]).values_list('city_name')[0][0]

    construction_pocket = ToiletConstruction.objects.filter(slum__electoral_ward__administrative_ward__city__id = city_id, completion_date__range= [startdate, enddate])

    household_list = HouseholdData.objects.filter(city_id = city_id).values_list('household_number',flat= True)
    fff_data = HouseholdData.objects.filter(ff_data__isnull=False,city_id =city_id)

    family_factsheet_available = fff_data.values_list('household_number',flat= True)


    for i in fff_data:
        for j in construction_pocket :
            if i.household_number == j.household_number and i.slum_id == j.slum_id :
                family_data = {}
                family_data.update({'Household_number': i.household_number})

                sp = SponsorProjectDetails.objects.filter(slum_id = i.slum_id).exclude(sponsor_id = 10).values_list('household_code', 'sponsor_project_id')
                sp_name = ""
                for i1 in sp:
                    if i1[0] is not None:
                        if int(i.household_number) in i1[0]:
                            sp_name = SponsorProject.objects.filter(id = i1[1]).values_list('name', flat=True)[0]
                            break

                if sp_name == "":
                    family_data.update({'Sponsor Name': "Funder Not Assign"})
                else:
                    family_data.update({'Sponsor Name': sp_name})

                slum_name = Slum.objects.filter(id = i.slum_id).values_list('name',flat = True)[0]

                data1 =  SBMUpload.objects.filter(household_number = i.household_number, slum__id = i.slum_id).values_list('name', 'application_id', 'aadhar_number', 'phone_number')

                
                household_list = HouseholdData.objects.filter(household_number = i.household_number, slum__id = i.slum_id).values_list('rhs_data',flat= True)

                if  len(household_list) > 0:
                    if household_list[0] is not None and  household_list[0]['Type_of_structure_occupancy'] == 'Occupied house':
                        family_data.update({'Name As Per RHS': household_list[0]['group_og5bx85/Full_name_of_the_head_of_the_household']})
                
                if data1.exists() == True:
                    data = data1.values_list('application_id', 'aadhar_number', 'phone_number')
                    if data[0][0] != 'nan':
                        family_data.update({'Application id': data[0][0]})
                    if data[0][1] != 'nan':
                        family_data.update({'Aadhar Number': data[0][1]})
                    if data[0][2] != 'nan':
                        family_data.update({'Phone Number': data[0][2]})

                
                family_data.update({'Slum Name': slum_name})
                ff_keys = i.ff_data.keys()
                if 'group_im2th52/Total_family_members' in ff_keys:
                    family_data.update({'Total_family_members': i.ff_data['group_im2th52/Total_family_members']})

                if 'group_im2th52/Number_of_members_over_60_years_of_age' in ff_keys:
                    family_data.update({'Above 60 years': i.ff_data['group_im2th52/Number_of_members_over_60_years_of_age']})
                elif 'group_im2th52Number_of_members_over_60_years_of_age' in ff_keys:
                    family_data.update({'Above 60 years': i.ff_data['group_im2th52Number_of_members_over_60_years_of_age']})

                if 'group_im2th52/Number_of_disabled_members' in ff_keys:
                    family_data.update({'disable_members': i.ff_data['group_im2th52/Number_of_disabled_members']})

                if 'group_im2th52/Number_of_Male_members' in ff_keys:
                    family_data.update({'Male_members': i.ff_data['group_im2th52/Number_of_Male_members']})

                if 'group_im2th52/Number_of_Female_members' in ff_keys:
                    family_data.update({'Female_members': i.ff_data['group_im2th52/Number_of_Female_members']})

                if 'group_im2th52/Number_of_Girl_children_between_0_18_yrs' in ff_keys:
                    family_data.update({'Between_0_to_18': i.ff_data['group_im2th52/Number_of_Girl_children_between_0_18_yrs']})

                if 'group_im2th52/Number_of_Children_under_5_years_of_age' in ff_keys:
                    family_data.update({'Below 5 years': i.ff_data['group_im2th52/Number_of_Children_under_5_years_of_age']})
                
                if 'group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet' in ff_keys:
                    family_data.update({'Have You Upgraded ?': i.ff_data['group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet']})
                
                if 'group_ne3ao98/Cost_of_upgradation_in_Rs' in ff_keys:
                    family_data.update({'Cost Of Upgradetion?': i.ff_data['group_ne3ao98/Cost_of_upgradation_in_Rs']})
                
                if 'group_ne3ao98/Where_the_individual_ilet_is_connected_to' in ff_keys:
                    family_data.update({'Toilet Connected To.': i.ff_data['group_ne3ao98/Where_the_individual_ilet_is_connected_to']})
                
                if 'group_oh4zf84/Name_of_the_family_head' in ff_keys:
                    family_data.update({'Name As Per Factsheet': i.ff_data['group_oh4zf84/Name_of_the_family_head']})

                if 'group_oh4zf84/Ownership_status' in ff_keys:
                    family_data.update({'Ownership Status As Per Factsheet': i.ff_data['group_oh4zf84/Ownership_status']})

                 
                
                all.append(family_data)


    return all, city