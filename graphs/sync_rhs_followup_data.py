from master.models import *
from graphs.models import *
import datetime
from django.utils import timezone
import pytz
import urllib2
import json
from django.conf import settings
from itertools import chain
from itertools import groupby
from django.utils.dateparse import parse_datetime




def convert_datetime(date_str):
	ret = parse_datetime(date_str)
	return ret


def trav(node):
    #Traverse up till the child node and add to list
    if 'type' in node and node['type'] == "group":
        return list(chain.from_iterable([trav(child) for child in node['children']]))
    elif (node['type'] == "select one" or node['type'] == "select all that apply") and 'children' in node.keys():
        return [node]
    return []
    
    
def fetch_labels_codes(rhs_data, form_code):
	name_label_data = []
	url_rhs_form = str(settings.KOBOCAT_FORM_URL)+'forms/'+str(form_code)+'/form.json'
	
	kobotoolbox_request_RHS_form = urllib2.Request(url_rhs_form)
	kobotoolbox_request_RHS_form.add_header('Authorization', settings.KOBOCAT_TOKEN)
	res_RHS_form = urllib2.urlopen(kobotoolbox_request_RHS_form)
	html_RHS_form = res_RHS_form.read()
	formdict_RHS_form = json.loads(html_RHS_form)
	for i in formdict_RHS_form['children']:
		temp_data = trav(i)  # trav() function traverses the dictionary to find last hanging child
		name_label_data.extend(temp_data)
	
	name_label_data_dict = {
 			obj_name_label_data['name']: {child['name']: child['label'] for child in obj_name_label_data['children']} for
			obj_name_label_data in name_label_data}
	for x in rhs_data:
		for key_f,value_f in x.items():
			key = key_f.split("/")[-1]
			if key in name_label_data_dict.keys():
				string = value_f.split(" ")
				for num in string:
					string[string.index(num)] = name_label_data_dict[key][num]
				x[key_f] = ", ".join(string)

	return rhs_data

def build_url(form_code, latest_date):
	rhs_url = str(settings.KOBOCAT_FORM_URL)+'data/' + str(form_code) + '?format=json'
	rhs_url += '&query={"_submission_time":{"$gt":"'+str(timezone.localtime(latest_date))+'"}}' #"slum_name":"272537892104", udyog nagar dalvi nagar pcmc "slum_name":"272537891802",
	#"slum_name":"272537891802",
	return rhs_url
	
def fetch_data(url):
	print(url)
        kobotoolbox_request = urllib2.Request(url)
        kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
        kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)

        res = urllib2.urlopen(kobotoolbox_request)
        # Read json data from kobotoolbox API
        html = res.read()
        records = json.loads(html)
        return records

