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

CARDS = {'General':[{'gen_avg_household_size':"Avg Household size"}, {'gen_tenement_density':"Tenement density (Huts/Hector)"},
                    {'household_owners_count':'Superstructure Ownership'}],
         'Waste': [{'waste_no_collection_facility_percentile':'Garbage Bin'},
                   {'waste_door_to_door_collection_facility_percentile':'Door to door waste collection'},
                   {'waste_dump_in_open_percent':'Dump in open'}],
         'Water': [{'water_individual_connection_percentile':'Individual water connection'},
                   {'water_shared_service_percentile':'Shared Water Connection'},{'waterstandpost_percentile':'Water Standposts'}],
         'Toilet': [{'toilet_seat_to_person_ratio':'Toilet seat to person ratio'},
                    {'toilet_men_women_seats_ratio':'Men to women toilet seats ratio'},
                    {'individual_toilet_coverage':'Individual Toilet Coverage'},{'ctb_coverage':'CTB coverage'}],
         'Road': [{'road_with_no_vehicle_access':'No. of slums with no vehicle access'},
                  {'pucca_road_coverage':'Pucca Road Coverage'},{'kutcha_road_coverage':'Kutcha Road Coverage'}],
         'Drainage':[{'drainage_coverage':'Drain coverage'}]}

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
    output_data['city'][city.name.city_name] = {'scores':{}, 'cards':{}}
    qol_scores = QOLScoreData.objects.filter(city=city)
    for clause in select_clause:
        output_data['city'][city.name.city_name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
    cities = DashboardData.objects.filter(city=city)
    cards = score_cards(cities)
    output_data['city'][city.name.city_name]['cards'] = cards
    drain_cov_admin = Rapid_Slum_Appraisal.objects.filter(slum_name__electoral_ward__administrative_ward__city__name__city_name=city).values('drainage_coverage')
    drain_card_admin = drainage_coverage(drain_cov_admin)
    output_data['city'][city.name.city_name]['cards']['Drainage']= drain_card_admin

    #Administrative ward calculations
    for admin_ward in AdministrativeWard.objects.filter(city=city):
        output_data['administrative_ward'][admin_ward.name] = {'scores': {}, 'cards':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        for clause in select_clause:
            output_data['administrative_ward'][admin_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        admin_wards = DashboardData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        cards = score_cards(admin_wards)
        output_data['administrative_ward'][admin_ward.name]['cards'] = cards
        drain_coverage_admin = Rapid_Slum_Appraisal.objects.filter(slum_name__electoral_ward__administrative_ward=admin_ward)
        drain_card_admin = drainage_coverage(drain_coverage_admin)
        output_data['administrative_ward'][admin_ward.name]['cards']['Drainage'] = drain_card_admin

    #Electoral ward calculations
    for electoral_ward in ElectoralWard.objects.filter(administrative_ward__city=city):
        output_data['electoral_ward'][electoral_ward.name] = {'scores': {}, 'cards':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward=electoral_ward)
        for clause in select_clause:
            output_data['electoral_ward'][electoral_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        ele_wards = DashboardData.objects.filter(slum__electoral_ward=electoral_ward)
        drain_cover_wards = Rapid_Slum_Appraisal.objects.filter(slum_name__electoral_ward=electoral_ward)
        if ele_wards.count() > 0:
            cards = score_cards(ele_wards)
            output_data['electoral_ward'][electoral_ward.name]['cards'] = cards
            drain_card_elec = drainage_coverage(drain_cover_wards)
            output_data['electoral_ward'][electoral_ward.name]['cards']['Drainage'] = drain_card_elec

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
    drainage_coverage = Rapid_Slum_Appraisal.objects.filter(slum_name__name = slum_name)
    for k,v in CARDS.items():
        data_cards = {}
	try:
         if k == 'Drainage':
             data_cards[k] = [drainage_coverage.values_list(i.keys()[0], flat=True)[0] for i in v]
             data_cards = convert_float_to_str(data_cards)
             all_cards.update(data_cards)
         else:
             data_cards[k] = [root_query.values_list(i.keys()[0], flat=True)[0] for i in v]
             data_cards = convert_float_to_str(data_cards)
             all_cards.update(data_cards)
	except:
		pass
    return all_cards

def convert_float_to_str(data_dict):

    roundoff_str = {}

    def to_str_per(i):
        r = round(float(i), 2) if i != None else 0
        roundoff_str[k].append(str(r) + '%')
        return roundoff_str

    def to_str(i):
        r = round(float(i), 2) if i != None else 0
        roundoff_str[k].append(str(r))
        return roundoff_str

    for k,v in data_dict.items():
        roundoff_str[k] = []
        if k in ['Waste','Water','Drainage']:
            for i in v:
                if i != None:
                    roundoff_str.update(to_str_per(i))
        elif k == 'Toilet':
            for i in v:
                if i != None and v.index(i) == 0:
                    r = int(i) if i != None else 0
                    roundoff_str[k].append('1:'+ str(r))
                elif i != None and v.index(i) == 1:
                    r = int(i) if i != None else 0
                    roundoff_str[k].append(str(r)+':100')
                else:
                    if i != None and v.index(i) in [2,3]:
                        roundoff_str.update(to_str_per(i))
        elif k == 'Road':
            for i in v:
                if v.index(i) in [1,2]:
                    roundoff_str.update(to_str_per(i))
                else:
                    roundoff_str.update(to_str(i))
        elif k == 'General':
            for i in v:
                if i !=None and v.index(i) == 2:
                    roundoff_str.update(to_str_per(i))
                else:
                    roundoff_str.update(to_str(i))
        else :
            roundoff_str.update(to_str(i))

    return roundoff_str

def drainage_coverage(ele):
    new_list =[]
    for k,v in CARDS.items():
        if k == 'Drainage':
            for i in v:
                avrg = ele.values_list(i.keys()[0],flat=True)
    for i in avrg:
        try:
            i = int(i) if i != None else 0
            new_list.append(i)
        except:
            pass
    drain = (sum(new_list)/len(new_list) if len(new_list)!=0 else 0)
    drain_coverage = [str(round(float(drain), 2)) + '%']
    return drain_coverage

def score_cards(ele):
    all_cards ={}
    for k,v in CARDS.items():
        cards = {}
        if k =='Road':
            cards[k] = []
            for i in v: # list of dict
                if i.keys()[0] == 'road_with_no_vehicle_access':
                    avrg = ele.aggregate(Sum(i.keys()[0])).values()[0]
                    cards[k].append(avrg)
                else:
                    avrg = ele.aggregate(Avg(i.keys()[0])).values()[0]
                    cards[k].append(avrg)
        elif k =='Drainage':
            pass
        else :
            avrg = [ele.aggregate(Avg(i.keys()[0])).values()[0] for i in v]
            cards[k] = avrg
        str = convert_float_to_str(cards) # convert values in "40.0%" format
        all_cards.update(str)
    return all_cards

def dashboard_all_cards(request,key):

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
