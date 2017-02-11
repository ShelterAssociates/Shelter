#	Script written on Python 3.6
# 	Author : Parag Fulzele
#	Description : Main script to convert shelter old database data into XML files
#

import os
import sys

from common import *
from ra_survey import *
from rhs_survey import *
from ff_survey import *


city_option = {
	'1': 'Pune',
	'2': 'PCMC',
}

survey_type_option = {
	'1': 'Rapid Apprisal',
	'2': 'Rapid Household Apprisal',
	'3': 'Family Factsheet',
}

select_option = {
	'city': None,
	'survey_type': None,
}

city_mapping = {
	'1' : 4, # Pune
	'2' : 5, # PCMC
}

city_survey_mapping = {
	# Pune
	'1': {
		'1': 13, # RA
		'2': [46, 17], # RHS
		'3': 18, # FF
	},
	# PCMC
	'2': { 
		'1': 16, # RA
		'2': [36], # RHS
		'3': 35, # FF
	},
}

mapped_excel_path_mapping = {
	# Pune
	'1': {
		'1': os.path.join(root_folder_path, 'FilesToRead', 'MappedExcel_Pune', 'RA_Old_New_QuestionMapping_Parag.xlsx'), # RA
		'2': os.path.join(root_folder_path, 'FilesToRead', 'MappedExcel_Pune', 'RHS_Old_New_QuestionMapping_Parag.xlsx'), # RHS
		'3': os.path.join(root_folder_path, 'FilesToRead', 'MappedExcel_Pune', 'FF_Old_New_QuestionMapping_Parag.xlsx'), # FF
	},
	# PCMC
	'2': { 
		'1': os.path.join(root_folder_path, 'FilesToRead', 'MappedExcel_PCMC', 'RA_Old_New_QuestionMapping_Parag.xlsx'), # RA
		'2': os.path.join(root_folder_path, 'FilesToRead', 'MappedExcel_PCMC', 'RHS_Old_New_QuestionMapping_Parag.xlsx'), # RHS
		'3': os.path.join(root_folder_path, 'FilesToRead', 'MappedExcel_PCMC', 'FF_Old_New_QuestionMapping_Parag.xlsx'), # FF
	},
}

survey_xml_value_mapping = {
	# RA
	'1': {
		'xml_root': 'aLgeqjc9AzPHE2sDHuXqeH',
		'xml_root_attr_id': 'aLgeqjc9AzPHE2sDHuXqeH',
		'xml_root_attr_version': 'vqHbK4eJqHpdq4RodWyrvu',
		'formhub_uuid': 'c4b78cd3aa354882befb0919586c2096',
	},
	# RHS
	'2': { 
		'xml_root': 'agGEx5SL9H4QjcUp7FBF7z',
		'xml_root_attr_id': 'agGEx5SL9H4QjcUp7FBF7z',
		'xml_root_attr_version': 'vwu8oHVqQ9Ebzq9jJDyZER',
		'formhub_uuid': '4e443b93e589419f9463ee742c8cfe77',
	},
	# FF
	'3': { 
		'xml_root': 'aG7Ju4AGq5WfdMfNvGMypH',
		'xml_root_attr_id': 'aG7Ju4AGq5WfdMfNvGMypH',
		'xml_root_attr_version': 'vY9Bs39cHooJ3VeQQ9nLPQ',
		'formhub_uuid': 'cfad7aa6f505437bbd35b1b9a1c12dc0',
	},
}

def back_menu():
	choice = ''
	
	print('\n')
	print('b \t Back to survey type selection')
	print('n \t New migration')
	print('q \t Quit migration')
	print('\n')
	
	while choice != 'q':
		choice = input('Select option: ')

		if choice == 'b':
			select_option['survey_type'] = None
			choice = '2'
			break;
		elif choice == 'n':
			select_option['city'] = None
			select_option['survey_type'] = None
			choice = '1'
			break;
		elif choice == 'q':
			break;
		else:
			print('Invalid option.')
			
	return choice;

def display_menu(choice):
	if choice:
		if sys.platform == 'win32':
			os.system('cls')
		elif sys.platform == 'linux':
			os.system('clear')
	
	print('\nShelter Database migration to XML')
	
	city = select_option['city']
	survey_type = select_option['survey_type']
	
	if city:
		print('selected city: ', city_option[city])
	
	if survey_type:
		print('selected survey for : ', survey_type_option[survey_type])
	
	
		
	return choice;

