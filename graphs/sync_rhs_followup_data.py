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
from component.kobotoolbox import parse_RIM_answer_with_toilet
import pdb
import re



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
					try:
						string[string.index(num)] = name_label_data_dict[key][num]
					except Exception as e:
						print e
						print num
						print key
						print string.index(num)
				x[key_f] = ", ".join(string)

	return rhs_data

	
def fetch_data(form_code, latest_date):
	rhs_url = str(settings.KOBOCAT_FORM_URL)+'data/' + str(form_code) + '?format=json'
	if latest_date != '':
		rhs_url += '&query={"_submission_time":{"$gt":"'+str(timezone.localtime(latest_date))+'"}}'
	find_count = rhs_url + '&count=1'
	count_url = urllib2.Request(find_count)
	count_url.add_header('User-agent', 'Mozilla 5.10')
	count_url.add_header('Authorization', settings.KOBOCAT_TOKEN)

	count_url_res = urllib2.urlopen(count_url)
	count_html = count_url_res.read()
	count_records =json.loads(count_html) 
	slots = count_records['count'] / 30000
	records = []
	if int(count_records['count']) > 0 :
		for x in range(slots+1):
			start = x*30000
			url = rhs_url
			if latest_date != '':
				url = url + '&query={"_submission_time":{"$gt":"'+str(timezone.localtime(latest_date))+'"}}'
			url+='&start='+str(start)
			kobotoolbox_request = urllib2.Request(url)
			kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
			kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
			print "here aboves"
			res = urllib2.urlopen(kobotoolbox_request)
			html = res.read()
			records.extend(json.loads(html))
			print url
	return records

def syn_rim_data(city_id):
	cities = City.objects.filter(id__in=[city_id])
	for city in cities:
		survey = Survey.objects.filter(city__id = int(city.id), description__contains = 'RIM')
		if survey:
			kobo_survey = survey[0].kobotool_survey_id

			latest_rim = SlumData.objects.filter(city=city).order_by('-submission_date').first()

			latest_date = datetime.datetime(2000, 1, 1,0,0,0,0, pytz.UTC)
			if latest_rim:
				latest_date = latest_rim.submission_date

			url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?format=json&query={"_submission_time":{"$gt":"'+str(timezone.localtime(latest_date))+'"}}'
			req = urllib2.Request(url)
			req.add_header('Authorization', settings.KOBOCAT_TOKEN)
			resp = urllib2.urlopen(req)
			content = resp.read()
			submission = json.loads(content)

			url1 = settings.KOBOCAT_FORM_URL + 'forms/' + kobo_survey + '/form.json'
			req1 = urllib2.Request(url1)
			req1.add_header('Authorization', settings.KOBOCAT_TOKEN)
			resp1 = urllib2.urlopen(req1)
			content1 = resp1.read()
			form_data = json.loads(content1)
		# To maintain the order in which questions are displayed we iterate through the form data
		if len(submission) > 0:
			for record in submission:
				key = record['group_zl6oo94/group_uj8eg07/slum_name']
				print key
				try:

					slum = Slum.objects.get(shelter_slum_code=key)

					output = parse_RIM_answer_with_toilet([record], form_data)
					data = {
								'slum' : slum,
								'city' : city,
								'submission_date' : convert_datetime(str(record['_submission_time'])),
								'rim_data' : output,
							}
					slum_data, created= SlumData.objects.update_or_create(slum=slum, defaults=data)
					slum_data.modified_on = datetime.datetime.now()
					if created:
						slum_data.created_on = datetime.datetime.now()
					slum_data.save()
				except Exception as e:
					pass