def syn_rhs_followup_data():
	count_o = []
	count_u = []
	count_l = []
	a = []
	replaced_locked_houses = {}
	double_houses = {}
	only_followup_updated = 0
	rhs_and_followup_updated = 0
	total_records = 0
	cities = City.objects.all()
	for city in cities:
		survey_forms = Survey.objects.filter(city__id = int(city.id), description__contains = 'RHS')
		for i in survey_forms:
			latest_rhs_date = datetime.datetime(2000, 1, 1,0,0,0,0, pytz.UTC)
			latest_followup_date = datetime.datetime(2000, 1, 1,0,0,0,0, pytz.UTC)

			form_code = i.kobotool_survey_id
			
			latest_rhs = HouseholdData.objects.filter(slum__electoral_ward__administrative_ward__city = i.city).order_by('-submission_date')
			if len(latest_rhs) != 0:
				latest_rhs_date = latest_rhs[0].submission_date 

			latest_followup = FollowupData.objects.filter(slum__electoral_ward__administrative_ward__city = i.city).order_by('-submission_date')
			if len(latest_followup) != 0:
				latest_followup_date = latest_followup[0].submission_date

			latest_date = latest_followup_date if latest_followup_date > latest_rhs_date else latest_rhs_date
			if city.id == 3:
				print timezone.localtime(latest_date)
				url = build_url(form_code, latest_date)
				rhs_data = fetch_data(url)
				data_with_lables = fetch_labels_codes(rhs_data, form_code)
				total_records +=(len(data_with_lables))
				sorted(data_with_lables, key = lambda x:x['slum_name'])

				for key,list_records in groupby(data_with_lables, lambda x:x['slum_name']):
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						print key 
						slum = Slum.objects.get(shelter_slum_code = 272537891001)
					for record in list_records:
						#print record['Type_of_structure_occupancy'], record['_submission_time'], record['group_og5bx85/Type_of_survey']
						if record['Type_of_structure_occupancy'] in ['Unoccupied house', 'Locked house']:
							if record['Type_of_structure_occupancy'] == 'Unoccupied house':
								count_u.append(record['Household_number'])
								a.append(record['Household_number'])
							if record['Type_of_structure_occupancy'] == 'Locked house':
								count_l.append(record['Household_number'])
								a.append(record['Household_number'])
							print '******************************'
							print record['Type_of_structure_occupancy']	, record['Household_number']
							try:
								household_data = HouseholdData(

								household_number = record['Household_number'],
								slum = slum,
								city = city,
								submission_date = convert_datetime(str(record['_submission_time'])) ,
								rhs_data = record
								)
								household_data.save()
								rhs_and_followup_updated +=1
							except Exception as e:
								print e # 

				for key,list_records in groupby(data_with_lables, lambda x:x['slum_name']):
					temp_locked_houses_replaced = []
					temp_double_houses = []
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						print key 
						slum = Slum.objects.get(shelter_slum_code = 272537891001)
					for record in list_records:
					 	if record['Type_of_structure_occupancy'] == 'Occupied house':
							if record['group_og5bx85/Type_of_survey'] == 'RHS':
								f_data = {}
								r_data = {}
								try:
									temp_hh = HouseholdData.objects.get(household_number = record['Household_number'], slum = slum)
									if str(temp_hh.rhs_data['Type_of_structure_occupancy']) == 'Locked house':
										temp.temp_locked_houses_replaced.append(temp_hh.household_number)
										temp_hh.delete()

									if str(temp_hh.rhs_data['Type_of_structure_occupancy']) == 'Occupied house':
										if temp_hh.submission_date < convert_datetime(str(record['_submission_time'])):
											temp_double_houses.append(temp_hh.household_number)
											temp_hh.delete()

								except Exception as e:
									print "temp_hh error"
									print e

								count_o.append(record['Household_number'])
								a.append(record['Household_number'])
								
								for i in record.iteritems():	
									if 'group_oi8ts04' in i[0]:
										f_data.update({i[0]:i[1]})
									else:
										r_data.update({i[0]:i[1]})
								f_data.update({"_submission_time":record["_submission_time"], "_id":record["_id"]})
								try:
									household_data = HouseholdData(

									household_number = record['Household_number'],
									slum = slum,
									city = city,
									submission_date = convert_datetime(str(record['_submission_time'])) ,
									rhs_data = r_data
									)
									household_data.save()
									rhs_and_followup_updated +=1
								
									followup_data = FollowupData(

									household_number = record['Household_number'],
									slum = slum,
									city = city,
									submission_date = convert_datetime(str(record['_submission_time'])) ,
									followup_data = f_data,
									flag_followup_in_rhs = True
									)
									followup_data.save()
									print record['group_og5bx85/Type_of_survey']
								except Exception as e:
									# print "error in followup rhs"
									print e
					
					replaced_locked_houses.update({slum:temp_locked_houses_replaced})
					double_houses.update({slum:temp_double_houses})				
				for key,list_records in groupby(data_with_lables, lambda x:x['slum_name']):
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						print key 
						slum = Slum.objects.get(shelter_slum_code = 272537891001)
					for record in list_records:
						if record['Type_of_structure_occupancy'] == 'Occupied house':
							if record['group_og5bx85/Type_of_survey'] == 'Follow-up survey':
								count_o.append(record['Household_number'])
								a.append(record['Household_number'])
								f_data = {}
								for i in record.iteritems():	
									if 'group_oi8ts04' in i[0]:
										f_data.update({i[0]:i[1]})
									
								f_data.update({"_submission_time":record["_submission_time"], "_id":record["_id"]})
								try:
									print "adding folloup"
									flag = True if len(HouseholdData.objects.filter(household_number = record['Household_number'], slum = slum)) > 0 else False
									followup_data = FollowupData(

									household_number = record['Household_number'],
									slum = slum,
									city = city,
									submission_date = convert_datetime(str(record['_submission_time'])) ,
									followup_data = f_data,
									flag_followup_in_rhs = flag
									)
									followup_data.save()
									only_followup_updated +=1
								except Exception as e:
									print "error in followup"
									print e
									print record['Household_number']
			# print "unoccupied =" + str(count_u) + str(len(count_u))
			# print "locked = " + str(count_l) + str(len(count_l))
			# print "Occupied = " + str(count_o) + str(len(count_o))
			print "All = " + str(a)	
			print "Only RHS updated = " + str(rhs_and_followup_updated)
			print "Only Follow-up updated = " + str(only_followup_updated)
			print "total records = " + str(total_records) 
			print "replaced_locked_houses : " + str(replaced_locked_houses)
			print "double_houses : " + str(double_houses)
							
				
				
syn_rhs_followup_data()

