#	Script written on Python 3.6
# 	Author : Parag Fulzele
#	Description : Methods to convert RHS survey into xml
#

import uuid
import traceback
import copy

from common import *

# dictionary use to set and export data into xml
gl_rhs_xml_dict = {
	'formhub' : {
		'uuid' : None
	},
	'start' : None,
	'end' : None,
	'group_ce0hf58' : {
		'city' : None,
		'admin_ward' : None,
		'slum_name' : None,
		'date_of_rhs' : None,
		'name_of_surveyor_who_collected_rhs_data' : None,
		'house_no' : None,
		'Type_of_structure_occupancy' : None
	},
	'group_ye18c77' : {
		'group_ud4em45' : {
			'what_is_the_full_name_of_the_family_head_' : None,
			'mobile_number' : None,
			'adhar_card_number' : None
		},
		'group_yw8pj39' : {
			'what_is_the_structure_of_the_house' : None,
			'what_is_the_ownership_status_of_the_house' : None,
			'number_of_family_members' : None,
			'Do_you_have_a_girl_child_under' : None,
			'if_yes_how_many_' : None,
			'house_area_in_sq_ft' : None,
			'Current_place_of_defecation_toilet' : None,
			'does_any_member_of_your_family_go_for_open_defecation_' : None,
			'where_the_individual_toilet_is_connected_to_' : None,
			'type_of_water_connection' : None,
			'facility_of_waste_collection' : None,
			'Are_you_interested_in_individu' : None,
			'if_yes_why_' : None,
			'if_no_why_' : None,
			'type_of_toilet_preference' : None,
			'Have_you_applied_for_indiviual' : None,
			'How_many_installements_have_yo' : None,
			'when_did_you_receive_the_first_installment_date' : None,
			'when_did_you_receive_the_second_installment_date' : None,
			'what_is_the_status_of_toilet_under_sbm_' : None,
			'Does_any_family_members_has_co' : None
		},
	},
	'__version__' : None,
	'meta' : {
		'instanceID' : None
	}
}

## RHS survey queries
# get list of all household in all slums for survey
qry_rhs_slum_household_survey_list = "select distinct household.slum_id, household.household_code from survey_fact f \
join slum_data_household household on household.id = f.object_id \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
where s.id = %s and p.id = %s and f.content_type_id = 27 \
order by household.slum_id, household.household_code asc"

# get list of all question and answer for all household in slum
qry_rhs_survey_slum_household_question_answer = "(select household1.household_code, '-1' as question_id, to_char(min(f1.updated_on),'YYYY-MM-DD\"T\"HH24:MI:SS.MS+05:30') as answer from survey_fact f1 \
join survey_survey s1 on s1.id = f1.survey_id join survey_project p1 on p1.id = s1.project_id \
join survey_surveydesiredfact sdf1 on f1.desired_fact_id = sdf1.desired_fact_id and s1.id = sdf1.survey_id \
join slum_data_household household1 on household1.id = f1.object_id \
where s1.id = %s and p1.id = %s and f1.content_type_id = 27 \
 and household1.slum_id= %s group by household1.household_code) \
UNION All \
(select household.household_code, f.desired_fact_id as question_id, f.data as answer from survey_fact f \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
join survey_surveydesiredfact sdf on f.desired_fact_id = sdf.desired_fact_id and s.id = sdf.survey_id \
join slum_data_household household on household.id = f.object_id \
where s.id = %s and p.id = %s and f.content_type_id = 27 and household.slum_id= %s order by household.household_code, sdf.weight asc)"

# since RHS has two survey and its been decided that data from new survey (in case if slum data is in both survey)
# get list of common slum to use data from new slum only
qry_rhs_common_slum_list = "(select distinct household.slum_id from survey_fact f \
join slum_data_household household on household.id = f.object_id \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
where s.id = %s and p.id = %s and f.content_type_id = 27 order by household.slum_id asc) \
INTERSECT ALL \
(select distinct household.slum_id from survey_fact f \
join slum_data_household household on household.id = f.object_id \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
where s.id = %s and p.id = %s and f.content_type_id = 27 \
order by household.slum_id asc)"

# get list of all household in all slums for second survey
qry_rhs_master_slum_household_survey_list = "select distinct household.slum_id, household.household_code from survey_fact f \
join slum_data_household household on household.id = f.object_id \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
where s.id = %s and p.id = %s and f.content_type_id = 27 \
order by household.slum_id, household.household_code asc"

