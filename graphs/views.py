from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from itertools import groupby
from django.db.models import Avg,Sum
from graphs.models import *
from master.models import *
import json

CARDS = {'General':[{'gen_avg_household_size':"Avg Household size"}, {'gen_tenement_density':"Tenement density (Persons/Hector)"}],
         'Waste': [{'waste_no_collection_facility_percentile':'No waste collection'},
                   {'waste_door_to_door_collection_facility_percentile':'Door to door waste collection'},
                   {'waste_dump_in_open_percent':'Dump in open'}],
         'Water': [{'water_individual_connection_percentile':'Individual water connection'}],#,{'water_no_service_percentile':'No service'}],
         'Toilet': [{'toilet_seat_to_person_ratio':'Toilet to person ratio'},{'toilet_men_women_seats_ratio':'Men to women toilet seats ratio'}],
                    # {'individual_toilet_coverage':'Individual Toilets'},{'open_defecation_coverage':'Open defecation'},{'ctb_coverage':'CTB coverage'}],
         'Road': [{'pucca_road':'No. of slums with pucca road'},{'road_with_no_vehicle_access':'Slums with no vehicle access'},
                  {'pucca_road_coverage':'Pucca Road Coverage'},{'kutcha_road_coverage':'Kutcha Road Coverage'},
                  {'kutcha_road':'No. of slums with kutcha road'}]}
         # 'Drainage':[{'drains_coverage':'Drain coverage'}]}

@login_required(login_url='/accounts/login/')
def graphs_display(request, graph_type):
    custom_url = settings.GRAPHS_BUILD_URL % settings.GRAPH_DETAILS[graph_type][1::-1]
    return render(request, 'graphs.html', {'custom_url':custom_url})

def get_dashboard_card(request, key):
    output_data = {'city':{}, 'admin_ward':{}, 'electoral_ward':{}, 'slum':{}}
    select_clause = ['totalscore_percentile', 'general_percentile', 'drainage_percentile',
                     'road_percentile', 'toilet_percentile', 'water_percentile', 'waste_percentile']

    city = get_object_or_404(City, pk=key)

    #City level
    output_data['city'][city.name.city_name] = {'scores':{}, 'cards':{}}
    qol_scores = QOLScoreData.objects.filter(city=city)
    for clause in select_clause:
        output_data['city'][city.name.city_name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
    cities = DashboardData.objects.filter(city=city)
    cards = score_cards(cities)
    output_data['city'][city.name.city_name]['cards'] = cards

    #Administrative ward calculations
    for admin_ward in AdministrativeWard.objects.filter(city=city):
        output_data['admin_ward'][admin_ward.name] = {'scores': {}, 'cards':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        for clause in select_clause:
            output_data['admin_ward'][admin_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        admin_wards = DashboardData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        cards = score_cards(admin_wards)
        output_data['admin_ward'][admin_ward.name]['cards'] = cards

    #Electoral ward calculations
    for electoral_ward in ElectoralWard.objects.filter(administrative_ward__city=city):
        output_data['electoral_ward'][electoral_ward.name] = {'scores': {}, 'cards':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward=electoral_ward)
        for clause in select_clause:
            output_data['electoral_ward'][electoral_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        ele_wards = DashboardData.objects.filter(slum__electoral_ward=electoral_ward)
        if ele_wards.count() > 0:
            cards = score_cards(ele_wards)
            output_data['electoral_ward'][electoral_ward.name]['cards'] = cards

    #Slum level calculations
    output_data['slum'] = {'scores':{},'cards':{}}
    select_clause.append('slum__name')
    qol_scores = QOLScoreData.objects.filter(city = city).values(*select_clause)
    qol_scores = groupby(qol_scores, key=lambda x:x['slum__name'])
    qol_scores = {key: {'scores': list(values)[0],'cards': get_card_data(key)} for key, values in qol_scores}
    output_data['slum'] = qol_scores
    output_data['metadata'] = CARDS
    return HttpResponse(json.dumps(output_data),content_type='application/json')

def get_card_data(slum_name):
    all_cards = {}
    root_query = DashboardData.objects.filter(slum__name = slum_name)
    for k,v in CARDS.items():
        data_cards = {}
        data_cards[k] = [root_query.values_list(i.keys()[0], flat=True)[0] for i in v]
        data_cards = convert_float_to_str(data_cards)
        all_cards.update(data_cards)
    return all_cards

def convert_float_to_str(data_dict):

    roundoff_str = {}

    def to_str_per(i):
        r = round(float(i), 2) if i != None else 0.0
        roundoff_str[k].append(str(r) + '%')
        return roundoff_str

    def to_str(j):
        r = round(float(i), 2) if i != None else 0.0
        roundoff_str[k].append(str(r))
        return roundoff_str

    for k,v in data_dict.items():
        roundoff_str[k] = []
        if k in ['Waste', 'Water']:
            for i in v:
                if i != None:
                    roundoff_str.update(to_str_per(i))
        elif k == 'Road':
            for i in v:
                if v.index(i) in [2,3]:
                    roundoff_str.update(to_str_per(i))
                else:
                    roundoff_str.update(to_str(i))
        else:
            for i in v:
                roundoff_str.update(to_str(i))
    return roundoff_str

def score_cards(ele):
    all_cards ={}
    for k,v in CARDS.items():
        cards = {}
        if k == 'Road':
            cards[k] = []
            for i in v:
                for k1,v1 in i.items():
                    if k1 in ['kutcha_road','pucca_road','road_with_no_vehicle_access']:
                        avrg = ele.aggregate(Sum(k1)).values()[0]
                        cards[k].append(avrg)
                    else:
                        avrg = ele.aggregate(Avg(k1)).values()[0]
                        cards[k].append(avrg)
        else:
            avrg = [ele.aggregate(Avg(i.keys()[0])).values()[0] for i in v]
            cards[k] = avrg
        str = convert_float_to_str(cards) # convert values in "40.0%" format
        all_cards.update(str)
    return all_cards