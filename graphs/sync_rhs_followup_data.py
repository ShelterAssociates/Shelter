from master.models import *
from graphs.models import *
import datetime
from django.utils import timezone
import pytz
from urllib import request as urllib2
import json
from django.conf import settings
from itertools import chain
from itertools import groupby
from django.utils.dateparse import parse_datetime
from component.kobotoolbox import parse_RIM_answer_with_toilet
import pdb
import re
import pytz

def convert_datetime(date_str):
	ret = parse_datetime(date_str)#pytz.utc.localize(parse_datetime(date_str))
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
						print(e)
						print(num)
						print(key)
						print(string.index(num))
				x[key_f] = ", ".join(string)

	return rhs_data

	
def fetch_data(form_code, latest_date):
	rhs_url = str(settings.KOBOCAT_FORM_URL)+'data/' + str(form_code) + '?format=json'
	if latest_date != '':
		rhs_url += '&query={"end":{"$gt":"'+urllib2.quote(str(timezone.localtime(latest_date)))+'"}}'
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
			# if latest_date != '':
			# 	url = url + '&query={"_submission_time":{"$gt":"'+urllib2.quote(str(timezone.localtime(latest_date)))+'"}}'
			url+='&start='+str(start)
			kobotoolbox_request = urllib2.Request(url)
			kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
			kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
			print("here aboves")
			res = urllib2.urlopen(kobotoolbox_request)
			html = res.read()
			records.extend(json.loads(html))
			print(url)
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

			url = settings.KOBOCAT_FORM_URL +'data/' + kobo_survey + '?format=json&query={"end":{"$gt":"'+urllib2.quote(str(timezone.localtime(latest_date)))+'"}}'
			#url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?format=json&query={"end":{"$gt":"' + urllib2.quote(str(timezone.localtime(latest_date))) + '"}}'
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
			print (url)
			print ("Total count "+ str(len(submission)))
			for record in submission:
				if 'group_zl6oo94/group_uj8eg07/slum_name' in record:
					key = record['group_zl6oo94/group_uj8eg07/slum_name']
					try:

						slum = Slum.objects.get(shelter_slum_code=key)

						output = parse_RIM_answer_with_toilet([record], form_data)
						data = {
									'slum' : slum,
									'city' : city,
									'submission_date' : convert_datetime(str(record['end'])),
									'rim_data' : output,
								}
						slum_data, created= SlumData.objects.update_or_create(slum=slum, defaults=data)
						slum_data.modified_on = timezone.now()
						if created:
							slum_data.created_on = timezone.now()
						slum_data.save()
					except Exception as e:
						print ("RIM ERROR:: Slum name not found - " +str(key))
				else:
					print ("RIM ERROR:: Slum name missing for "+ str(record["_id"]))