# get list of all question and answer for all household in slum from second survey
qry_rhs_master_survey_slum_household_question_answer ="(select household1.household_code, '-1' as question_id, to_char(min(f1.updated_on),'YYYY-MM-DD\"T\"HH24:MI:SS.MS+05:30') as answer from survey_fact f1 \
join survey_survey s1 on s1.id = f1.survey_id join survey_project p1 on p1.id = s1.project_id \
join survey_surveydesiredfact sdf1 on f1.desired_fact_id = sdf1.desired_fact_id and s1.id = sdf1.survey_id \
join slum_data_household household1 on household1.id = f1.object_id \
where s1.id = %s and p1.id = %s and f1.content_type_id = 27 \
 and household1.slum_id= %s group by household1.household_code) \
UNION All \
(select household.household_code, f.desired_fact_id as question_id, f.data as answer from survey_fact f \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
join survey_surveydesiredfact sdf on f.desired_fact_id = sdf.desired_fact_id and s.id = sdf.survey_id \
join slum_data_household household on household.id = f.object_id \
where s.id = %s and p.id = %s and f.content_type_id = 27 and household.slum_id= %s order by household.household_code, sdf.weight asc)"

# path of survey excel file(xls) to read option and xml keys
RHS_excelFile = os.path.join(root_folder_path, 'FilesToRead', 'RHS.xls')

