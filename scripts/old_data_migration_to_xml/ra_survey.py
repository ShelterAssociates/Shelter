#	Script written on Python 3.6
# 	Author : Parag Fulzele
#	Description : Methods to convert RA survey into xml
#

import uuid
import traceback
import copy

from common import *

# dictionary use to set and export data into xml
gl_ra_xml_dict = {
	'formhub' : {
		'uuid' : None
	},
	'start' : None,
	'end' : None,
	'group_ws5ux48' : {
		'date_of_survey' : None,
		'name_of_surveyor_s_who_checke' : None,
		'name_of_surveyor_s_who_collec' : None,
		'name_of_surveyor_s_who_took_t' : None
	},
	'group_zl6oo94' : {
		'group_uj8eg07' : {
			'city' : None,
			'admin_ward' : None,
			'slum_name' : None,
			'survey_sector_number' : None,
			'landmark' : None
		},
		'group_wb1hp47' : {
			'year_established_according_to' : None,
			'legal_status' : None,
			'Date_of_declaration' : None,
			'land_owner' : None,
			'development_plan_reservation_t' : None,
			'development_plan_reservation' : None,
			'approximate_area_of_the_settle' : None,
			'number_of_huts_in_settlement' : None,
			'location' : None,
			'topography' : None,
			'describe_the_slum' : None
		}
	},
	'group_te3dx03' : {
		'group_ul75r92' : {
			'status_of_defecation' : None,
			'number_of_community_toilet_blo' : None,
			'number_of_pay_and_use_CTBs' : None
		},
		'group_tb3th42' : {
			'is_the_CTB_in_use' : None,
			'fee_for_use_of_ctb_per_family' : None,
			'cost_of_pay_and_use_toilet_pe' : None,
			'ctb_gender_usage' : None,
			'total_number_of_mixed_seats_al' : None,
			'number_of_mixed_seats_allotted' : None,
			'the_reason_for_the_mixed_seats' : None,
			'number_of_seats_allotted_to_me' : None,
			'number_of_seats_allotted_to_me_001' : None,
			'the_reason_for_men_not_using_t' : None,
			'number_of_seats_allotted_to_wo' : None,
			'number_of_seats_allotted_to_wo_001' : None,
			'the_reason_for_women_not_using' : None,
			'is_the_ctb_available_at_night' : None,
			'ctb_maintenance_provided_by' : None,
			'condition_of_ctb_structure' : None,
			'out_of_total_seats_no_of_pans_in_good_condition' : None,
			'out_of_total_seats_no_of_doors_in_good_condition' : None,
			'out_of_total_seats_no_of_seats_where_electricity_is_available' : None,
			'out_of_total_seats_no_of_seats_where_tiles_on_wall_are_in_good_condition' : None,
			'out_of_total_seats_no_of_seats_where_tiles_on_floor_are_in_good_condition' : None,
			'frequency_of_ctb_cleaning_by_U' : None,
			'does_the_ulb_ngo_communty_use' : None,
			'cleanliness_of_the_ctb' : None,
			'is_there_a_caretaker_for_the_C' : None,
			'type_of_water_supply_in_ctb' : None,
			'capacity_of_ctb_water_tank_in' : None,
			'litres_of_water_used_by_commun' : None,
			'availability_of_water_in_the_t' : None,
			'availability_of_electricity_in' : None,
			'availability_of_electricity_in_001' : None,
			'facility_in_the_toilet_block_f' : None,
			'condition_of_facility_for_chil' : None,
			'sewage_disposal_system' : None,
			'distance_to_nearest_ulb_sewer' : None
		},
		'toilet_comment' : None
	},
	'group_zj8tc43' : {
		'Total_number_of_standposts_in_' : None,
		'Total_number_of_standposts_NOT' : None,
		'total_number_of_taps_in_use_n' : None,
		'total_number_of_taps_in_use_n_001' : None,
		'total_number_of_handpumps_in_u' : None,
		'total_number_of_handpumps_in_u_001' : None,
		'alternative_source_of_water' : None,
		'availability_of_water' : None,
		'pressure_of_water_in_the_syste' : None,
		'coverage_of_wateracross_settle' : None,
		'quality_of_water_in_the_system' : None,
		'water_supply_comment' : None
	},
	'group_ks0wh10' : {
		'total_number_of_waste_containe' : None,
		'facility_of_waste_collection' : None,
		'frequency_of_waste_collection' : None,
		'frequency_of_waste_collection__002' : None,
		'frequency_of_waste_collection_001' : None,
		'frequency_of_waste_collection_' : None,
		'frequency_of_waste_collection__001' : None,
		'coverage_of_waste_collection_a' : None,
		'coverage_of_waste_collection_a_001' : None,
		'coverage_of_waste_collection_a_002' : None,
		'coverage_of_waste_collection_a_003' : None,
		'where_are_the_communty_open_du' : None,
		'do_the_member_of_community_dep' : None,
		'Waste_management_comments' : None
	},
	'group_kk5gz02' : {
		'presence_of_drains_within_the' : None,
		'coverage_of_drains_across_the' : None,
		'do_the_drains_get_blocked' : None,
		'is_the_drainage_gradient_adequ' : None,
		'diameter_of_ulb_sewer_line_acr' : None,
		'drainage_comment' : None
	},
	'group_bv7hf31' : {
		'Presence_of_gutter' : None,
		'type_of_gutter_within_the_sett' : None,
		'coverage_of_gutter' : None,
		'are_gutter_covered' : None,
		'do_gutters_flood' : None,
		'do_gutter_get_choked' : None,
		'is_gutter_gradient_adequate' : None,
		'comments_on_gutter' : None
	},
	'group_xy9hz30' : {
		'presence_of_roads_within_the_s' : None,
		'type_of_roads_within_the_settl' : None,
		'coverage_of_pucca_road_across' : None,
		'finish_of_the_road' : None,
		'average_width_of_internal_road' : None,
		'average_width_of_arterial_road' : None,
		'point_of_vehicular_access_to_t' : None,
		'is_the_settlement_below_or_abo' : None,
		'are_the_huts_below_or_above_th' : None,
		'road_and_access_comment' : None
	},
	'__version__' : None,
	'meta' : {
		'instanceID' : None
	}
}