def select_city():
	print("\n")
	
	for opt, city in city_option.items():
		print('%s \t %s' % (opt, city))
	print('q \t Quit Migration')
	print("\n")
	
	return_choice = ''
	choice = ''
	while choice != 'q':
		choice = input('Select city for migration: ')

		if choice in city_option.keys():
			select_option['city'] = choice
			return_choice = '2'
			break;
		elif choice == 'q':
			return_choice = 'q'
		else:
			print('Invalid city option.')
	
	return return_choice;

def select_survey_type():
	print("\n")
	
	for opt, survey in survey_type_option.items():
		print('%s \t %s' % (opt, survey))
	print('b \t Back to city selection')
	print("\n")
	
	return_choice = ''
	choice = ''
	while choice != 'q':
		choice = input('Select survey type for migration: ')

		if choice in survey_type_option.keys():
			select_option['survey_type'] = choice
			return_choice = '3'
			break;
		elif choice == 'b':
			select_option['city'] = None
			return_choice = '1'
			break;
		else:
			print('Invalid survey type option.')
	
	return return_choice;

def confirm_migration():
	print('\n')
	print('y \t Yes')
	print('n \t No')
	print('s \t Back to survey type selection')
	print('c \t Back to city selection')
	print('q \t Quit migration')
	print('\n')
	
	return_choice = ''
	choice = ''
	while choice != 'q':
		choice = input('Confirm migration: ')

		if choice == 'y':
			is_migrate = True
			return_choice = 'yb'
			break;
		elif choice == 'n':
			return_choice = 'nb'
			break;
		elif choice == 's':
			select_option['survey_type'] = None
			return_choice = '2'
			break;
		elif choice == 'c':
			select_option['city'] = None
			select_option['survey_type'] = None
			return_choice = '1'
			break;
		elif choice == 'q':
			return_choice = 'q'
			break;
		else:
			print('Invalid survey type option.')
	
	return return_choice;
	
def migrate():
	
	choice = confirm_migration()
	
	if choice == 'yb':
		display_menu('r')
		print('\nExecuting acutal migration program')
		city = select_option['city']
		survey = select_option['survey_type']
		
		if city:
			city_id = city_mapping[city]
			city_name = city_option[city]
		else:
			print('Cannot migrate data. Please contact administrator - city error')
		
		if city_id and survey:
			survey_map = city_survey_mapping[city]
			if survey == '2':
				survey_id = survey_map[survey][0]
				survey_id2 = survey_map[survey][1] if len(survey_map[survey]) == 2 else None
			else:
				survey_id = survey_map[survey]
				survey_id2 = None
			
			survey_name = survey_type_option[survey]
		else:
			print('Cannot migrate data. Please contact administrator - survey error')
		
		if city_id and survey_id:
			log_folder_path = os.path.join(root_folder_path, 'xml_output', city_name, 'log')
			
			mapped_excelFile = mapped_excel_path_mapping[city][survey]

			output_folder_path = os.path.join(root_folder_path, 'xml_output', city_name, survey_name)
			
			xml_root = survey_xml_value_mapping[survey]['xml_root']
			xml_root_attr_id = survey_xml_value_mapping[survey]['xml_root_attr_id']
			xml_root_attr_version = survey_xml_value_mapping[survey]['xml_root_attr_version']
			formhub_uuid = survey_xml_value_mapping[survey]['formhub_uuid']
			
			
			set_survey_log_path_option(log_folder_path)
			
			set_survey_option(city_id, survey_id, mapped_excelFile, output_folder_path, survey_id2)

			set_survey_xml_option(xml_root, xml_root_attr_id, xml_root_attr_version, formhub_uuid)
			
			#print(options_dict)
			
			if survey == '1':
				print('Generating xml for RA')
				create_ra_xml(options_dict)
			elif survey == '2':
				print('Generating xml for RHS')
				create_rhs_xml(options_dict)
			elif survey == '3':
				print('Generating xml for FF')
				create_ff_xml(options_dict)
			
			reset_survey_option()
			
			print('\nDone Migration of %s for %s city \n' % (survey_name, city_name))
	
	return choice;
	
def run_program():
	choice = ''
	is_migrate = False
	
	choice = display_menu('1')
	while choice != 'q':
		
		if choice == '1':
			choice = select_city()
		elif choice == '2':
			choice = select_survey_type()
		elif choice == '3':
			migreate_choice = migrate()
			if migreate_choice == 'yb':
				choice = back_menu()
			elif migreate_choice == 'nb':
				display_menu(choice)
				choice = back_menu()
			else:
				choice = migreate_choice
		else:
			print('Invalid option')
		
		if choice == 'q':
			select_option['city'] = None
			select_option['survey_type'] = None
			
		display_menu(choice)
		
		if choice == 'q':
			print('Program Terminated')

	return;

run_program()