# create rapid household survey xml
def create_rhs_xml(options):
	# variables
	global question_map_dict
	global question_option_map_dict
	global option_dict
	
	global city_ward_slum_dict
	
	global qry_slum_list
	global qry_rhs_slum_household_survey_list
	global qry_rhs_survey_slum_household_question_answer
	
	global qry_rhs_common_slum_list
	global qry_rhs_master_slum_household_survey_list
	global qry_rhs_master_survey_slum_household_question_answer
	
	global gl_rhs_xml_dict
	
	global RHS_excelFile;
	
	xml_root = options['xml_root']
	xml_root_attr_id = options['xml_root_attr_id']
	xml_root_attr_version = options['xml_root_attr_version']
	xml_formhub_uuid = options['formhub_uuid']
	
	project_id = options['project']
	survey_id = options['survey']
	survey_id2 = options['survey2']
	mapexcelfile = options['mapped_excelFile']
	output_folder_path = options['output_path']
	
	unprocess_records = {}
	
	write_log("Start : Log for RHS Survey for per household in each slum ")
	
	#read old xls file city - ward - slum mapping
	read_xml_excel(RHS_excelFile)
	#print("Read excel file")
	write_log("Read excel file " + RHS_excelFile)
	
	#print(city_ward_slum_dict)
	
	#read map xlsx file for question, option mapping
	read_map_excel(mapexcelfile)
	#print("Read mapped excel file")
	write_log("Read mapped excel file" + mapexcelfile)
	
	# get slum code list
	slum_code_list = {}
	slum_code1_list = get_slum_code(qry_slum_list % survey_id)
	
	# check if second survey is exists or not 
	# get slum code list 
	if survey_id2:
		slum_code2_list = get_slum_code(qry_slum_list % survey_id2)
		
		slum_code2_list.update(slum_code1_list)
		
		slum_code_list.update(slum_code2_list)
	else:
		slum_code_list.update(slum_code1_list)
	
	#print("fatch slum code")
	write_log("fatch slum code")
	
	# set two survey for processing with default values
	rhs_group = {'master':None, 'New':None}
	
	if survey_id2:
		# get common slum among two survey
		common_slum_id_list = get_list_ids(qry_rhs_common_slum_list  % (survey_id, project_id, survey_id2, project_id))
		write_log("fatch common slum in both data for RHS -- " + (', '.join(str(x) for x in common_slum_id_list)))
		
		#print('common_slum_id_list=> ', common_slum_id_list)
		
		master_slum_household_list = get_household_survey(qry_rhs_master_slum_household_survey_list % (survey_id2, project_id))
		#print('master_slum_household_list before - ',master_slum_household_list.keys())
		
		# remove common survey from second survey list
		for slum_id in common_slum_id_list:
			del master_slum_household_list[slum_id]
	
		#print("fetch master slum household list")
		#print('master_slum_household_list  ',master_slum_household_list.keys())
	
		rhs_group['master']= master_slum_household_list
	
	# get slum and household list
	new_slum_household_list = get_household_survey(qry_rhs_slum_household_survey_list % (survey_id, project_id))
	#print("fetch slum household list")
	#print(new_slum_household_list)
	write_log("fetch household slum survey list")
	
	rhs_group['New'] = new_slum_household_list
	
	fail = 0
	success = 0
	total_process_house = 0
	
	# check for each survey into group
	for rhs_key, slum_household_list in rhs_group.items():
		#check key value
		#print('rhs_key = ', rhs_key)
		#print('slum_household_list == ',slum_household_list)
		
		# check if data exists for survey
		if slum_household_list:
			# check per household in each slum
			for slum, household_list in slum_household_list.items():
				print("proocessing data for slum - ", slum)
				write_log("proocessing data for slum - "+str(slum))
				
				unprocess_records.setdefault(str(slum), [])
				
				#get slum code for currently processing slum
				try:
					slum_code = None
					slum_code = slum_code_list[slum]
				except:
					pass
				
				# process data only if slum code exists
				if slum_code:
					#get admin ward and city code for slum
					admin_ward = get_admin_ward(slum_code)
					city = get_city_id(admin_ward)
					
					#print('slum_code : %s  admin_ward : %s  city : %s' % (slum_code, admin_ward, city))
					
					# get query for survey
					qry_rhs_question_answer = ''
					if rhs_key == 'master':
						qry_rhs_question_answer = (qry_rhs_master_survey_slum_household_question_answer  % (survey_id2, project_id, slum, survey_id2, project_id, slum)) 
					else: 
						qry_rhs_question_answer = (qry_rhs_survey_slum_household_question_answer  % (survey_id, project_id, slum, survey_id, project_id, slum))
					
					# get question and answer for households in slum
					household_fact = get_household_wise_question_answer(qry_rhs_question_answer)
					#print(household_fact)
					total_process_house += len(household_fact)
					
					# process each household in slum
					for household in household_list:
						try:
							#print("proocessing data for household - %s in slum - %s" % (household, slum))
							#write_log("proocessing data for household - %s in slum - %s" % (household, str(slum)))
							
							#get question and its answers for household
							fact = household_fact[household]
							
							#print('question answer', fact)
							
							# get dictionary to create xml
							rhs_xml_dict = copy.deepcopy(gl_rhs_xml_dict)
							
							# set dictionary to create RHS xml
							rhs_xml_dict['formhub']['uuid'] = xml_formhub_uuid
							
							rhs_xml_dict['start'] = get_answer('start', fact)
							rhs_xml_dict['end'] = get_answer('end', fact)
							
							#Administrative Information
							rhs_xml_dict['group_ce0hf58']['city'] = city
							rhs_xml_dict['group_ce0hf58']['admin_ward'] = admin_ward
							rhs_xml_dict['group_ce0hf58']['slum_name'] = slum_code
							
							date_of_rhs = get_answer('date_of_rhs', fact)
							if date_of_rhs:
								rhs_xml_dict['group_ce0hf58']['date_of_rhs'] = get_formatted_data(date_of_rhs)
							
							rhs_xml_dict['group_ce0hf58']['name_of_surveyor_who_collected_rhs_data'] = get_answer('name_of_surveyor_who_collected_rhs_data', fact)
							rhs_xml_dict['group_ce0hf58']['house_no'] = get_answer('house_no', fact)
							
							Type_of_structure_occupancy = get_answer('Type_of_structure_occupancy', fact)
							if Type_of_structure_occupancy:
								rhs_xml_dict['group_ce0hf58']['Type_of_structure_occupancy'] = Type_of_structure_occupancy
							
							#print('process - Administrative Information')
							#write_log('process - Administrative Information')
							
							#Household Information - Personal Information
							if Type_of_structure_occupancy == '01' or Type_of_structure_occupancy == '03':
								rhs_xml_dict['group_ye18c77']['group_ud4em45']['what_is_the_full_name_of_the_family_head_'] = get_answer('what_is_the_full_name_of_the_family_head_', fact)
								rhs_xml_dict['group_ye18c77']['group_ud4em45']['mobile_number'] = get_answer('mobile_number', fact)
								rhs_xml_dict['group_ye18c77']['group_ud4em45']['adhar_card_number'] = get_answer('adhar_card_number', fact)
								
							#print('process - Household Information - Personal Information')
							#write_log('process - Household Information - Personal Information')
							
							#Household Information - General Information
							if Type_of_structure_occupancy == '01':
								what_is_the_structure_of_the_house = get_answer('what_is_the_structure_of_the_house', fact)
								if what_is_the_structure_of_the_house:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['what_is_the_structure_of_the_house'] = what_is_the_structure_of_the_house
								
								what_is_the_ownership_status_of_the_house = get_answer('what_is_the_ownership_status_of_the_house', fact)
								if what_is_the_ownership_status_of_the_house:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['what_is_the_ownership_status_of_the_house'] = what_is_the_ownership_status_of_the_house
								
								number_of_family_members = get_answer('number_of_family_members', fact)
								try:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['number_of_family_members'] = get_rhs_family_member_count(number_of_family_members)
								except:
									#unprocess_records[str(slum)].append([str(household), "unable to process number of family member for answer =>"+(number_of_family_members if not isinstance(number_of_family_members, list) else ','.join(number_of_family_members))])
									pass
								
								Do_you_have_a_girl_child_under = get_answer('Do_you_have_a_girl_child_under', fact)
								if Do_you_have_a_girl_child_under:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['Do_you_have_a_girl_child_under'] = Do_you_have_a_girl_child_under
									
									if Do_you_have_a_girl_child_under == '01':
										rhs_xml_dict['group_ye18c77']['group_yw8pj39']['if_yes_how_many_'] = int(get_answer('if_yes_how_many_', fact))
								
								house_area_in_sq_ft = get_answer('house_area_in_sq_ft', fact)
								try:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['house_area_in_sq_ft'] = get_rhs_area_in_squar_feet(house_area_in_sq_ft)
								except:
									#unprocess_records[str(slum)].append([str(household), "unable to process house area in sq ft for answer =>"+(house_area_in_sq_ft if not isinstance(house_area_in_sq_ft, list) else ','.join(house_area_in_sq_ft))])
									pass
								
								Current_place_of_defecation_toilet = get_answer('Current_place_of_defecation_toilet', fact)
								if Current_place_of_defecation_toilet:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['Current_place_of_defecation_toilet'] = Current_place_of_defecation_toilet
								
								does_any_member_of_your_family_go_for_open_defecation_ = get_answer('does_any_member_of_your_family_go_for_open_defecation_', fact)
								if does_any_member_of_your_family_go_for_open_defecation_:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['does_any_member_of_your_family_go_for_open_defecation_'] = does_any_member_of_your_family_go_for_open_defecation_
								
								if Current_place_of_defecation_toilet and (Current_place_of_defecation_toilet == '01' or Current_place_of_defecation_toilet == '02'):
									where_the_individual_toilet_is_connected_to_ = get_answer('where_the_individual_toilet_is_connected_to_', fact)
									if where_the_individual_toilet_is_connected_to_:
										rhs_xml_dict['group_ye18c77']['group_yw8pj39']['where_the_individual_toilet_is_connected_to_'] = where_the_individual_toilet_is_connected_to_
								
								type_of_water_connection = get_answer('type_of_water_connection', fact)
								if type_of_water_connection:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['type_of_water_connection'] = type_of_water_connection
								
								facility_of_waste_collection = get_answer('facility_of_waste_collection', fact)
								if facility_of_waste_collection:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['facility_of_waste_collection'] = facility_of_waste_collection
								
								if Current_place_of_defecation_toilet and (Current_place_of_defecation_toilet != '01' or Current_place_of_defecation_toilet != '02'):
									Are_you_interested_in_individu = get_answer('Are_you_interested_in_individu', fact)
									if Are_you_interested_in_individu:
										rhs_xml_dict['group_ye18c77']['group_yw8pj39']['Are_you_interested_in_individu'] = Are_you_interested_in_individu
										
										if Are_you_interested_in_individu == '01':
											if_yes_why_ = get_answer('if_yes_why_', fact)
											if if_yes_why_:
												rhs_xml_dict['group_ye18c77']['group_yw8pj39']['if_yes_why_'] = if_yes_why_
											
										if Are_you_interested_in_individu == '02':
											if_no_why_ = get_answer('if_no_why_', fact)
											if if_no_why_:
												rhs_xml_dict['group_ye18c77']['group_yw8pj39']['if_no_why_'] = if_no_why_
										
										if Are_you_interested_in_individu == '01' and city != 3789:
											type_of_toilet_preference = get_answer('type_of_toilet_preference', fact)
											if type_of_toilet_preference:
												rhs_xml_dict['group_ye18c77']['group_yw8pj39']['type_of_toilet_preference'] = type_of_toilet_preference
								
								if Current_place_of_defecation_toilet and Current_place_of_defecation_toilet != '01':
									Have_you_applied_for_indiviual = get_answer('Have_you_applied_for_indiviual', fact)
									if Have_you_applied_for_indiviual:
										rhs_xml_dict['group_ye18c77']['grup_yw8pj39']['Have_you_applied_for_indiviual'] = Have_you_applied_for_indiviual
										
										if Have_you_applied_for_indiviual == '01':
											How_many_installements_have_yo = get_answer('How_many_installements_have_yo', fact)
											if How_many_installements_have_yo:
												rhs_xml_dict['group_ye18c77']['group_yw8pj39']['How_many_installements_have_yo'] = How_many_installements_have_yo
												
												if How_many_installements_have_yo == '02' or How_many_installements_have_yo == '03':
													rhs_xml_dict['group_ye18c77']['group_yw8pj39']['when_did_you_receive_the_first_installment_date'] = get_answer('when_did_you_receive_the_first_installment_date', fact)
												
												if How_many_installements_have_yo == '03':
													rhs_xml_dict['group_ye18c77']['group_yw8pj39']['when_did_you_receive_the_second_installment_date'] = get_answer('when_did_you_receive_the_second_installment_date', fact)
											
											what_is_the_status_of_toilet_under_sbm_ = get_answer('what_is_the_status_of_toilet_under_sbm_', fact)
											if what_is_the_status_of_toilet_under_sbm_:
												rhs_xml_dict['group_ye18c77']['group_yw8pj39']['what_is_the_status_of_toilet_under_sbm_'] = what_is_the_status_of_toilet_under_sbm_
								
								Does_any_family_members_has_co = get_answer('Does_any_family_members_has_co', fact)
								if Does_any_family_members_has_co:
									rhs_xml_dict['group_ye18c77']['group_yw8pj39']['Does_any_family_members_has_co'] = Does_any_family_members_has_co
							
							#print('process - Household Information - General Information')
							#write_log('process - Household Information - General Information')
							
							rhs_xml_dict['__version__'] = xml_root_attr_version
							
							rhs_xml_dict['meta']['instanceID'] = 'uuid:' + str(uuid.uuid4())
							
							
							# get xml string to store in xml file
							repeat_dict = {}
							xml_root_string = create_xml_string(rhs_xml_dict, repeat_dict, xml_root, xml_root_attr_id, xml_root_attr_version)
							
							# create xml file
							file_name = 'RHS_Survey_Slum_Id_' + str(slum) + '_House_code_' + household
							
							final_output_folder_path = os.path.join(output_folder_path, "slum_" +str(slum))
							
							create_xml_file(xml_root_string, file_name, final_output_folder_path)
							
							success += 1
								
							#print ('rhs data - ', rhs_xml_dict)
							
							del rhs_xml_dict
							
							#break;
						except Exception as ex:
							exception_log = 'Exception occurred for household id ' +str(household) + ' of slum id ' + str(slum) + ' \t  exception : '+ str(ex) +' \t  traceback : '+ traceback.format_exc()
							unprocess_records[str(slum)].append([str(household), str(ex)])
							
							fail += 1
							write_log(exception_log)
							
							#break;
							pass
					#break;
				else:
					# write log that slum code is not found for slum id
					write_log('slum code is not found for slum id '+str(slum))
					unprocess_records[str(slum)].append([None, 'slum code is not found when mapped'])
					fail += 1
			#break;
		
	if unprocess_records:
		write_log('List of slum and household for which unable to create xml')
		write_log('slum_id \t household_code \t exception')
		for slum_id, error_lst in unprocess_records.items():
			for error in error_lst:
				#print('error ', error[0], '    msg ',error[1])
				write_log(slum_id+' \t\t' + (error[0]+' \t' if error[0] else ' \t\t') +' \t\t\t' + error[1])
		
	write_log('End : Log for RHS Survey for slum \n')
	print("End processing")
	
	total_slum = (len(rhs_group['master']) if rhs_group['master'] else 0) + len(rhs_group['New'])
	total_house = (sum(len(v1) for v1 in iter(rhs_group['master'].values())) if rhs_group['master'] else 0) + sum(len(v2) for v2 in iter(rhs_group['New'].values()))
		
	result_log = 'total slum records : '+str(total_slum) +'\t total house records in all slum : '+str(total_house)
	print(result_log)
	write_log(result_log)
	
	result_log2 = 'process house records in all slum : '+str(total_process_house) + ' \t fail to process : '+str(fail) + ' \t success : '+str(success)	
	print(result_log2)
	write_log(result_log2)
	
	return;