## RA survey queries
# get list of all slum for survey
qry_ra_survey_list = "select distinct f.object_id as slum_id from survey_fact f join slum_data_slum slum on slum.id = f.object_id \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
where s.id = %s and p.id = %s and f.content_type_id = 26 order by f.object_id asc"

# get list of all question and answer for slum
qry_ra_survey_slum_question_answer = "(select '-1' as question_id, to_char(min(f1.updated_on),'YYYY-MM-DD\"T\"HH24:MI:SS.MS+05:30') as answer from survey_fact f1 \
join survey_survey s1 on s1.id = f1.survey_id join survey_project p1 on p1.id = s1.project_id \
join survey_surveydesiredfact sdf1 on f1.desired_fact_id = sdf1.desired_fact_id and s1.id = sdf1.survey_id \
join slum_data_slum slum1 on slum1.id = f1.object_id \
where s1.id = %s and p1.id = %s and f1.content_type_id = 26 and slum1.id=%s)\
UNION All \
(select f.desired_fact_id as question_id, f.data as answer from survey_fact f \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
join survey_surveydesiredfact sdf on f.desired_fact_id = sdf.desired_fact_id and s.id = sdf.survey_id \
join slum_data_slum slum on slum.id = f.object_id \
where s.id = %s and p.id = %s and f.content_type_id = 26 and slum.id=%s order by sdf.weight asc) "

# get list of all question and answer for toilet
qry_ra_survey_toilet_question_answer = "select toilet.id, f.desired_fact_id as question_id, f.data as answer from survey_fact f \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
join survey_surveydesiredfact sdf on f.desired_fact_id = sdf.desired_fact_id and s.id = sdf.survey_id \
join slum_data_toilet toilet on toilet.id = f.object_id join slum_data_slum slum on slum.id = toilet.slum_id \
where s.id = %s and p.id = %s and f.content_type_id = 33 and slum.id=%s order by toilet_id, sdf.weight asc"

# path of survey excel file(xls) to read option and xml keys
RA_excelFile = os.path.join(root_folder_path, 'FilesToRead', 'RA.xls')