def syn_rhs_followup_data(city_id, ff_flag=False, latest_flag=True):
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
			
			latest_rhs = HouseholdData.objects.filter(city__id = city.id).order_by('-submission_date')
			if len(latest_rhs) != 0 and latest_flag:
				latest_rhs_date = latest_rhs[0].submission_date 

			latest_followup = FollowupData.objects.filter(city__id = city.id).order_by('-submission_date')
			if len(latest_followup) != 0 and latest_flag:
				latest_followup_date = latest_followup[0].submission_date

			latest_date = latest_followup_date if latest_followup_date > latest_rhs_date else latest_rhs_date
			print(latest_date)
			if ff_flag:
				sync_ff_data(city.id, latest_date)

			if True:#city.id == 1: #3,4 done
				#print timezone.localtime(latest_date)
				# url = build_url()
				rhs_data = fetch_data(form_code, latest_date)
				data_with_lables = fetch_labels_codes(rhs_data, form_code)
				total_records +=(len(data_with_lables))
				print('len of data_with_lables before = ' + str(len(data_with_lables)))
				data_with_lables = [x for x in data_with_lables if 'slum_name' in x.keys()]
				data_with_lables = [x for x in data_with_lables if 'Type_of_structure_occupancy' in x.keys()]
				data_with_lables = sorted(data_with_lables, key = lambda x:x['slum_name'])
				print('len of data_with_lables after = ' + str(len(data_with_lables)))

				print("Unoccupied Houses and locked Houses")
				for key,list_records in groupby(data_with_lables, lambda x:x['slum_name']):
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						#print key 
						slum = Slum.objects.get(shelter_slum_code = 272537891001)
					for record in list_records:
						if 'group_oi8ts04/C1' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C1']})
						if 'group_oi8ts04/C2' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C2']})
						if 'group_oi8ts04/C3' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C3']})
						if 'group_oi8ts04/C4' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C4']})
						if 'group_oi8ts04/C5' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C5']})
						if record['Type_of_structure_occupancy'] in ['Unoccupied house', 'Locked house']:
							if record['Type_of_structure_occupancy'] == 'Unoccupied house':
								count_u.append(record['Household_number'])
								a.append(record['Household_number'])
							if record['Type_of_structure_occupancy'] == 'Locked house':
								count_l.append(record['Household_number'])
								a.append(record['Household_number'])
							try:
								household_data = HouseholdData(

								household_number = str(int(record['Household_number'])),
								slum = slum,
								city = city,
								submission_date = convert_datetime(str(record['end'])) ,
								rhs_data = record
								)
								household_data.save()
								rhs_and_followup_updated +=1
							except Exception as e:
								pass 

				print("Occupied Houses")
				for key,list_records in groupby(data_with_lables, lambda x:x['slum_name']):

					temp_locked_houses_replaced = []
					temp_double_houses = []
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						#print key 
						slum = Slum.objects.get(shelter_slum_code = 272537891001)
					list_records = list(list_records)
					#print(str(len(list_records)))
					for index,  record in enumerate(list_records):
						if 'group_oi8ts04/C1' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C1']})
						if 'group_oi8ts04/C2' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C2']})
						if 'group_oi8ts04/C3' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C3']})
						if 'group_oi8ts04/C4' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C4']})
						if 'group_oi8ts04/C5' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C5']})
					 	if record['Type_of_structure_occupancy'] == 'Occupied house':
							if 'group_og5bx85/Type_of_survey' in record and record['group_og5bx85/Type_of_survey'] == 'RHS':
								f_data = {}
								r_data = {}
								
								for i in record.iteritems():	
									if 'group_oi8ts04' in i[0]:
										f_data.update({i[0]:i[1]})
									else:
										r_data.update({i[0]:i[1]})
								f_data.update({"_submission_time":record["end"], "_id":record["_id"]})
								rhs_flag = False
								try:
									try:
										hh_data = HouseholdData.objects.filter(kobo_id = record['_id'])
										if hh_data.count() > 0 and hh_data.filter(slum=slum, household_number=str(int(record['Household_number']))).count()==0:
											hh_data.update(rhs_data=None)
											for hh_d in hh_data:
												if hh_d.ff_data == None:
													hh_d.delete()
										household_data = HouseholdData.objects.filter(slum=slum, city=city, household_number = str(int(record['Household_number'])))
										if household_data.count() > 0:
											if household_data[0].submission_date < convert_datetime(str(record['end'])):
												HouseholdData.objects.filter(id=household_data[0].id).update(rhs_data = record, submission_date = convert_datetime(str(record['end'])))
										else:
											household_data = HouseholdData(
												household_number=str(int(record['Household_number'])),
												kobo_id= record['_id'],
												slum=slum,
												city=city,
												submission_date=convert_datetime(str(record['end'])),
												rhs_data=record
											)
											household_data.save()
											rhs_and_followup_updated += 1
									except:
										pass

									followup_Data = FollowupData.objects.filter(household_number = str(int(record['Household_number'])),
										slum = slum,
										city = city,flag_followup_in_rhs = True)
									if followup_Data.count() > 0:
										followup_Data.update(submission_date = convert_datetime(str(record['end'])) ,
											followup_data = f_data, kobo_id=f_data["_id"])
									else:
										followup_data = FollowupData(
											kobo_id=f_data["_id"],
											household_number = str(int(record['Household_number'])),
											slum = slum,
											city = city,
											submission_date = convert_datetime(str(record['end'])) ,
											followup_data = f_data,
											flag_followup_in_rhs = True
										)
										followup_data.save()
									#print record['group_og5bx85/Type_of_survey']
								except Exception as e:
									# print "error in followup rhs"
									print(e)
					
					replaced_locked_houses.update({slum:temp_locked_houses_replaced})
					double_houses.update({slum:temp_double_houses})

				print("Followup houses")
				for key,list_records in groupby(data_with_lables, lambda x:x['slum_name']):
					try:
						slum = Slum.objects.get(shelter_slum_code = key)
					except:
						#print key 
						slum = Slum.objects.get(shelter_slum_code = 272537891001)
					for record in list_records:
						if 'group_oi8ts04/C1' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C1']})
						if 'group_oi8ts04/C2' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C2']})
						if 'group_oi8ts04/C3' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C3']})
						if 'group_oi8ts04/C4' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C4']})
						if 'group_oi8ts04/C5' in record.keys():
							record.update({'group_oi8ts04/Current_place_of_defecation': record['group_oi8ts04/C5']})

						if record['Type_of_structure_occupancy'] == 'Occupied house':
							if 'group_og5bx85/Type_of_survey' in record and record['group_og5bx85/Type_of_survey'] == 'Follow-up survey':
								count_o.append(record['Household_number'])
								a.append(record['Household_number'])
								f_data = {}
								for i in record.iteritems():	
									if 'group_oi8ts04' in i[0]:
										f_data.update({i[0]:i[1]})
									
								f_data.update({"_submission_time":record["end"], "_id":record["_id"]})
								try:
									#print "adding followup"
									flag = True if len(HouseholdData.objects.filter(household_number = record['Household_number'], slum = slum)) > 0 else False
									try:
										followup = FollowupData.objects.filter(kobo_id=f_data["_id"] )
										if followup.count()>0:
											followup.update(slum=slum, city=city, household_number=str(int(record['Household_number'])),
															followup_data=f_data)
										else:
											followup_data = FollowupData(
												household_number = str(int(record['Household_number'])),
												slum = slum,
												city = city,
												submission_date = convert_datetime(str(record['end'])) ,
												followup_data = f_data,
												kobo_id = f_data["_id"],
												flag_followup_in_rhs = False
											)
											followup_data.save()
									except:
										pass
									only_followup +=1
								except Exception as e:
									print(e)
		
