#	Script written on Python 3.6
# 	Author : Parag Fulzele
#	Description : Methods to convert FF survey into xml
#

import uuid
import traceback
import copy

from common import *

# dictionary use to set and export data into xml
gl_ff_xml_dict = {
	'formhub' : {
		'uuid' : None
	},
	'group_vq77l17' : {
		'city' : None,
		'admin_ward' : None,
		'slum_name' : None,
		'Settlement_address' : None,
		'Household_number' : None
	},
	'group_oh4zf84' : {
		'Name_of_the_family_head' : None,
		'Name_of_Native_villa_district_and_state' : None,
		'Duration_of_stay_in_the_city' : None,
		'Duration_of_stay_in_s_current_settlement' : None,
		'Type_of_house' : None,
		'Ownership_status' : None
	},
	'group_im2th52' : {
		'Total_family_members' : None,
		'Number_of_Male_members' : None,
		'Number_of_Female_members' : None,
		'Number_of_Children_under_5_years_of_age' : None,
		'Number_of_members_over_60_years_of_age' : None,
		'Number_of_Girl_children_between_0_18_yrs' : None,
		'Number_of_disabled_members' : None,
		'If_yes_specify_type_of_disability' : None,
		'Number_of_earning_members' : None,
		'Occupation_s_of_earning_membe': None,
		'Occupation_s_of_earning_members' : None,
		'Approximate_monthly_family_income' : None
	},
	'group_ne3ao98' : {
		'Where_the_individual_ilet_is_connected_to' : None,
		'Who_has_built_your_toilet' : None,
		'Have_you_upgraded_yo_ng_individual_toilet' : None,
		'Cost_of_upgradation' : None,
		'Use_of_toilet' : None
	},
	'Note' : None,
	'Family_Photo' : None,
	'Toilet_Photo' : None,
	'__version__' : None,
	'meta' : {
		'instanceID' : None
	}
}

## FF survey queries
# get list of all household in all slums for survey
qry_ff_slum_household_survey_list = "select distinct household.slum_id, household.household_code from survey_fact f \
join slum_data_household household on household.id = f.object_id \
join survey_survey s on s.id = f.survey_id join survey_project p on p.id = s.project_id \
where s.id = %s and p.id = %s and f.content_type_id = 27 \
order by household.slum_id, household.household_code asc"

# get list of all question and answer for all household in slum
qry_ff_survey_slum_household_question_answer = "(select household1.household_code, '-1' as question_id, to_char(min(f1.updated_on),'YYYY-MM-DD\"T\"HH24:MI:SS.MS+05:30') as answer from survey_fact f1 \
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

# get list of option to set as text instead of option
qry_fact_option_text_list = "select code, description from survey_factoption where desired_fact_id=%s order by code asc"

# path of survey excel file(xls) to read option and xml keys
FF_excelFile = os.path.join(root_folder_path, 'FilesToRead', 'FF.xls')