def syn_rhs_followup_data(city_id):
	count_o = []
	count_u = []
	count_l = []
	a = []
	no_rhs_but_ff = []
	replaced_locked_houses = {}
	double_houses = {}
	only_followup = 0
	rhs_and_followup_updated = 0
	total_records = 0
	cities = City.objects.filter(id__in=[city_id])
	is_initial = True

	for city in cities:
		# if city.id == 6:
		# 	Type_of_structure_occupancy = 'group_ce0hf58/Type_of_structure_occupancy'
		# 	Household_number = 'group_ce0hf58/house_no'
		# 	slum_name = 'group_ce0hf58/slum_name'

		survey_forms_rhs = Survey.objects.filter(city__id = int(city.id), description__contains = 'RHS')
		for i in survey_forms_rhs:
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
			if True:#city.id == 1: #3,4 done
				#print timezone.localtime(latest_date)
				# url = build_url()
				rhs_data = fetch_data(form_code, latest_date)
				data_with_lables = fetch_labels_codes(rhs_data, form_code)
				total_records +=(len(data_with_lables))
				print 'len of data_with_lables before = ' + str(len(data_with_lables))
				data_with_lables = [x for x in data_with_lables if 'slum_name' in x.keys()]
				data_with_lables = [x for x in data_with_lables if 'Type_of_structure_occupancy' in x.keys()]
				data_with_lables = sorted(data_with_lables, key = lambda x:x['slum_name'])
				print 'len of data_with_lables after = ' + str(len(data_with_lables))


				for key,list_records in groupby(data_with_lables, lambda x:x['slum_name']):
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						#print key 
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
							#print '******************************'
							#print record['Type_of_structure_occupancy']	, record['Household_number']
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
						#print key 
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
									#print "temp_hh error"
									print e
									#.append(record['Household_number'])
								
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
									#print record['group_og5bx85/Type_of_survey']
								except Exception as e:
									# print "error in followup rhs"
									print e
					
					replaced_locked_houses.update({slum:temp_locked_houses_replaced})
					double_houses.update({slum:temp_double_houses})				
				for key,list_records in groupby(data_with_lables, lambda x:x['slum_name']):
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						#print key 
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
									#print "adding followup"
									flag = True if len(HouseholdData.objects.filter(household_number = record['Household_number'], slum = slum)) > 0 else False
									followup_data = FollowupData(

									household_number = record['Household_number'],
									slum = slum,
									city = city,
									submission_date = convert_datetime(str(record['_submission_time'])) ,
									followup_data = f_data,
									flag_followup_in_rhs = False
									)
									followup_data.save()
									only_followup +=1
									print flag
								except Exception as e:
									#print "error in followup"
									print e
									#print record['Household_number']
		

		survey_forms_ff = Survey.objects.filter(city__id = int(city.id), description__contains = 'FF')
		for i in survey_forms_ff:
			form_code = i.kobotool_survey_id
			ff_data = fetch_data(form_code, '')
			ff_data_with_labels = fetch_labels_codes(ff_data, form_code)
			if city.id ==1:
				ff_data_with_labels = [x for x in ff_data_with_labels if 'group_vq77l17/slum_name' in x.keys()]
				
				sorted(ff_data_with_labels, key = lambda x:x['group_vq77l17/slum_name']) #group_vq77l17/slum_name
				
				for key,list_records in groupby(ff_data_with_labels, lambda x:x['group_vq77l17/slum_name']):
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						# key 
						slum = Slum.objects.get(shelter_slum_code = 272537891001)
					for record in list_records:
						try:
							if 'group_im2th52/Approximate_monthly_family_income_in_Rs' in record:
								record['group_im2th52/Approximate_monthly_family_income_in_Rs'] = int('0'+''.join(re.findall('[\d+]',re.sub('(\.[0]*)','',record['group_im2th52/Approximate_monthly_family_income_in_Rs']))))
							if 'group_ne3ao98/Cost_of_upgradation_in_Rs' in record:
								record['group_ne3ao98/Cost_of_upgradation_in_Rs'] = int('0'+''.join(re.findall('[\d+]',re.sub('(\.[0]*)','',record['group_ne3ao98/Cost_of_upgradation_in_Rs']))))
							temp = HouseholdData.objects.get(household_number = record['group_vq77l17/Household_number'], slum = slum)
							temp.ff_data = record
							temp.save()
						except:
							#print no_rhs_but_ff.append(record['group_vq77l17/Household_number'] + " in" + str(slum) + " has a factesheet but no rhs/followup record") 
							print e
			

	# print "unoccupied =" + str(count_u) + str(len(count_u))
			# print "locked = " + str(count_l) + str(len(count_l))
			# print "Occupied = " + str(count_o) + str(len(count_o))
			# print "All = " + str(a)	
			# print "Only RHS updated = " + str(rhs_and_followup_updated)
			# print "Only Follow-up updated = " + str(only_followup_updated)
	print "no rhs but ff = " + str(only_followup) 
			# print "replaced_locked_houses : " + str(replaced_locked_houses)
			# print "double_houses : " + str(double_houses)
							
				
				
#syn_rhs_followup_data()

#syn_rim_data()

