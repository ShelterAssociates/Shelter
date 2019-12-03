from __future__ import division
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from itertools import groupby
from django.db.models import Avg,Sum, Count
from collections import OrderedDict
from graphs.models import *
from master.models import *
import json
from component.cipher import *
from django.db.models import Q

CARDS = {'Cards': {'General':[{'gen_avg_household_size':"Avg Household size"}, {'gen_tenement_density':"Tenement density (Huts/Hector)"},
                    {'household_owners_count':'Superstructure Ownership'}],
         'Waste': [{'waste_no_collection_facility_percentile':'Garbage Bin'},
                   {'waste_door_to_door_collection_facility_percentile':'Door to door waste collection'},
                   {'waste_dump_in_open_percent':'Dump in open'}],
         'Water': [{'water_individual_connection_percentile':'Individual water connection'},
                   {'water_shared_service_percentile':'Shared Water Connection'},{'waterstandpost_percentile':'Water Standposts'}],
         'Toilet': [{'toilet_seat_to_person_ratio':'Toilet to person seats ratio'},
                    {'toilet_men_women_seats_ratio':'Men|Women|Mix toilet seats'},
                    {'individual_toilet_coverage':'Individual Toilet Coverage'},{'ctb_coverage':'CTB usage'}],
         'Road': [{'road_with_no_vehicle_access':'No. of slums with no vehicle access'},
                  {'pucca_road_coverage':'Pucca Road Coverage'},{'kutcha_road_coverage':'Kutcha Road Coverage'}],
         'Drainage':[{'drainage_coverage':'Drain coverage'}]},
         'Keytakeaways' :
         {'General':[ [" &#128477 <b>value</b> slums with <b>undeclared</b> land status",],
                      [" <br> <b>value</b> slums with <b>private</b> land ownership",],
                      [" <br><b>value</b> slums likely to be affected by flooding, drainage and gutter problems due to <b>reasonable slope</b> of land topography"]],
         'Water': [[' &#128477 <b>value</b> slums where water availability  is <b>less than 2 hours</b>, '],
                  [' <b>value</b> with <b>water availability 24/7</b>'],
                  [' <br><b>value</b> slums with <b>poor</b> quality of water '],
                  [' <b>value</b> with <b>good</b> quality of water'],
                  [' <br><b>value</b> slums with <b>full water coverage</b> ,'],
                  [' <b>value</b> slums with <b>partial water coverage</b>'],
                  [' <br><b>value</b> slums where alternate water sources are <b>tanker</b> , '],
                  [' <b>value</b> with <b>water standposts</b>']],
         'Waste': [[' &#128477 <b>value</b>  slums having <b>open community dumping sites</b>'],
                   [' <br><b>value</b> slums practice <b> dumping in drains</b>'],
                   ['  <br><b>value</b> slums with <b>availability of waste containers</b>'],
                   ['  <br><b>value</b> slums with <b>full waste coverage</b> facility, '],
                   [' <b>value</b> with <b>partial waste coverage</b> , ' ],
                   [' <b>value</b> with <b> no coverage</b>'],
                   [' <br><b>value</b> slums with <b>daily</b>, '],
                   [' <b>value</b> with <b>twice a week </b> waste collection frequency']],
         'Road': [[' &#128477 <b>value</b>  slums having <b>more than one</b> vehicular access'],
                  [' <br><b>value</b>  slums where settlement is <b> below</b> access road'],
                  [' <br><b>value</b>  slums where huts are <b>above</b> internal roads']],
         'Drainage':[[' &#128477 <b>value</b>  slums where drains <b> get blocked </b>'],
                    [' <br><b>value</b> slums with <b>adequete</b> drain gradient, '],
                    [' <b>value</b>  with<b> inadequete </b>drain gradient'],
                    [' <br><b>value</b>  slums where gutter gets <b>flooded</b>'],
                    [' <br><b>value</b> slums with<b>adequete</b> gutter gradient, '],
                    [' <b>value</b> with <b> inadequete</b> gutter gradient']],
         'Toilet':[[' &#128477 <b>value</b>  slums where CTB structure is in <b> poor </b> condition'],
                   [' <br><b>value</b>  CTB seats out of total <b>are in good condition </b>'],
                   [' <br><b>value</b>  slums where <b> no availability of water</b> in CTB'],
                   [' <br><b>value</b>  slums where sewage is <b> laid in open</b>'],
                   [' <br><b>value</b>  slums where <b>no electricity in CTB at night</b>'],
                   [' <br><b>value</b>  slums where CTB is <b>not available at night</b>'],
                   [' <br><b>value</b> slums where cleanliness is <b> good</b> , '],
                   [' <b>value</b> slums where cleanliness is <b> poor </b>in condition']]
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
    qol_scores = QOLScoreData.objects.filter(city=city)
    for clause in select_clause:
        output_data['city'][city.name.city_name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
    cities = DashboardData.objects.filter(city=city)
    # city_keyTakeaways = SlumDataSplit.objects.filter(city=city)
    # city_keyTakeaways_ctb = SlumCTBdataSplit.objects.filter(city=city)
    cards = score_cards(cities)
    # key_takeaway = key_takeaways(city_keyTakeaways)
    # key_takeaway.update(key_takeaways_toilet(city_keyTakeaways_ctb))
    output_data['city'][city.name.city_name]['cards'] = cards
    # output_data['city'][city.name.city_name]['key_takeaways'] = key_takeaway

    #Administrative ward calculations
    for admin_ward in AdministrativeWard.objects.filter(city=city):
        output_data['administrative_ward'][admin_ward.name] = {'scores': {}, 'cards':{}}#, 'key_takeaways':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        for clause in select_clause:
            output_data['administrative_ward'][admin_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        admin_wards = DashboardData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        # admin_keyTakeaways = SlumDataSplit.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        # admin_keyTakeaways_ctb = SlumCTBdataSplit.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        cards = score_cards(admin_wards)
        # key_takeaway = key_takeaways(admin_keyTakeaways)
        # key_takeaway.update(key_takeaways_toilet(admin_keyTakeaways_ctb))
        output_data['administrative_ward'][admin_ward.name]['cards'] = cards
        # output_data['administrative_ward'][admin_ward.name]['key_takeaways'] = key_takeaway

    #Electoral ward calculations
    for electoral_ward in ElectoralWard.objects.filter(administrative_ward__city=city):
        output_data['electoral_ward'][electoral_ward.name] = {'scores': {}, 'cards':{} }#, 'key_takeaways':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward=electoral_ward)
        for clause in select_clause:
            output_data['electoral_ward'][electoral_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        ele_wards = DashboardData.objects.filter(slum__electoral_ward=electoral_ward)
        ele_keyTakeaways_other = SlumDataSplit.objects.filter(slum__electoral_ward=electoral_ward)
        # ele_keyTakeaways_ctb = SlumCTBdataSplit.objects.filter(slum__electoral_ward=electoral_ward)
        if ele_wards.count() > 0:
            cards = score_cards(ele_wards)
            # key_takeaway = key_takeaways(ele_keyTakeaways_other)
            # key_takeaway.update(key_takeaways_toilet(ele_keyTakeaways_ctb))
            output_data['electoral_ward'][electoral_ward.name]['cards'] = cards
            # output_data['electoral_ward'][electoral_ward.name]['key_takeaways'] = key_takeaway

    #Slum level calculations
    output_data['slum'] = {'scores':{},'cards':{}}#,'key_takeaways':{} }
    select_clause.append('slum__name')
    qol_scores = QOLScoreData.objects.filter(city=city).values(*select_clause)
    qol_scores = groupby(qol_scores, key=lambda x: x['slum__name'])
    qol_scores = {key: {'scores': list(values)[0],'cards': score_cards(DashboardData.objects.filter(slum__name=key))} for key, values in qol_scores}
                        # 'key_takeaways': all_key_takeaways(key) } for key, values in qol_scores}
    output_data['slum'] = qol_scores
    output_data['metadata'] = CARDS

    return HttpResponse(json.dumps(output_data),content_type='application/json')

# def all_key_takeaways(slum):
#     ''' collecting key take aways for all sections '''
#     ctb_data = key_takeaways_toilet(SlumCTBdataSplit.objects.filter(slum__name=slum))
#     other_sections = key_takeaways(SlumDataSplit.objects.filter(slum__name=slum))
#     ctb_data.update(other_sections)
#     return ctb_data

def score_cards(ele):
    """To calculate aggregate level data for electoral, admin and city"""
    all_cards ={ }
    aggrgated_data = ele.aggregate(Sum('occupied_household_count'),Sum('household_count'),
        Sum('total_road_area'),Sum('road_with_no_vehicle_access'),Sum('pucca_road_coverage'),Sum('kutcha_road_coverage'),
        Sum('gen_avg_household_size'),Sum('gen_tenement_density'),Sum('household_owners_count'),
        Sum('waste_no_collection_facility_percentile'),Sum('waste_door_to_door_collection_facility_percentile'),Sum('waste_dump_in_open_percent'),
        Sum('water_individual_connection_percentile'),Sum('water_shared_service_percentile'),Sum('waterstandpost_percentile'),
        Sum('toilet_seat_to_person_ratio'),Sum('individual_toilet_coverage'),Sum('fun_male_seats'),Sum('fun_fmale_seats'),
        Sum('toilet_men_women_seats_ratio'),Sum('ctb_coverage'),Sum('get_shops_count'))

    #drainage_card data
    slum_ids = ele.values_list('slum__id',flat=True)
    total_drain_count = 0
    data = Rapid_Slum_Appraisal.objects.filter(slum_name__id__in = slum_ids).aggregate(Sum('drainage_coverage'))
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
                    only_ctb_user = aggrgated_data['occupied_household_count__sum'] if aggrgated_data['occupied_household_count__sum'] else 0 - aggrgated_data['individual_toilet_coverage__sum'] if aggrgated_data['individual_toilet_coverage__sum'] else 0
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
                    cards[k].append(str(round(aggrgated_data['gen_avg_household_size__sum']/aggrgated_data['occupied_household_count__sum']\
                                              if aggrgated_data['occupied_household_count__sum'] else 0,2)))
                    house_n_shops_count = aggrgated_data['get_shops_count__sum'] + aggrgated_data['household_count__sum']
                    cards[k].append(str(int(house_n_shops_count/ aggrgated_data['gen_tenement_density__sum'] if aggrgated_data['gen_tenement_density__sum'] else 0)))
                    cards[k].append(str(round((aggrgated_data['household_owners_count__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    all_cards.update(cards)
                elif k =='Water':
                    cards[k].append(str(round((aggrgated_data['water_individual_connection_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    cards[k].append(str(round((aggrgated_data['water_shared_service_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    cards[k].append(str(round((aggrgated_data['waterstandpost_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
                    all_cards.update(cards)
                else:
                    cards[k].append(str(round((aggrgated_data['waste_no_collection_facility_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0, 2)) + " %")
                    cards[k].append(str(round((aggrgated_data['waste_door_to_door_collection_facility_percentile__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0, 2)) + " %")
                    cards[k].append(str(round((aggrgated_data['waste_dump_in_open_percent__sum'] / aggrgated_data['occupied_household_count__sum']) * 100 if aggrgated_data['occupied_household_count__sum'] else 0, 2)) + " %")
                    all_cards.update(cards)
        else :
            pass
    return all_cards

# def key_takeaways_toilet(slum):
#     '''calculating count of toilet sections' key take aways'''
#     all_cards={}
#     safe_m1 = 0
#     safe_m2 = 0
#     water =0
#     electricity =0
#     sewage =0
#     ctb_at_night =0
#     ctb_cleaning_good =0
#     ctb_cleaning_poor =0
#     for i in slum:
#         safe_m1 += 1 if i.ctb_structure_condition == 'Poor' else 0
#         safe_m2 += int(i.seats_in_good_condtn) if i.seats_in_good_condtn != 0 else 0
#         water += 1 if i.water_availability == ' Not available' else 0
#         electricity += 1 if i.electricity_in_ctb == 'No' else 0
#         sewage += 1 if i.sewage_disposal_system == 'Laid in the open' else 0
#         ctb_at_night += 1 if i.ctb_available_at_night in ['No','Yes, but Not all night'] else 0
#         ctb_cleaning_poor += 1 if i.cleanliness_of_the_ctb == 'Poor' else 0
#         ctb_cleaning_good += 1 if i.cleanliness_of_the_ctb == 'Good' else 0
#     all_cards['Toilet']=[safe_m1,safe_m2,water,sewage,electricity,ctb_at_night,ctb_cleaning_good,ctb_cleaning_poor]
#     return all_cards

# def key_takeaways(slum_name):
#     '''count of key take aways, section wise'''
#     all_cards = {}
#
#    #general data
#     gen_land_status =slum_name.filter(land_status='Undeclared').count()
#     gen_land_owner =slum_name.filter(land_ownership='Private').count()
#     gen_land_topography =slum_name.filter(land_topography='Depression Slope').count()
#
#     #water data
#     water_availability ={}
#     water_quality ={}
#     water_coverage ={}
#     water_source ={}
#
#     availability = slum_name.values('availability_of_water').annotate(count=Count('availability_of_water'))
#     for i in availability:
#         water_availability[i['availability_of_water']]= i['count']
#     water_availability_2hrs = water_availability['Less than 2 hrs']  if 'Less than 2 hrs' in water_availability.keys() else 0
#     water_availability_24_7 = water_availability['24/7']  if 'Daily' in water_availability.keys() else 0
#
#     quality = slum_name.values('quality_of_water').annotate(count=Count('quality_of_water'))
#     for i in quality:
#         water_quality[i['quality_of_water']]= i['count']
#     quality_poor = water_quality['Poor']  if 'Poor' in water_quality.keys() else 0
#     qualiyt_good = water_quality['Good']  if 'Good' in water_quality.keys() else 0
#
#     coverage = slum_name.values('coverage_of_water').annotate(count=Count('coverage_of_water'))
#     for i in coverage:
#         water_coverage[i['coverage_of_water']]= i['count']
#     coverage_full = water_coverage["Full coverage"]  if 'Full coverage' in water_coverage.keys() else 0
#     prtial_coverage = water_coverage['Partial coverage']  if 'Partial coverage' in water_coverage.keys() else 0
#
#     source = slum_name.values('alternative_source_of_water').annotate(count=Count('alternative_source_of_water'))
#     for i in source:
#         water_source[i['alternative_source_of_water']]= i['count']
#     tanker = water_source['Tanker']  if 'Tanker' in water_source.keys() else 0
#     standpost = water_source['Water standpost']  if 'Water standpost' in water_source.keys() else 0
#
#     #waste data
#     waste_coverage_door ={}
#     waste_coverage_tempo = {}
#     waste_coverage_van = {}
#     waste_coverage_ghantagadi = {}
#     waste_freq_door = {}
#     waste_freq_tempo = {}
#     waste_freq_van = {}
#     waste_freq_ghantagadi = {}
#
#     count_waste_container = 0
#     dump_sites = slum_name.filter(~Q(community_dump_sites = 'None')).count()
#     dump_in_drain = slum_name.filter(dump_in_drains ='Yes').count()
#     container = int(slum_name.values_list('number_of_waste_container',flat=True)[0])
#     count_waste_container += container
#
#     cvrg_door_t_door = slum_name.values('waste_coverage_door_to_door').annotate(count=Count('waste_coverage_door_to_door'))
#     for i in cvrg_door_t_door:
#         waste_coverage_door[i['waste_coverage_door_to_door']] = i['count']
#     dtd_full = waste_coverage_door['Full coverage'] if 'Full coverage' in waste_coverage_door.keys() else 0
#     dtd_part = waste_coverage_door['Partial coverage'] if 'Partial coverage' in waste_coverage_door.keys() else 0
#     dtd_no = waste_coverage_door['0'] if '0' in waste_coverage_door.keys() else 0
#
#     cvrg_mla_tempo = slum_name.values('waste_coverage_by_mla_tempo').annotate(count=Count('waste_coverage_by_mla_tempo'))
#     for i in cvrg_mla_tempo:
#         waste_coverage_tempo[i['waste_coverage_by_mla_tempo']] = i['count']
#     mla_full = waste_coverage_tempo['Full coverage'] if 'Full coverage' in waste_coverage_tempo.keys() else 0
#     mla_part = waste_coverage_tempo['Partial coverage'] if 'Partial coverage' in waste_coverage_tempo.keys() else 0
#     mla_no = waste_coverage_tempo['0'] if '0' in waste_coverage_tempo.keys() else 0
#
#     cvrg_van = slum_name.values('waste_coverage_by_ulb_van').annotate(count=Count('waste_coverage_by_ulb_van'))
#     for i in cvrg_van:
#         waste_coverage_van[i['waste_coverage_by_ulb_van']]= i['count']
#     van_full = waste_coverage_van['Full coverage'] if 'Full coverage' in waste_coverage_van.keys() else 0
#     van_part = waste_coverage_van['Partial coverage'] if 'Partial coverage' in waste_coverage_van.keys() else 0
#     van_no = waste_coverage_van['0'] if '0' in waste_coverage_van.keys() else 0
#
#     cvrg_ghantagadi = slum_name.values('waste_coverage_by_ghantagadi').annotate(count=Count('waste_coverage_by_ghantagadi'))
#     for i in cvrg_ghantagadi:
#         waste_coverage_ghantagadi[i['waste_coverage_by_ghantagadi']] = i['count']
#     gadi_full = waste_coverage_ghantagadi['Full coverage']  if 'Full coverage' in waste_coverage_ghantagadi.keys() else 0
#     gadi_part = waste_coverage_ghantagadi['Partial coverage']  if 'Partial coverage' in waste_coverage_ghantagadi.keys() else 0
#     gado_no = waste_coverage_ghantagadi['0'] if '0' in waste_coverage_ghantagadi.keys() else 0
#
#     full_coverage = gadi_full+van_full+dtd_full+mla_full
#     partial_coverage =gadi_part+van_part+dtd_part+mla_part
#     no_coverage = gado_no+van_no+mla_no+dtd_no
#
#     freq_door = slum_name.values('waste_coll_freq_door_to_door').annotate(count=Count('waste_coll_freq_door_to_door'))
#     for i in freq_door:
#         waste_freq_door[i['waste_coll_freq_door_to_door']] = i['count']
#     door_freq = waste_freq_door['Less than twice a week'] if 'Less than twice a week' in waste_freq_door.keys() else 0
#     door_freq_daily = waste_freq_door['Daily'] if 'Daily' in waste_freq_door.keys() else 0
#
#     freq_van = slum_name.values('waste_coll_freq_by_ulb_van').annotate(count=Count('waste_coll_freq_by_ulb_van'))
#     for i in freq_van:
#         waste_freq_van[i['waste_coll_freq_by_ulb_van']] = i['count']
#     van_freq = waste_freq_van['Less than twice a week'] if 'Less than twice a week' in waste_freq_van.keys() else 0
#     van_freq_daily = waste_freq_van['Daily'] if 'Daily' in waste_freq_van.keys() else 0
#
#     freq_tempo= slum_name.values('waste_coll_freq_by_mla_tempo').annotate(count=Count('waste_coll_freq_by_mla_tempo'))
#     for i in freq_tempo:
#         waste_freq_tempo[i['waste_coll_freq_by_mla_tempo']] = i['count']
#     tempo_freq = waste_freq_tempo['Less than twice a week'] if 'Less than twice a week' in waste_freq_tempo.keys() else 0
#     tempo_freq_daily = waste_freq_tempo['Daily'] if 'Daily' in waste_freq_tempo.keys() else 0
#
#     freq_ghantagadi = slum_name.values('waste_coll_freq_by_ghantagadi').annotate(count=Count('waste_coll_freq_by_ghantagadi'))
#     for i in freq_ghantagadi:
#         waste_freq_ghantagadi[i['waste_coll_freq_by_ghantagadi']] = i['count']
#     gadi_freq = waste_freq_ghantagadi['Less than twice a week'] if 'Less than twice a week' in waste_freq_ghantagadi.keys() else 0
#     gadi_freq_daily = waste_freq_ghantagadi['Daily'] if 'Daily' in waste_freq_ghantagadi.keys() else 0
#
#     freq_colln_twice = door_freq+van_freq+gadi_freq+tempo_freq
#     freq_colln_daily = gadi_freq_daily+tempo_freq_daily+door_freq_daily+van_freq_daily
#
#     #road data
#     slum_level = slum_name.filter(is_the_settlement_below_or_above='Below').count()
#     huts_level = slum_name.filter(are_the_huts_below_or_above='Above').count()
#     vehicle_access = slum_name.filter(point_of_vehicular_access='More than one').count()
#     #drainage data
#     drain_gradient_adequete = slum_name.filter(is_the_drainage_gradient_adequ='Yes').count()
#     drain_gradient_inadequet = slum_name.filter(is_the_drainage_gradient_adequ='No').count()
#     drain_block = slum_name.filter(do_the_drains_get_blocked='Yes').count()
#     #gutter data
#     gutter_grd_adequete = slum_name.filter(do_gutters_flood='Yes').count()
#     gutter_grd_inadequet = slum_name.filter(do_gutters_flood='No').count()
#     gutter_flood = slum_name.filter(is_gutter_gradient_adequate='Yes').count()
#
#     for k1,v1 in CARDS.items():
#         cards = {}
#         if k1 == 'Keytakeaways':
#             for k,v in v1.items():
#                 cards[k] = []
#                 if k == 'General':
#                     cards[k]= [gen_land_status,gen_land_owner,gen_land_topography]
#                     all_cards.update(cards)
#                 elif k == 'Water':
#                     cards[k]= [water_availability_2hrs,water_availability_24_7,quality_poor,qualiyt_good,
#                                coverage_full,prtial_coverage,tanker,standpost]
#                     all_cards.update(cards)
#                 elif k == 'Waste':
#                     cards[k] = [dump_sites,dump_in_drain,count_waste_container,full_coverage,partial_coverage,no_coverage,
#                                 freq_colln_twice,freq_colln_daily]
#                     all_cards.update(cards)
#                 elif k == 'Road':
#                     cards[k]= [slum_level,huts_level,vehicle_access]
#                     all_cards.update(cards)
#                 else:
#                     cards[k]= [drain_block,drain_gradient_adequete,drain_gradient_inadequet,gutter_flood,gutter_grd_adequete,gutter_grd_inadequet]
#                     all_cards.update(cards)
#     return all_cards

def dashboard_all_cards(request,key):
    '''dashboard all cities card data'''
    def get_data(key):

        cipher = AESCipher()
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
            output_data['city'][city_name]['city_id'] = "city::" + cipher.encrypt(str(city.id))
            output_data['city'][city_name].update(qol_scores)
            output_data['city'][city_name]['slum_count'] = slum_count
            output_data['city'][city_name]['total_slum_count'] = total_slum_count
        return output_data

    result = get_data(key)
    return HttpResponse(json.dumps(result), content_type='application/json')
