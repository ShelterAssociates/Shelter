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
    def findgcd(a, b):
        if (b == 0):
            return a
        else:
            return findgcd(b, a % b)
    gcd = findgcd(m,wm)
    a = m/gcd if gcd!=0 else 0
    b= wm/gcd if gcd!=0 else 0
    ratio =(str(a)+":"+str(b))
    return ratio

def score_cards(ele):
    """To calculate aggregate level data for electoral, admin and city"""
    all_cards ={}
    #data required for cal
    occupide_household_count = ele.aggregate(Sum('occupied_household_count')).values()[0]
    total_household_count = ele.aggregate(Sum('household_count')).values()[0]
    #road data
    total_road_area = ele.aggregate(Sum('total_road_area')).values()[0]
    road_with_no_vehicle_access = ele.aggregate(Sum('road_with_no_vehicle_access')).values()[0]
    pucca_road_coverage = ele.aggregate(Sum('pucca_road_coverage')).values()[0]
    kutcha_road_coverage = ele.aggregate(Sum('kutcha_road_coverage')).values()[0]
    #general data
    gen_avg_household_size = ele.aggregate(Avg('gen_avg_household_size')).values()[0]
    gen_tenement_density = ele.aggregate(Sum('gen_tenement_density')).values()[0]
    household_owners_count = ele.aggregate(Sum('household_owners_count')).values()[0]
    #waste data
    waste_no_garbage_bin_percentile = ele.aggregate(Sum('waste_no_collection_facility_percentile')).values()[0]
    waste_door_to_door_collection_facility_percentile = ele.aggregate(Sum('waste_door_to_door_collection_facility_percentile')).values()[0]
    waste_dump_in_open_percent = ele.aggregate(Sum('waste_dump_in_open_percent')).values()[0]
    #water data
    water_individual_connection_percentile = ele.aggregate(Sum('water_individual_connection_percentile')).values()[0]
    water_shared_service_percentile = ele.aggregate(Sum('water_shared_service_percentile')).values()[0]
    waterstandpost_percentile = ele.aggregate(Sum('waterstandpost_percentile')).values()[0]
    #toilet data
    toilet_seat_to_person_ratio = ele.aggregate(Sum('toilet_seat_to_person_ratio')).values()[0]
    individual_toilet_coverage = ele.aggregate(Sum('individual_toilet_coverage')).values()[0]
    ctb_coverage = ele.aggregate(Sum('ctb_coverage')).values()[0]
    fun_male_seats = ele.aggregate(Sum('fun_male_seats')).values()[0]
    fun_fmale_seats = ele.aggregate(Sum('fun_fmale_seats')).values()[0]

    #drainage_card data
    slum_ids = ele.values_list('slum_id',flat=True)
    total_drain_count = 0
    for i in slum_ids:
        try:
            data = Rapid_Slum_Appraisal.objects.get(slum_name_id=i)
            drain_card = data.drainage_coverage if data else 0
            total_drain_count += drain_card if drain_card != None else 0
        except Exception as e:
            print e

    for k,v in CARDS.items():
        cards = {}
        cards[k] = []
        if k =='Drainage':
            drain_coverage = str(round(total_drain_count / total_household_count if total_household_count != 0 else 0, 2)) + ' %'
            cards[k]= [drain_coverage]
            all_cards.update(cards)
        elif k =='Road':
            cards[k].append(str(int(road_with_no_vehicle_access)))
            cards[k].append(str(round((pucca_road_coverage/total_road_area)*100 if total_road_area!=0 else 0,2))+' %')
            cards[k].append(str(round((kutcha_road_coverage/total_road_area)*100 if total_road_area!=0 else 0,2))+' %')
            all_cards.update(cards)
        elif k == 'Toilet':
            cards[k].append("1:"+ str(int((occupide_household_count*4)/toilet_seat_to_person_ratio if toilet_seat_to_person_ratio!=0 else 0)))
            men_wmn_seats_ratio = get_ratio(fun_male_seats, fun_fmale_seats)
            cards[k].append(men_wmn_seats_ratio)
            cards[k].append(str(round((individual_toilet_coverage/occupide_household_count)*100 if occupide_household_count!=0 else 0,2))+" %")
            cards[k].append(str(round((ctb_coverage/occupide_household_count)*100 if occupide_household_count!=0 else 0,2))+" %")
            all_cards.update(cards)
        elif k == 'General':
            cards[k].append(str(round(gen_avg_household_size,2)))
            cards[k].append(str(int(total_household_count / gen_tenement_density if gen_tenement_density != 0 else 0)))
            cards[k].append(str(round((household_owners_count / occupide_household_count) * 100 if occupide_household_count != 0 else 0,2))+" %")
            all_cards.update(cards)
        elif k =='Water':
            cards[k].append(str(round((water_individual_connection_percentile / occupide_household_count) * 100 if occupide_household_count != 0 else 0,2))+" %")
            cards[k].append(str(round((water_shared_service_percentile / occupide_household_count) * 100 if occupide_household_count != 0 else 0,2))+" %")
            cards[k].append(str(round((waterstandpost_percentile / occupide_household_count) * 100 if occupide_household_count != 0 else 0,2))+" %")
            all_cards.update(cards)
        else:
            cards[k].append(str(round((waste_no_garbage_bin_percentile / occupide_household_count) * 100 if occupide_household_count != 0 else 0, 2)) + " %")
            cards[k].append(str(round((waste_door_to_door_collection_facility_percentile / occupide_household_count) * 100 if occupide_household_count != 0 else 0, 2)) + " %")
            cards[k].append(str(round((waste_dump_in_open_percent / occupide_household_count) * 100 if occupide_household_count != 0 else 0, 2)) + " %")
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