# create rapid survey xml
def create_ra_xml(options):
	# get list of all servey to create xml for each survey
	global question_map_dict
	global question_option_map_dict
	global option_dict
	
	global city_ward_slum_dict
	
	global qry_slum_list
	global qry_ra_survey_list
	global qry_ra_survey_question_answer
	
	global gl_ra_xml_dict
	
	global RA_excelFile;
	
	xml_root = options['xml_root']
	xml_root_attr_id = options['xml_root_attr_id']
	xml_root_attr_version = options['xml_root_attr_version']
	xml_formhub_uuid = options['formhub_uuid']
	
	project_id = options['project']
	survey_id = options['survey']
	mapexcelfile = options['mapped_excelFile']
	output_folder_path = options['output_path']
	
	
	name_mismatch_records = {
		'name_of_surveyor_s_who_checke' : {'count':0, 'slum':[]},
		'name_of_surveyor_s_who_collec' : {'count':0, 'slum':[]},
		'name_of_surveyor_s_who_took_t' : {'count':0, 'slum':[]}
	}
	unprocess_records = {}
	
	write_log("Start : Log for RA Survey for each slum ")
	
	#read old xls file city - ward - slum mapping
	read_xml_excel(RA_excelFile)
	#print("Read excel file")
	write_log("Read excel file " + RA_excelFile)
	
	#print(city_ward_slum_dict)
	
	#read map xlsx file for question, option mapping
	read_map_excel(mapexcelfile)
	#print("Read mapped excel file")
	write_log("Read mapped excel file" + mapexcelfile)
	
	# get slum code list
	slum_code_list = get_slum_code(qry_slum_list % survey_id)
	#print("fatch slum code")
	#print(slum_code_list)
	write_log("fatch slum code")
	
	# get slum list 
	survey_list = get_list_ids(qry_ra_survey_list % (survey_id, project_id))
	#print("fetch survey list")
	#print(survey_list)
	write_log("fetch survey list")
	
	total_slum = len(survey_list)
	unprocess_slum = 0
	total_process = 0
	fail = 0
	success = 0
	
	progress_max_count = len(survey_list)
	progess_counter = 0
	# set progress bar
	show_progress_bar(progess_counter, progress_max_count)
	
	# check per slum
	for slum in survey_list:
		total_process += 1
		try:
			#print("proocessing data for slum - ", slum)
			write_log("proocessing data for slum id : "+ str(slum))
			toilet_info = []
			
			slum_fact = get_question_answer(qry_ra_survey_slum_question_answer % (survey_id, project_id, slum, survey_id, project_id, slum))  
			toilet_fact = get_toilet_question_answer(qry_ra_survey_toilet_question_answer % (survey_id, project_id, slum))
						
			fact = {}
			fact.update(slum_fact)
			#fact.update(toilet_fact)
			
			#get slum code for currently processing slum
			slum_code = slum_code_list[slum]
			
			# process data only if slum code exists
			if slum_code:
				#print('slum_fact - ', slum_fact)
				#print('\n')
				#print('toilet_fact - ', toilet_fact)
				#print('\n')
				#print('question answer', fact)
				
				#get admin ward and city code for slum
				admin_ward = get_admin_ward(slum_code)
				city = get_city_id(admin_ward)
				
				# get dictionary to create xml
				ra_xml_dict = copy.deepcopy(gl_ra_xml_dict)
				
				group_tb3th42_dict = copy.deepcopy(ra_xml_dict['group_te3dx03']['group_tb3th42'])
				del ra_xml_dict['group_te3dx03']['group_tb3th42']
				
				del ra_xml_dict['group_zl6oo94']['group_wb1hp47']['Date_of_declaration']
				
				
				#toilet_block_details = group_tb3th42_dict.copy()
				
				#print('slum_code : %s  admin_ward : %s  city : %s' % (slum_code, admin_ward, city))
				
				#print('toilet_block_details : ',toilet_block_details)
				
				# set dictionary to create RHS xml
				ra_xml_dict['formhub']['uuid'] = xml_formhub_uuid
				
				ra_xml_dict['start'] = get_answer('start', fact)
				ra_xml_dict['end'] = get_answer('end', fact)
				
				#Administration section
				date_of_survey = get_answer('date_of_survey', fact) #check date format
				if date_of_survey:
					#print("date_of_survey ="+date_of_survey)
					ra_xml_dict['group_ws5ux48']['date_of_survey'] = get_formatted_data(date_of_survey)
				
				name_of_surveyor_s_who_checke = get_answer('name_of_surveyor_s_who_checke', fact)
				name_of_surveyor_1 = get_name_id('sf02f44', name_of_surveyor_s_who_checke)
				if name_of_surveyor_1 is None:
					name_mismatch_records['name_of_surveyor_s_who_checke']['count'] += 1
					name_mismatch_records['name_of_surveyor_s_who_checke']['slum'].append(slum)
				else:
					ra_xml_dict['group_ws5ux48']['name_of_surveyor_s_who_checke'] = name_of_surveyor_1
				
				name_of_surveyor_s_who_collec = get_answer('name_of_surveyor_s_who_collec', fact)
				name_of_surveyor_2 = get_name_id('qs59t66', name_of_surveyor_s_who_collec)
				if name_of_surveyor_2 is None:
					name_mismatch_records['name_of_surveyor_s_who_collec']['count'] += 1
					name_mismatch_records['name_of_surveyor_s_who_collec']['slum'].append(slum)
				else:
					ra_xml_dict['group_ws5ux48']['name_of_surveyor_s_who_collec'] = name_of_surveyor_2
				
				name_of_surveyor_s_who_took_t = get_answer('name_of_surveyor_s_who_took_t', fact)
				name_of_surveyor_3 = get_name_id('gf4ac05', name_of_surveyor_s_who_took_t)
				if name_of_surveyor_3 is None:
					name_mismatch_records['name_of_surveyor_s_who_took_t']['count'] += 1
					name_mismatch_records['name_of_surveyor_s_who_took_t']['slum'].append(slum)
				else:
					ra_xml_dict['group_ws5ux48']['name_of_surveyor_s_who_took_t'] = name_of_surveyor_3
				
				#print('process - Administration section')
				#write_log('process - Administration section')
				
				#General information - Part A
				ra_xml_dict['group_zl6oo94']['group_uj8eg07']['city'] = city
				ra_xml_dict['group_zl6oo94']['group_uj8eg07']['admin_ward'] = admin_ward
				ra_xml_dict['group_zl6oo94']['group_uj8eg07']['slum_name'] = slum_code
				ra_xml_dict['group_zl6oo94']['group_uj8eg07']['survey_sector_number'] = get_answer('survey_sector_number', fact)
				ra_xml_dict['group_zl6oo94']['group_uj8eg07']['landmark'] = get_answer('landmark', fact)
				
				#print('process - General information - Part A')
				#write_log('process - General information - Part A')
				
				#General information - Part B
				ra_xml_dict['group_zl6oo94']['group_wb1hp47']['year_established_according_to'] = get_answer('year_established_according_to', fact)
				legal_status = get_answer('legal_status', fact)
				
				if legal_status:
					ra_xml_dict['group_zl6oo94']['group_wb1hp47']['legal_status'] = legal_status
					if legal_status != '01':
						ra_xml_dict['group_zl6oo94']['group_wb1hp47']['Date_of_declaration'] = get_answer('Date_of_declaration', fact)
					#else:
						#del ra_xml_dict['group_zl6oo94']['group_wb1hp47']['Date_of_declaration']
				
				land_owner = get_answer('land_owner', fact)
				if land_owner:
					ra_xml_dict['group_zl6oo94']['group_wb1hp47']['land_owner'] = land_owner
				
				development_plan_reservation_t = get_answer('development_plan_reservation_t', fact)
				if development_plan_reservation_t:
					ra_xml_dict['group_zl6oo94']['group_wb1hp47']['development_plan_reservation_t'] = development_plan_reservation_t
				
				ra_xml_dict['group_zl6oo94']['group_wb1hp47']['development_plan_reservation'] = get_answer('development_plan_reservation', fact)
				
				approximate_area_of_the_settle = get_answer('approximate_area_of_the_settle', fact)
				ra_xml_dict['group_zl6oo94']['group_wb1hp47']['approximate_area_of_the_settle'] = convert_area_from_square_meters(approximate_area_of_the_settle)
				
				number_of_huts_in_settlement = get_approximat_huts(slum, get_answer('number_of_huts_in_settlement', fact))
				ra_xml_dict['group_zl6oo94']['group_wb1hp47']['number_of_huts_in_settlement'] = number_of_huts_in_settlement
				
				location = get_answer('location', fact)
				if location:
					ra_xml_dict['group_zl6oo94']['group_wb1hp47']['location'] = location
				
				topography = get_answer('topography', fact)
				if topography:
					ra_xml_dict['group_zl6oo94']['group_wb1hp47']['topography'] = topography
				
				ra_xml_dict['group_zl6oo94']['group_wb1hp47']['describe_the_slum'] = get_answer('describe_the_slum', fact)
				
				#print('process - General information - Part B')
				#write_log('process - General information - Part B')
				
				#Toilet Information - Status of Defecation
				status_of_defecation = get_answer('status_of_defecation', fact)
				if status_of_defecation:
					ra_xml_dict['group_te3dx03']['group_ul75r92']['status_of_defecation'] = status_of_defecation
				
				number_of_community_toilet_blo = get_answer('number_of_community_toilet_blo', fact)
				ra_xml_dict['group_te3dx03']['group_ul75r92']['number_of_community_toilet_blo'] = number_of_community_toilet_blo
				
				if number_of_community_toilet_blo and int(number_of_community_toilet_blo) > 0:
					no_toilet = int(number_of_community_toilet_blo)
					no_actual_toilet = len(toilet_fact)
					if no_toilet != no_actual_toilet:
						ra_xml_dict['group_te3dx03']['group_ul75r92']['number_of_community_toilet_blo'] = no_actual_toilet
						
					ra_xml_dict['group_te3dx03']['group_ul75r92']['number_of_pay_and_use_CTBs'] = int(get_answer('number_of_pay_and_use_CTBs', fact))
				
					# loop for no of toilet 
					for toilet_id in toilet_fact.keys():
						#Toilet Information - Toilet Block Details
						toilet_details_dict = {}
						
						is_the_CTB_in_use = get_answer('is_the_CTB_in_use', toilet_fact[toilet_id])
						if is_the_CTB_in_use:
							toilet_details_dict['is_the_CTB_in_use'] = is_the_CTB_in_use
							
							if is_the_CTB_in_use == '04':
								toilet_details_dict['fee_for_use_of_ctb_per_family'] = int(get_answer('fee_for_use_of_ctb_per_family', toilet_fact[toilet_id]))
								toilet_details_dict['cost_of_pay_and_use_toilet_pe'] = int(get_answer('cost_of_pay_and_use_toilet_pe', toilet_fact[toilet_id]))
								toilet_details_dict['ctb_gender_usage'] = get_answer('ctb_gender_usage', toilet_fact[toilet_id])
								
								ctb_gender_usage = get_answer('ctb_gender_usage', toilet_fact[toilet_id])
								if ctb_gender_usage:
									if ctb_gender_usage == '03':
										toilet_details_dict['total_number_of_mixed_seats_al'] = 0 #get_answer('total_number_of_mixed_seats_al', toilet_fact[toilet_id])
										
										number_of_mixed_seats_allotted = get_answer('number_of_mixed_seats_allotted', toilet_fact[toilet_id])
										toilet_details_dict['number_of_mixed_seats_allotted'] = 0 #get_answer('number_of_mixed_seats_allotted', toilet_fact[toilet_id])
										
										#if number_of_mixed_seats_allotted is not None and int(number_of_mixed_seats_allotted) > 0:
										#	toilet_details_dict['the_reason_for_the_mixed_seats'] = None #get_answer('the_reason_for_the_mixed_seats', toilet_fact[toilet_id])
									elif ctb_gender_usage == '01' or ctb_gender_usage == '04':
										toilet_details_dict['number_of_seats_allotted_to_me'] = int(get_answer('number_of_seats_allotted_to_me', toilet_fact[toilet_id]))
										
										number_of_seats_allotted_to_me_001 = get_answer('number_of_seats_allotted_to_me_001', toilet_fact[toilet_id])
										toilet_details_dict['number_of_seats_allotted_to_me_001'] = int(number_of_seats_allotted_to_me_001)
										
										if int(number_of_seats_allotted_to_me_001) > 0:
											the_reason_for_men_not_using_t = get_answer('the_reason_for_men_not_using_t', toilet_fact[toilet_id])
											if the_reason_for_men_not_using_t:
												toilet_details_dict['the_reason_for_men_not_using_t'] = the_reason_for_men_not_using_t
									elif ctb_gender_usage == '02' or ctb_gender_usage == '04':
										toilet_details_dict['number_of_seats_allotted_to_wo'] = int(get_answer('number_of_seats_allotted_to_wo', toilet_fact[toilet_id]))
										
										number_of_seats_allotted_to_wo_001 = get_answer('number_of_seats_allotted_to_wo_001', toilet_fact[toilet_id])
										toilet_details_dict['number_of_seats_allotted_to_wo_001'] = int(number_of_seats_allotted_to_wo_001)
										
										if int(number_of_seats_allotted_to_wo_001) > 0:
											the_reason_for_women_not_using = get_answer('the_reason_for_women_not_using', toilet_fact[toilet_id])
											if the_reason_for_women_not_using:
												toilet_details_dict['the_reason_for_women_not_using'] = the_reason_for_women_not_using
								
								is_the_ctb_available_at_night = get_answer('is_the_ctb_available_at_night', toilet_fact[toilet_id])
								if is_the_ctb_available_at_night:
									toilet_details_dict['is_the_ctb_available_at_night'] = is_the_ctb_available_at_night
								
								ctb_maintenance_provided_by = get_answer('ctb_maintenance_provided_by', toilet_fact[toilet_id])
								if ctb_maintenance_provided_by:
									toilet_details_dict['ctb_maintenance_provided_by'] = ctb_maintenance_provided_by
								
								condition_of_ctb_structure = get_answer('condition_of_ctb_structure', toilet_fact[toilet_id])
								if condition_of_ctb_structure:
									toilet_details_dict['condition_of_ctb_structure'] = condition_of_ctb_structure
								
								toilet_details_dict['out_of_total_seats_no_of_pans_in_good_condition'] = None #get_answer('out_of_total_seats_no_of_pans_in_good_condition', toilet_fact[toilet_id])
								toilet_details_dict['out_of_total_seats_no_of_doors_in_good_condition'] = None #get_answer('out_of_total_seats_no_of_doors_in_good_condition', toilet_fact[toilet_id])
								toilet_details_dict['out_of_total_seats_no_of_seats_where_electricity_is_available'] = None #get_answer('out_of_total_seats_no_of_seats_where_electricity_is_available', toilet_fact[toilet_id])
								toilet_details_dict['out_of_total_seats_no_of_seats_where_tiles_on_wall_are_in_good_condition'] = None #get_answer('out_of_total_seats_no_of_seats_where_tiles_on_wall_are_in_good_condition', toilet_fact[toilet_id])
								toilet_details_dict['out_of_total_seats_no_of_seats_where_tiles_on_floor_are_in_good_condition'] = None #get_answer('out_of_total_seats_no_of_seats_where_tiles_on_floor_are_in_good_condition', toilet_fact[toilet_id])
								
								frequency_of_ctb_cleaning_by_U = get_answer('frequency_of_ctb_cleaning_by_U', toilet_fact[toilet_id])
								if frequency_of_ctb_cleaning_by_U:
									toilet_details_dict['frequency_of_ctb_cleaning_by_U'] = frequency_of_ctb_cleaning_by_U
								
								does_the_ulb_ngo_communty_use = get_answer('does_the_ulb_ngo_communty_use', toilet_fact[toilet_id])
								if does_the_ulb_ngo_communty_use:
									toilet_details_dict['does_the_ulb_ngo_communty_use'] = does_the_ulb_ngo_communty_use
								
								cleanliness_of_the_ctb = get_answer('cleanliness_of_the_ctb', toilet_fact[toilet_id])
								if cleanliness_of_the_ctb:
									toilet_details_dict['cleanliness_of_the_ctb'] = cleanliness_of_the_ctb
								
								is_there_a_caretaker_for_the_C = get_answer('is_there_a_caretaker_for_the_C', toilet_fact[toilet_id])
								if is_there_a_caretaker_for_the_C:
									toilet_details_dict['is_there_a_cretaker_for_the_C'] = is_there_a_caretaker_for_the_C
								
								type_of_water_supply_in_ctb = get_answer('type_of_water_supply_in_ctb', toilet_fact[toilet_id])
								if type_of_water_supply_in_ctb:
									toilet_details_dict['type_of_water_supply_in_ctb'] = type_of_water_supply_in_ctb
									
									if type_of_water_supply_in_ctb == '02':
										capacity_of_ctb_water_tank_in = get_answer('capacity_of_ctb_water_tank_in', toilet_fact[toilet_id])
										if capacity_of_ctb_water_tank_in:
											toilet_details_dict['capacity_of_ctb_water_tank_in'] = capacity_of_ctb_water_tank_in
								
								litres_of_water_used_by_commun = get_answer('litres_of_water_used_by_commun', toilet_fact[toilet_id])
								if litres_of_water_used_by_commun:
									toilet_details_dict['litres_of_water_used_by_commun'] = litres_of_water_used_by_commun
								
								availability_of_water_in_the_t = get_answer('availability_of_water_in_the_t', toilet_fact[toilet_id])
								if availability_of_water_in_the_t:
									toilet_details_dict['availability_of_water_in_the_t'] = availability_of_water_in_the_t
								
								availability_of_electricity_in = get_answer('availability_of_electricity_in', toilet_fact[toilet_id])
								if availability_of_electricity_in:
									toilet_details_dict['availability_of_electricity_in'] = availability_of_electricity_in
								
								availability_of_electricity_in_001 = get_answer('availability_of_electricity_in_001', toilet_fact[toilet_id])
								if availability_of_electricity_in_001:
									toilet_details_dict['availability_of_electricity_in_001'] = availability_of_electricity_in_001
								
								facility_in_the_toilet_block_f = get_answer('facility_in_the_toilet_block_f', toilet_fact[toilet_id])
								if facility_in_the_toilet_block_f:
									toilet_details_dict['facility_in_the_toilet_block_f'] = facility_in_the_toilet_block_f
									
									if facility_in_the_toilet_block_f == '02':
										condition_of_facility_for_chil = get_answer('condition_of_facility_for_chil', toilet_fact[toilet_id])
										if condition_of_facility_for_chil:
											toilet_details_dict['condition_of_facility_for_chil'] = condition_of_facility_for_chil
								
								sewage_disposal_system = get_answer('sewage_disposal_system', toilet_fact[toilet_id])
								if sewage_disposal_system:
									toilet_details_dict['sewage_disposal_system'] = sewage_disposal_system
								
								distance_to_nearest_ulb_sewer = get_answer('distance_to_nearest_ulb_sewer', toilet_fact[toilet_id])
								if distance_to_nearest_ulb_sewer:
									toilet_details_dict['distance_to_nearest_ulb_sewer'] = distance_to_nearest_ulb_sewer
							
							# add into list 
							toilet_info.append({'group_tb3th42': toilet_details_dict})
				else:
					del ra_xml_dict['group_te3dx03']['group_ul75r92']['number_of_pay_and_use_CTBs']
					
				ra_xml_dict['group_te3dx03']['toilet_comment'] = get_answer('toilet_comment', fact)
				
				#print('process - Toilet Information - Status of Defecation')
				#write_log('process - Toilet Information - Status of Defecation')
				
				#Water Information
				Total_number_of_standposts_in_ = get_answer('Total_number_of_standposts_in_', fact)
				
				if Total_number_of_standposts_in_:
					ra_xml_dict['group_zj8tc43']['Total_number_of_standposts_in_'] = int(Total_number_of_standposts_in_)
					
					if  int(Total_number_of_standposts_in_) > 0:
						ra_xml_dict['group_zj8tc43']['total_number_of_taps_in_use_n'] = get_answer('total_number_of_taps_in_use_n', fact)
				
				Total_number_of_standposts_NOT = get_answer('Total_number_of_standposts_NOT', fact)
								
				if Total_number_of_standposts_NOT:
					ra_xml_dict['group_zj8tc43']['Total_number_of_standposts_NOT'] = Total_number_of_standposts_NOT
					
					if (not(Total_number_of_standposts_in_ is None) and int(Total_number_of_standposts_in_) > 0) or int(Total_number_of_standposts_NOT) > 0:
						ra_xml_dict['group_zj8tc43']['total_number_of_taps_in_use_n_001'] = get_answer('total_number_of_taps_in_use_n_001', fact)
				
				total_number_of_handpumps_in_u = get_answer('total_number_of_handpumps_in_u', fact)
				ra_xml_dict['group_zj8tc43']['total_number_of_handpumps_in_u'] = int(total_number_of_handpumps_in_u) if total_number_of_handpumps_in_u else 0
				
				total_number_of_handpumps_in_u_001 = get_answer('total_number_of_handpumps_in_u_001', fact)
				ra_xml_dict['group_zj8tc43']['total_number_of_handpumps_in_u_001'] = int(total_number_of_handpumps_in_u_001) if total_number_of_handpumps_in_u_001 else 0
				
				alternative_source_of_water = get_answer('alternative_source_of_water', fact)
				if alternative_source_of_water:
					ra_xml_dict['group_zj8tc43']['alternative_source_of_water'] = alternative_source_of_water
				
				availability_of_water = get_answer('availability_of_water', fact)
				if availability_of_water:
					ra_xml_dict['group_zj8tc43']['availability_of_water'] = availability_of_water
				
				pressure_of_water_in_the_syste = get_answer('pressure_of_water_in_the_syste', fact)
				if pressure_of_water_in_the_syste:
					ra_xml_dict['group_zj8tc43']['pressure_of_water_in_the_syste'] = pressure_of_water_in_the_syste
				
				coverage_of_wateracross_settle = get_answer('coverage_of_wateracross_settle', fact)
				if coverage_of_wateracross_settle:
					ra_xml_dict['group_zj8tc43']['coverage_of_wateracross_settle'] = coverage_of_wateracross_settle
				
				quality_of_water_in_the_system = get_answer('quality_of_water_in_the_system', fact)
				if quality_of_water_in_the_system:
					ra_xml_dict['group_zj8tc43']['quality_of_water_in_the_system'] = quality_of_water_in_the_system
				
				ra_xml_dict['group_zj8tc43']['water_supply_comment'] = get_answer('water_supply_comment', fact)
				
				#print('process - Water Information')
				#write_log('process - Water Information')
				
				#Waste Management Information
				total_number_of_waste_containe = get_answer('total_number_of_waste_containe', fact)
				ra_xml_dict['group_ks0wh10']['total_number_of_waste_containe'] = int(total_number_of_waste_containe) if total_number_of_waste_containe else 0
				
				facility_of_waste_collection = get_answer('facility_of_waste_collection', fact)
				if facility_of_waste_collection:
					ra_xml_dict['group_ks0wh10']['facility_of_waste_collection'] = facility_of_waste_collection
					
					#if facility_of_waste_collection == '02':
						#ra_xml_dict['group_ks0wh10']['frequency_of_waste_collection'] = None #get_answer('frequency_of_waste_collection', fact)
						#ra_xml_dict['group_ks0wh10']['coverage_of_waste_collection_a'] = None #get_answer('coverage_of_waste_collection_a', fact)
					#elif facility_of_waste_collection == '03':
						#ra_xml_dict['group_ks0wh10']['frequency_of_waste_collection__002'] = None #get_answer('frequency_of_waste_collection__002', fact)
						#ra_xml_dict['group_ks0wh10']['coverage_of_waste_collection_a_001'] = None #get_answer('coverage_of_waste_collection_a_001', fact)
					#elif facility_of_waste_collection == '04':
						#ra_xml_dict['group_ks0wh10']['frequency_of_waste_collection_001'] = None #get_answer('frequency_of_waste_collection_001', fact)
						#ra_xml_dict['group_ks0wh10']['coverage_of_waste_collection_a_002'] = None #get_answer('coverage_of_waste_collection_a_002', fact)
					#elif facility_of_waste_collection == '05':
						#ra_xml_dict['group_ks0wh10']['frequency_of_waste_collection_'] = None #get_answer('frequency_of_waste_collection_', fact)
						#ra_xml_dict['group_ks0wh10']['coverage_of_waste_collection_a_003'] = None #get_answer('coverage_of_waste_collection_a_003', fact)
					#elif facility_of_waste_collection == '06':
						#ra_xml_dict['group_ks0wh10']['frequency_of_waste_collection__001'] = None #get_answer('frequency_of_waste_collection__001', fact)
				
				where_are_the_communty_open_du = get_answer('where_are_the_communty_open_du', fact)
				if where_are_the_communty_open_du:
					ra_xml_dict['group_ks0wh10']['where_are_the_communty_open_du'] = where_are_the_communty_open_du
				
				do_the_member_of_community_dep = get_answer('do_the_member_of_community_dep', fact)
				if do_the_member_of_community_dep:
					ra_xml_dict['group_ks0wh10']['do_the_member_of_community_dep'] = do_the_member_of_community_dep
				
				ra_xml_dict['group_ks0wh10']['Waste_management_comments'] = get_answer('Waste_management_comments', fact)
				
				#print('process - Waste Management Information')
				#write_log('process - Waste Management Information')
				
				#Drainage Information
				presence_of_drains_within_the = get_answer('presence_of_drains_within_the', fact)
				if presence_of_drains_within_the:
					ra_xml_dict['group_kk5gz02']['presence_of_drains_within_the'] = presence_of_drains_within_the
					
					if presence_of_drains_within_the == '02':
						coverage_of_drains_across_the = get_answer('coverage_of_drains_across_the', fact)
						if coverage_of_drains_across_the:
							ra_xml_dict['group_kk5gz02']['coverage_of_drains_across_the'] = coverage_of_drains_across_the
						
						do_the_drains_get_blocked = get_answer('do_the_drains_get_blocked', fact)
						if do_the_drains_get_blocked:
							ra_xml_dict['group_kk5gz02']['do_the_drains_get_blocked'] = do_the_drains_get_blocked
						
						is_the_drainage_gradient_adequ = get_answer('is_the_drainage_gradient_adequ', fact)
						if is_the_drainage_gradient_adequ:
							ra_xml_dict['group_kk5gz02']['is_the_drainage_gradient_adequ'] = is_the_drainage_gradient_adequ
						
						#ra_xml_dict['group_kk5gz02']['diameter_of_ulb_sewer_line_acr'] = None #get_answer('diameter_of_ulb_sewer_line_acr', fact)
					
				ra_xml_dict['group_kk5gz02']['drainage_comment'] = get_answer('drainage_comment', fact)
				
				#print('process - Drainage Information')
				#write_log('process - Drainage Information')
				
				#Gutter Information
				Presence_of_gutter = get_answer('Presence_of_gutter', fact)
				if Presence_of_gutter:
					ra_xml_dict['group_bv7hf31']['Presence_of_gutter'] = Presence_of_gutter
					
					if Presence_of_gutter == '02':
						ra_xml_dict['group_bv7hf31']['type_of_gutter_within_the_sett'] = get_answer('type_of_gutter_within_the_sett', fact)
						ra_xml_dict['group_bv7hf31']['coverage_of_gutter'] = get_answer('coverage_of_gutter', fact)
						ra_xml_dict['group_bv7hf31']['are_gutter_covered'] = get_answer('are_gutter_covered', fact)
						ra_xml_dict['group_bv7hf31']['do_gutters_flood'] = get_answer('do_gutters_flood', fact)
						ra_xml_dict['group_bv7hf31']['do_gutter_get_choked'] = get_answer('do_gutter_get_choked', fact)
						ra_xml_dict['group_bv7hf31']['is_gutter_gradient_adequate'] = get_answer('is_gutter_gradient_adequate', fact)
					
				ra_xml_dict['group_bv7hf31']['comments_on_gutter'] = get_answer('comments_on_gutter', fact)
				
				#print('process - Gutter Information')
				#write_log('process - Gutter Information')
				
				#Roads and Access Information
				presence_of_roads_within_the_s = get_answer('presence_of_roads_within_the_s', fact)
				if presence_of_roads_within_the_s:
					ra_xml_dict['group_xy9hz30']['presence_of_roads_within_the_s'] = presence_of_roads_within_the_s
					
					if presence_of_roads_within_the_s == '02':
						type_of_roads_within_the_settl = get_answer('type_of_roads_within_the_settl', fact)
						if type_of_roads_within_the_settl:
							ra_xml_dict['group_xy9hz30']['type_of_roads_within_the_settl'] = type_of_roads_within_the_settl
							
							if type_of_roads_within_the_settl == '03':
								coverage_of_pucca_road_across = get_answer('coverage_of_pucca_road_across', fact)
								if coverage_of_pucca_road_across:
									ra_xml_dict['group_xy9hz30']['coverage_of_pucca_road_across'] = coverage_of_pucca_road_across
						
						finish_of_the_road = get_answer('finish_of_the_road', fact)
						if finish_of_the_road:
							ra_xml_dict['group_xy9hz30']['finish_of_the_road'] = finish_of_the_road
						
						average_width_of_internal_road = get_answer('average_width_of_internal_road', fact)
						if average_width_of_internal_road:
							ra_xml_dict['group_xy9hz30']['average_width_of_internal_road'] = average_width_of_internal_road
						
						average_width_of_arterial_road = get_answer('average_width_of_arterial_road', fact)
						if average_width_of_arterial_road:
							ra_xml_dict['group_xy9hz30']['average_width_of_arterial_road'] = average_width_of_arterial_road
						
						point_of_vehicular_access_to_t = get_answer('point_of_vehicular_access_to_t', fact)
						if point_of_vehicular_access_to_t:
							ra_xml_dict['group_xy9hz30']['point_of_vehicular_access_to_t'] = point_of_vehicular_access_to_t
						
						is_the_settlement_below_or_abo = get_answer('is_the_settlement_below_or_abo', fact)
						if is_the_settlement_below_or_abo:
							ra_xml_dict['group_xy9hz30']['is_the_settlement_below_or_abo'] = is_the_settlement_below_or_abo
						
						are_the_huts_below_or_above_th = get_answer('are_the_huts_below_or_above_th', fact)
						if are_the_huts_below_or_above_th:
							ra_xml_dict['group_xy9hz30']['are_the_huts_below_or_above_th'] = are_the_huts_below_or_above_th
				
				ra_xml_dict['group_xy9hz30']['road_and_access_comment'] = get_answer('road_and_access_comment', fact)
				
				#print('process - Roads and Access Information')
				#write_log('process - Roads and Access Information')
				
				ra_xml_dict['__version__'] = xml_root_attr_version
				
				ra_xml_dict['meta']['instanceID'] = 'uuid:' + str(uuid.uuid4())
				
				
				# get xml string to store in xml file
				repeat_dict = {'group_te3dx03' : { 'append_index' : 1, 'list' : toilet_info}}
				xml_root_string = create_xml_string(ra_xml_dict, repeat_dict, xml_root, xml_root_attr_id, xml_root_attr_version)
				
				# create xml file
				file_name = 'RA_Survey_Slum_Id_' + str(slum)
				create_xml_file(xml_root_string, file_name, output_folder_path)
				
				success += 1
				
				del ra_xml_dict
			else:
				unprocess_slum += 1
				# write log that slum code is not found for slum id
				write_log('slum code is not found for slum id '+str(slum))
				unprocess_records[str(slum)] = 'slum code is not found when mapped'
			
			#print ('ra data - ', ra_xml_dict)
			#print ('ra toilate data - ', toilet_info)
			
			#break;
		except Exception as ex:
			exception_log = 'Exception occurred for slum id '+str(slum)+' \t  exception : '+ str(ex) +' \t  traceback : '+ traceback.format_exc()
			unprocess_records[str(slum)] = str(ex)
			
			fail += 1
			write_log(exception_log)
			
			#break;
			pass
		
		progess_counter += 1
		show_progress_bar(progess_counter, progress_max_count)
		
		
	if unprocess_records:
		write_log('List of slum for which unable to create xml')
		write_log('slum_id \t exception')
		for slum_id, error_msg in unprocess_records.items():
			write_log(slum_id+' \t\t'+error_msg)
		
	write_log('End : Log for RA Survey for each slum \n')
	print("End processing")
	
	set_process_slum_count(total_slum, unprocess_slum)
	set_process_count(total_process, success, fail)
	show_process_status()
	
	
	#name_mismatch_records_log = 'Name of surveyor not match -  \t '
	#name_mismatch_records_log += ' name_of_surveyor_s_who_checke : '+str(name_mismatch_records['name_of_surveyor_s_who_checke']['count']) + ' \t '
	#name_mismatch_records_log += ' name_of_surveyor_s_who_collec : '+str(name_mismatch_records['name_of_surveyor_s_who_collec']['count']) + ' \t '
	#name_mismatch_records_log += ' name_of_surveyor_s_who_took_t : '+str(name_mismatch_records['name_of_surveyor_s_who_took_t']['count']) + ' \t '
	#print(name_mismatch_records_log)
	#write_log(name_mismatch_records_log)
	
	return;