def sync_ff_data(city_id, latest_date=''):
	cities = City.objects.filter(id__in=[city_id])
	for city in cities:
		survey_forms_ff = Survey.objects.filter(city__id = int(city.id), description__contains = 'FF')
		for i in survey_forms_ff:
			form_code = i.kobotool_survey_id
			ff_data = fetch_data(form_code, latest_date)
			ff_data_with_labels = fetch_labels_codes(ff_data, form_code)

			ff_data_with_labels = [x for x in ff_data_with_labels if 'group_vq77l17/slum_name' in x.keys()]

			ff_data_with_labels = sorted(ff_data_with_labels, key = lambda x:x['group_vq77l17/slum_name']) #group_vq77l17/slum_name

			for key,list_records in groupby(ff_data_with_labels, lambda x:x['group_vq77l17/slum_name']):
				slum = None
				try:
					slum = Slum.objects.get(shelter_slum_code = key)
				except:
					print (key," - slum not found")
				if slum:
					list_records = list(list_records)
					print(key, ' - ', str(len(list_records)))
					for record in list_records:
						try:
							if 'group_im2th52/Approximate_monthly_family_income_in_Rs' in record:
								record['group_im2th52/Approximate_monthly_family_income_in_Rs'] = int('0'+''.join(re.findall('[\d+]',re.sub('(\.[0]*)','',record['group_im2th52/Approximate_monthly_family_income_in_Rs']))))
							if 'group_ne3ao98/Cost_of_upgradation_in_Rs' in record:
								record['group_ne3ao98/Cost_of_upgradation_in_Rs'] = int('0'+''.join(re.findall('[\d+]',re.sub('(\.[0]*)','',record['group_ne3ao98/Cost_of_upgradation_in_Rs']))))
							hh_data = HouseholdData.objects.filter(ff_kobo_id= record["_id"])
							if hh_data.count() >0 and hh_data.filter(household_number=str(int(record['group_vq77l17/Household_number'])), slum=slum).count()==0:
								hh_data.update(ff_data=None)
								for hh in hh_data:
									if not hh.rhs_data:
										hh.delete()
							
							temp = HouseholdData.objects.filter(household_number = str(int(record['group_vq77l17/Household_number'])), slum = slum)
							if temp.count()>0:
								temp.update(ff_data = record, ff_kobo_id=record['_id'])
							else:
								household_data = HouseholdData(household_number = str(int(record['group_vq77l17/Household_number'])), slum = slum,
															   ff_data=record, ff_kobo_id=record['_id'], city=city, submission_date=convert_datetime(str(record['end'])))
								household_data.save()
						except Exception as e:
							#print no_rhs_but_ff.append(record['group_vq77l17/Household_number'] + " in" + str(slum) + " has a factesheet but no rhs/followup record")
							print(e)
			

	# print "unoccupied =" + str(count_u) + str(len(count_u))
			# print "locked = " + str(count_l) + str(len(count_l))
			# print "Occupied = " + str(count_o) + str(len(count_o))
			# print "All = " + str(a)	
			# print "Only RHS updated = " + str(rhs_and_followup_updated)
			# print "Only Follow-up updated = " + str(only_followup_updated)
			# print "replaced_locked_houses : " + str(replaced_locked_houses)
			# print "double_houses : " + str(double_houses)
							
				
				
#syn_rhs_followup_data()

#syn_rim_data()

