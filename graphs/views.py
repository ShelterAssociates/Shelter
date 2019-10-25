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
from fractions import Fraction

CARDS = {'General':[{'gen_avg_household_size':"Avg Household size"}, {'gen_tenement_density':"Tenement density (Huts/Hector)"},
                    {'household_owners_count':'Superstructure Ownership'}],
         'Waste': [{'waste_no_collection_facility_percentile':'Garbage Bin'},
                   {'waste_door_to_door_collection_facility_percentile':'Door to door waste collection'},
                   {'waste_dump_in_open_percent':'Dump in open'}],
         'Water': [{'water_individual_connection_percentile':'Individual water connection'},
                   {'water_shared_service_percentile':'Shared Water Connection'},{'waterstandpost_percentile':'Water Standposts'}],
         'Toilet': [{'toilet_seat_to_person_ratio':'Toilet seat to person ratio'},
                    {'toilet_men_women_seats_ratio':'Men to women toilet seats'},
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

    #Administrative ward calculations
    for admin_ward in AdministrativeWard.objects.filter(city=city):
        output_data['administrative_ward'][admin_ward.name] = {'scores': {}, 'cards':{}}
        qol_scores = QOLScoreData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        for clause in select_clause:
            output_data['administrative_ward'][admin_ward.name]['scores'][clause] = qol_scores.aggregate(Avg(clause))[clause + '__avg']
        admin_wards = DashboardData.objects.filter(slum__electoral_ward__administrative_ward=admin_ward)
        cards = score_cards(admin_wards)
        output_data['administrative_ward'][admin_ward.name]['cards'] = cards

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
    qol_scores = {key: {'scores': list(values)[0],'cards': score_cards(DashboardData.objects.filter(slum__name=key))} for key, values in qol_scores}
    output_data['slum'] = qol_scores
    output_data['metadata'] = CARDS
    return HttpResponse(json.dumps(output_data),content_type='application/json')

def get_ratio(m,wm):
    #a = m/wm if wm and m else 0
    #ratio = str(Fraction(a).limit_denominator()).replace('/',':')
    ratio = str(m) + ":"+ str(wm)
    return ratio

def score_cards(ele):
    """To calculate aggregate level data for electoral, admin and city"""
    all_cards ={}
    aggrgated_data = ele.aggregate(Sum('occupied_household_count'),Sum('household_count'),
        Sum('total_road_area'),Sum('road_with_no_vehicle_access'),Sum('pucca_road_coverage'),Sum('kutcha_road_coverage'),
        Sum('gen_avg_household_size'),Sum('gen_tenement_density'),Sum('household_owners_count'),
        Sum('waste_no_collection_facility_percentile'),Sum('waste_door_to_door_collection_facility_percentile'),Sum('waste_dump_in_open_percent'),
        Sum('water_individual_connection_percentile'),Sum('water_shared_service_percentile'),Sum('waterstandpost_percentile'),
        Sum('toilet_seat_to_person_ratio'),Sum('individual_toilet_coverage'),Sum('fun_male_seats'),Sum('fun_fmale_seats'),Sum('ctb_coverage'))

    #drainage_card data
    slum_ids = ele.values_list('slum__id',flat=True)
    total_drain_count = 0
    data = Rapid_Slum_Appraisal.objects.filter(slum_name__id__in = slum_ids).aggregate(Sum('drainage_coverage'))
    total_drain_count += data['drainage_coverage__sum'] if data['drainage_coverage__sum'] !=None else 0

    for k,v in CARDS.items():
        cards = {}
        cards[k] = []
        if k =='Drainage':
            drain_coverage = str(round((total_drain_count / aggrgated_data['household_count__sum'])*100 if aggrgated_data['household_count__sum'] else 0, 2)) + ' %'
            cards[k]= [drain_coverage]
            all_cards.update(cards)
        elif k =='Road':
            cards[k].append(str(int(aggrgated_data['road_with_no_vehicle_access__sum'] if aggrgated_data['road_with_no_vehicle_access__sum'] else 0 )))
            cards[k].append(str(round((aggrgated_data['pucca_road_coverage__sum']/aggrgated_data['total_road_area__sum'])*100 if aggrgated_data['total_road_area__sum'] else 0,2))+' %')
            cards[k].append(str(round((aggrgated_data['kutcha_road_coverage__sum']/aggrgated_data['total_road_area__sum'])*100 if aggrgated_data['total_road_area__sum'] else 0,2))+' %')
            all_cards.update(cards)
        elif k == 'Toilet':
            cards[k].append("1:"+ str(int((aggrgated_data['occupied_household_count__sum']*4)/aggrgated_data['toilet_seat_to_person_ratio__sum']\
                                              if aggrgated_data['toilet_seat_to_person_ratio__sum'] else 0)))
            men_wmn_seats_ratio = get_ratio(aggrgated_data['fun_male_seats__sum'],aggrgated_data['fun_fmale_seats__sum'])
            cards[k].append(men_wmn_seats_ratio)
            cards[k].append(str(round((aggrgated_data['individual_toilet_coverage__sum']/aggrgated_data['occupied_household_count__sum'])*100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
            cards[k].append(str(round((aggrgated_data['ctb_coverage__sum']/aggrgated_data['occupied_household_count__sum'])*100 if aggrgated_data['occupied_household_count__sum'] else 0,2))+" %")
            all_cards.update(cards)
        elif k == 'General':
            cards[k].append(str(round(aggrgated_data['gen_avg_household_size__sum']/aggrgated_data['occupied_household_count__sum']\
                                      if aggrgated_data['occupied_household_count__sum'] else 0,2)))
            cards[k].append(str(int(aggrgated_data['household_count__sum'] / aggrgated_data['gen_tenement_density__sum'] if aggrgated_data['gen_tenement_density__sum']  else 0)))
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