# create family factsheet survey xml
def create_ff_xml(options):
	# variables
	global question_map_dict
	global question_option_map_dict
	global option_dict
	
	global city_ward_slum_dict
	
	global qry_slum_list
	global qry_ff_slum_household_survey_list
	global qry_ff_survey_slum_household_question_answer
	
	global qry_fact_option_text_list
	
	global gl_ff_xml_dict
	
	global FF_excelFile;
	
	xml_root = options['xml_root']
	xml_root_attr_id = options['xml_root_attr_id']
	xml_root_attr_version = options['xml_root_attr_version']
	xml_formhub_uuid = options['formhub_uuid']
	
	project_id = options['project']
	survey_id = options['survey']
	mapexcelfile = options['mapped_excelFile']
	output_folder_path = options['output_path']
	
	unprocess_records = {}
	
	write_log("Start : Log for FF Survey for per household in each slum ")
	
	#read old xls file city - ward - slum mapping
	read_xml_excel(FF_excelFile)
	#print("Read excel file")
	write_log("Read excel file " + FF_excelFile)
	
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
	
	# get slum and household list
	slum_household_list = get_household_survey(qry_ff_slum_household_survey_list % (survey_id, project_id))
	#print("fetch slum household list")
	#print(new_slum_household_list)
	write_log("fetch household slum survey list")
	
	# get list of option to set as text into xml
	occupation_option_list = get_question_answer(qry_fact_option_text_list % 434)
	disability_option_list = get_question_answer(qry_fact_option_text_list % 432)
	
	#print(occupation_option_list)
	#print(disability_option_list)
	
	fail = 0
	success = 0
	total_process_house = 0
	
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
			
			# get question and answer for households in slum
			household_fact = get_household_wise_question_answer(qry_ff_survey_slum_household_question_answer % (survey_id, project_id, slum, survey_id, project_id, slum))
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
					ff_xml_dict = copy.deepcopy(gl_ff_xml_dict)
					
					# set dictionary to create RHS xml
					ff_xml_dict['formhub']['uuid'] = xml_formhub_uuid
					
					#Slum Information
					ff_xml_dict['group_vq77l17']['city'] = city
					ff_xml_dict['group_vq77l17']['admin_ward'] = admin_ward
					ff_xml_dict['group_vq77l17']['slum_name'] = slum_code
					ff_xml_dict['group_vq77l17']['Settlement_address'] = get_answer('Settlement_address', fact)
					
					Household_number = get_answer('Household_number', fact)
					try:
						ff_xml_dict['group_vq77l17']['Household_number'] = int(Household_number)
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process house number for answer =>"+(Household_number if not isinstance(Household_number, list) else ','.join(Household_number))])
						pass
					
					#print('process - Slum Information')
					#write_log('process - Slum Information')
					
					#Family Information
					ff_xml_dict['group_oh4zf84']['Name_of_the_family_head'] = get_answer('Name_of_the_family_head', fact)
					ff_xml_dict['group_oh4zf84']['Name_of_Native_villa_district_and_state'] = get_answer('Name_of_Native_villa_district_and_state', fact)
					ff_xml_dict['group_oh4zf84']['Duration_of_stay_in_the_city'] = get_answer('Duration_of_stay_in_the_city', fact)
					ff_xml_dict['group_oh4zf84']['Duration_of_stay_in_s_current_settlement'] = get_answer('Duration_of_stay_in_s_current_settlement', fact)
					
					Type_of_house = get_answer('Type_of_house', fact)
					if Type_of_house:
						ff_xml_dict['group_oh4zf84']['Type_of_house'] = Type_of_house
					
					Ownership_status = get_answer('Ownership_status', fact)
					if Ownership_status:
						ff_xml_dict['group_oh4zf84']['Ownership_status'] = Ownership_status
					
					#print('process - Family Information')
					#write_log('process - Family Information')
					
					#Family Members Information
					Total_family_members = get_answer('Total_family_members', fact)
					try:
						ff_xml_dict['group_im2th52']['Total_family_members'] = int(Total_family_members)
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process number of male member for answer =>"+(Total_family_members if Total_family_members else 'NoneTYpe')])
						pass
					
					Number_of_Male_members = get_answer('Number_of_Male_members', fact)
					try:
						ff_xml_dict['group_im2th52']['Number_of_Male_members'] = int(Number_of_Male_members)
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process number of male member for answer =>"+(Number_of_Male_members if Number_of_Male_members else 'NoneTYpe')])
						pass
					
					Number_of_Female_members = get_answer('Number_of_Female_members', fact)
					try:
						ff_xml_dict['group_im2th52']['Number_of_Female_members'] = int(Number_of_Female_members)
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process number of male member for answer =>"+(Number_of_Female_members if Number_of_Female_members else 'NoneTYpe')])
						pass
					
					Number_of_Children_under_5_years_of_age = get_answer('Number_of_Children_under_5_years_of_age', fact)
					try:
						ff_xml_dict['group_im2th52']['Number_of_Children_under_5_years_of_age'] = int(Number_of_Children_under_5_years_of_age)
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process number of children under 5 years of age for answer =>"+(Number_of_Children_under_5_years_of_age)])
						pass
					
					Number_of_members_over_60_years_of_age = get_answer('Number_of_members_over_60_years_of_age', fact)
					try:
						ff_xml_dict['group_im2th52']['Number_of_members_over_60_years_of_age'] = int(Number_of_members_over_60_years_of_age)
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process number of member over 60 years of age for answer =>"+(Number_of_members_over_60_years_of_age)])
						pass
					
					Number_of_Girl_children_between_0_18_yrs = get_answer('Number_of_Girl_children_between_0_18_yrs', fact)
					try:
						ff_xml_dict['group_im2th52']['Number_of_Girl_children_between_0_18_yrs'] = int(Number_of_Girl_children_between_0_18_yrs)
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process number of girl children between 0-18 of age for answer =>"+(Number_of_Girl_children_between_0_18_yrs if Number_of_Girl_children_between_0_18_yrs else 'NoneTYpe')])
						pass
					
					Number_of_disabled_members = get_answer('Number_of_disabled_members', fact)
					try:
						ff_xml_dict['group_im2th52']['Number_of_disabled_members'] = int(Number_of_disabled_members)
						
						if Number_of_disabled_members > 0:
							ff_xml_dict['group_im2th52']['If_yes_specify_type_of_disability'] = get_option_text(disability_option_list, get_answer('If_yes_specify_type_of_disability', fact))
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process number of disable member for answer =>"+(Number_of_disabled_members if Number_of_disabled_members else 'NoneTYpe')])
						pass
					
					Number_of_earning_members = get_answer('Number_of_earning_members', fact)
					try:
						ff_xml_dict['group_im2th52']['Number_of_earning_members'] = int(Number_of_earning_members)
					except:
						#unprocess_records[str(slum)].append([str(household), "unable to process number of disable member for answer =>"+(Number_of_earning_members if Number_of_earning_members else 'NoneTYpe')])
						pass
					
					ff_xml_dict['group_im2th52']['Occupation_s_of_earning_membe'] = get_answer('Occupation_s_of_earning_membe', fact)
					
					ff_xml_dict['group_im2th52']['Approximate_monthly_family_income'] = get_answer('Approximate_monthly_family_income', fact)
					
					#print('process - Family Members Information')
					#write_log('process - Family Members Information')
					
					#Toilet Information
					Where_the_individual_ilet_is_connected_to = get_answer('Where_the_individual_ilet_is_connected_to', fact)
					if Where_the_individual_ilet_is_connected_to:
						ff_xml_dict['group_ne3ao98']['Where_the_individual_ilet_is_connected_to'] = Where_the_individual_ilet_is_connected_to
					
					Who_has_built_your_toilet = get_answer('Who_has_built_your_toilet', fact)
					if Who_has_built_your_toilet:
						ff_xml_dict['group_ne3ao98']['Who_has_built_your_toilet'] = Who_has_built_your_toilet
					
					Have_you_upgraded_yo_ng_individual_toilet = get_answer('Have_you_upgraded_yo_ng_individual_toilet', fact)
					if Have_you_upgraded_yo_ng_individual_toilet:
						ff_xml_dict['group_ne3ao98']['Have_you_upgraded_yo_ng_individual_toilet'] = Have_you_upgraded_yo_ng_individual_toilet
					
					ff_xml_dict['group_ne3ao98']['Cost_of_upgradation'] = get_answer('Cost_of_upgradation', fact)
					
					Use_of_toilet = get_answer('Use_of_toilet', fact)
					if Use_of_toilet:
						ff_xml_dict['group_ne3ao98']['Use_of_toilet'] = Use_of_toilet
					
					#print('process - Toilet Information')
					#write_log('process - Toilet Information')
					
					ff_xml_dict['Note'] = get_answer('Note', fact)
					ff_xml_dict['Family_Photo'] = None #get_answer('Family_Photo', fact)
					ff_xml_dict['Toilet_Photo'] = None #get_answer('Toilet_Photo', fact)
					
					ff_xml_dict['__version__'] = xml_root_attr_version
					
					ff_xml_dict['meta']['instanceID'] = 'uuid:' + str(uuid.uuid4())
					
					
					# get xml string to store in xml file
					repeat_dict = {}
					xml_root_string = create_xml_string(ff_xml_dict, repeat_dict, xml_root, xml_root_attr_id, xml_root_attr_version)
					
					# create xml file
					file_name = 'FF_Survey_Slum_Id_' + str(slum) + '_House_code_' + household
					
					final_output_folder_path = os.path.join(output_folder_path, "slum_" +str(slum))
					
					create_xml_file(xml_root_string, file_name, final_output_folder_path)
					
					success += 1
						
					#print ('ff data - ', ff_xml_dict)
					
					del ff_xml_dict
					
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

		
	if unprocess_records:
		write_log('List of slum and household for which unable to create xml')
		write_log('slum_id \t household_code \t exception')
		for slum_id, error_lst in unprocess_records.items():
			for error in error_lst:
				#print('error ', error[0], '    msg ',error[1])
				write_log(slum_id+' \t\t' + (error[0]+' \t' if error[0] else ' \t\t') +' \t\t\t' + error[1])
		
	write_log('End : Log for FF Survey for slum \n')
	print("End processing")
	
	total_slum = len(slum_household_list)
	total_house = sum(len(v1) for v1 in iter(slum_household_list.values()))
		
	result_log = 'total slum records : '+str(total_slum) +'\t total house records in all slum : '+str(total_house)
	print(result_log)
	write_log(result_log)
	
	result_log2 = 'process house records in all slum : '+str(total_process_house) + ' \t fail to process : '+str(fail) + ' \t success : '+str(success)	
	print(result_log2)
	write_log(result_log2)
	
	return;



