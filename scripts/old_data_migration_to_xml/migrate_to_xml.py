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
from kobotoolbox_upload import *


city_option = {
	'1': 'Pune',
	'2': 'PCMC',
}

survey_type_option = {
	'1': 'Rapid Infrastructure Mapping(RIM)',
	'2': 'Rapid Household Survey(RHS)',
	'3': 'Family Factsheet',
}

select_option = {
	'city': None,
	'survey_type': None,
	'action': None,
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
	# RA/RIM
	'1': {
		'xml_root': 'aQPuZBqwRijfvAwaStCxaB',
		'xml_root_attr_id': 'aQPuZBqwRijfvAwaStCxaB',
		'xml_root_attr_version': 'vFj7RvJEym3fLv6SXxRpob',
		'formhub_uuid': 'ea15aac487e7498e883a0447e0bce41c',
	},
	# RHS
	'2': { 
		'xml_root': 'a4K9qAQYGwsKxrpwvHuViw',
		'xml_root_attr_id': 'a4K9qAQYGwsKxrpwvHuViw',
		'xml_root_attr_version': 'vXS3hfQDM2CGiAZiFkupZQ',
		'formhub_uuid': 'd00bbe550e6f463dbb66730ed8b0b663',
	},
	# FF
	'3': { 
		'xml_root': 'arYdwNvdtxSQACTGudh8CH',
		'xml_root_attr_id': 'arYdwNvdtxSQACTGudh8CH',
		'xml_root_attr_version': 'v6eYZVeo6V3vqy6jhcDueQ',
		'formhub_uuid': '53d6a92a6af14094b24b25a3bc7d3861',
	},
}

survey_photo_mapping = {
	# List of key/xml element which has photo name
	'1': None, 	# RA
	'2': None, 	# RHS
	'3': ['Family_Photo', 'Toilet_Photo'],  # FF
}

root_output_folder = os.path.join(root_folder_path, 'xml_output')

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
	
	print('\n')
	print('Shelter Database migration to XML')
	print('\n')
	
	city = select_option['city']
	survey_type = select_option['survey_type']
	action = select_option['action']
	
	if action:
		if action == '1': # create xml
			print('selected action: Generate XML files')
		elif action == '2': # upload xml to kobo tool box
			print('selected action: Upload XML files to KoboToolBox')
		elif action == '3': # delete previously created xml 
			print('selected action: Delete existing XML files')
		
	if city:
		print('selected city: ', city_option[city])
	
	if survey_type:
		print('selected survey for : ', survey_type_option[survey_type])
	
	return choice;

def select_city(bmenu = True):
	print("\n")
	
	for opt, city in city_option.items():
		print('%s \t %s' % (opt, city))
	
	if bmenu:
		print('b \t Back to action selection')
		print('q \t Quit Program')
		
	print("\n")
	
	return_choice = ''
	choice = ''
	while choice != 'q':
		choice = input('Select city for migration: ')
		
		if choice in city_option.keys():
			select_option['city'] = choice
			return_choice = '2' # select survey type
			break;
		elif bmenu and choice == 'q':
			return_choice = 'q' # exit program 
			break;
		elif bmenu and choice == 'b':
			select_option['action'] = None
			return_choice = '3' # select action 
			break;
		else:
			print('Invalid city option.')
			choice = ''
	
	return return_choice;

def select_survey_type(bmenu = True):
	print("\n")
	
	for opt, survey in survey_type_option.items():
		print('%s \t %s' % (opt, survey))
	
	print('b \t Back to city selection')
	
	if bmenu:
		print('q \t Quit Program')
		
	print("\n")
	
	return_choice = ''
	choice = ''
	while choice != 'q':
		choice = input('Select survey type for migration: ')

		if choice in survey_type_option.keys():
			select_option['survey_type'] = choice
			
			if select_option['action'] == '1':
				return_choice = '4' # generate xml
			elif select_option['action'] == '2':
				return_choice = '5' # upload xml
			elif select_option['action'] == '3':
				return_choice = '6' # delete xml
			break;
			
		elif choice == 'b':
			select_option['city'] = None
			return_choice = '1' # select city 
			break;
			
		elif bmenu and choice == 'q':
			return_choice = 'q' # select city 
			break;
			
		else:
			print('Invalid survey type option.')
			choice = ''
	
	return return_choice;

def select_action():
	print('m \t Generate data into xml format')
	print('u \t Upload files into Kobo Tool Box')
	print('d \t Delete existing data from last action')
	print('q \t Quit migration')
	print('\n')
	
	return_choice = ''
	choice = ''
	while choice != 'q':
		choice = input('Confirm migration: ')

		if choice == 'm':
			select_option['action'] = '1'
			break;
			
		elif choice == 'u':
			select_option['action'] = '2' 
			break;
			
		elif choice == 'd':
			select_option['action'] = '3' 
			break;
			
		elif choice == 'q':
			return_choice = 'q' # exit program
			break;
		else:
			print('Invalid action option.')
	
	select_option['city'] = None
	select_option['survey_type'] = None
	
	if select_option['action'] == '3':
		return_choice = '6' # delete
	elif return_choice != 'q':
		return_choice = '1' # select city
	
	
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
			return_choice = 'yb' # start migration
			break;
		elif choice == 'n':
			return_choice = '3' # go to back menu
			break;
		elif choice == 's':
			select_option['survey_type'] = None
			return_choice = '2' # select survey type
			break;
		elif choice == 'c':
			select_option['city'] = None
			select_option['survey_type'] = None
			return_choice = '1' #select city 
			break;
		elif choice == 'q':
			return_choice = 'q' # exit program
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
			log_folder_path = os.path.join(root_output_folder, city_name, 'log')
			
			mapped_excelFile = mapped_excel_path_mapping[city][survey]

			output_folder_path = os.path.join(root_output_folder, city_name, survey_name)
			
			xml_root = survey_xml_value_mapping[survey]['xml_root']
			xml_root_attr_id = survey_xml_value_mapping[survey]['xml_root_attr_id']
			xml_root_attr_version = survey_xml_value_mapping[survey]['xml_root_attr_version']
			formhub_uuid = survey_xml_value_mapping[survey]['formhub_uuid']
			
			set_survey_log_path_option(log_folder_path)
			
			set_survey_option(city_id, survey_id, mapped_excelFile, survey_id2)

			set_survey_xml_option(xml_root, xml_root_attr_id, xml_root_attr_version, formhub_uuid)
			
			set_survey_output_path_option(output_folder_path)
			
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
	
def confirm_upload_xml():
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
		choice = input('Confirm upload: ')

		if choice == 'y':
			return_choice = 'yb' # start migration
			break;
		elif choice == 'n':
			return_choice = '3' # go to back menu
			break;
		elif choice == 's':
			select_option['survey_type'] = None
			return_choice = '2' # select survey type
			break;
		elif choice == 'c':
			select_option['city'] = None
			select_option['survey_type'] = None
			return_choice = '1' #select city 
			break;
		elif choice == 'q':
			return_choice = 'q' # exit program
			break;
		else:
			print('Invalid survey type option.')
	
	return return_choice;
	
def upload_xml():
	global survey_photo_mapping
	global select_option

	choice = confirm_upload_xml()
	
	if choice == 'yb':
		display_menu('r')
		print('\nExecuting acutal file upload program')
		city = select_option['city']
		survey = select_option['survey_type']
		
		if city and survey:
			city_name = city_option[city]
			survey_name = survey_type_option[survey]
			
			log_folder_path = os.path.join(root_output_folder, city_name, 'log')
			
			output_folder_path = os.path.join(root_output_folder, city_name, survey_name)
			
			set_survey_log_path_option(log_folder_path)
			
			set_survey_output_path_option(output_folder_path)
			
			upload_to_kobotoolbox(survey_photo_mapping, select_option)
			
			reset_survey_option()
			
			print('\nDone Migration upload of %s for %s city \n' % (survey_name, city_name))
		
	return choice;

def view_generated_data_list():
	result = True
	
	if os.path.exists(root_output_folder):
		for cid, city in city_option.items():
			if os.path.exists(os.path.join(root_output_folder, city)):
				survey_list = [];
				
				for sid, survey in survey_type_option.items():
					if os.path.exists(os.path.join(root_output_folder, city, survey)):
						survey_list.append(survey)
				
				if survey_list:
					print("Found following survey for '%s' city: " % city)
					for survey in survey_list:
						print("- ",survey)
					print("\n")
	else:
		result = False
		print("No data exists/generated.")
	
	
		
	return result;

def confirm_file_deletion():
	print('\n')
	print('y \t Yes')
	print('n \t No')
	print('b \t Back to action selection')
	print('q \t Quit migration')
	print('\n')
	
	return_choice = ''
	choice = ''
	while choice != 'q':
		choice = input('Confirm deletion : ')

		if choice == 'y':
			return_choice = 'yb' # start deletion
			break;
		elif choice == 'n':
			select_option['action'] = None
			select_option['city'] = None
			select_option['survey_type'] = None
			return_choice = '3' # go to back menu
			break;
		elif choice == 'b':
			select_option['action'] = None
			select_option['city'] = None
			select_option['survey_type'] = None
			return_choice = '3' # select action
			break;
		elif choice == 'q':
			return_choice = 'q' # exit program
			break;
		else:
			print('Invalid survey type option.')
	
	return return_choice;

def select_delete_option():
	choice = None
	# check if found existing records then ask for deletion
	if view_generated_data_list():
		print('a \t Delete All')
		print('c \t Delete for selected city')
		print('s \t Delete for selected survey')
		print('b \t Back to action selection')
		print('q \t Quit migration')
		print('\n')
		
		while choice != 'q':
			choice = input('Select deletion option: ')
		
			if choice == 'a':
				select_option['action'] = '3'
				break;
			elif choice == 'c':
				select_option['action'] = '3'
				
				display_menu('0')
				print("\nDelete existing data for selected city")
				
				if not select_option['city']:
					select_city(False)
				break;
			elif choice == 's':
				select_option['action'] = '3'
				
				display_menu('0')
				print("Delete existing data for selected city and survey")
				
				if not select_option['city']:
					select_city(False)
				
				display_menu('0')
				print("Delete existing data for selected city and survey")
				
				if not select_option['survey_type']:
					select_survey_type(False)
					
				break;
			elif choice == 'b':
				break;
			elif choice == 'q':
				break;
			else:
				print('Invalid deletion option.')
	else:
		choice = 'b'
		
	return choice;

def delete_existing_files():
	select_choice = ''
	
	while select_choice != 'q':
		select_choice = select_delete_option()
		
		if select_choice == 'b':
			choice = '3' # back to main menu selection
			break;
		elif select_choice == 'q':
			choice = 'q' # quit program
			break;
		elif select_choice in ['a', 'c', 's']:
			display_menu('0')
			
			if select_choice == 'a':
				print("\nDelete all existing data")
				
			confirm = confirm_file_deletion()
			
			display_menu('0')
			
			if confirm == 'yb':
				del_folder_path = ""
				
				city = select_option['city']
				survey_type = select_option['survey_type']
				
				if select_choice == 's':
					del_folder_path = os.path.join(root_output_folder, city_option[city], survey_type_option[survey_type])
				elif select_choice == 'c':
					del_folder_path = os.path.join(root_output_folder, city_option[city])
				else:
					del_folder_path = os.path.join(root_output_folder, 'temp')
					
				if del_folder_path:
					if select_choice != 'a':
						select_choice = ''
						
						if os.path.exists(del_folder_path):
							shutil.rmtree(del_folder_path, ignore_errors=True)
							choice = '3' # back to main menu selection
							break;
						else:
							print("\nData not found for selected option. Please select again\n")
							select_option['city'] = None
							select_option['survey_type'] = None
					elif select_choice == 'a':
						
						select_choice = ''
						
						city_name = ""
						for cid, city in city_option.items():
							del_folder_path = os.path.join(root_output_folder, city)
							
							if os.path.exists(del_folder_path):
								shutil.rmtree(del_folder_path, ignore_errors=True)
							else:
								city_name += city+', '
						
						if city_name:
							print("\nData not found for '%s' cites. Please select again\n" % city_name[:-2])
						else:
							choice = '3' # back to main menu selection
							break;
			else:
				select_choice = ''
		else:
			display_menu('0')
	
	select_option['city'] = None
	select_option['survey_type'] = None
	select_option['action'] = None
	
	return choice;


def run_program():
	choice = ''
	
	start_option = '3' # show selection menu
	
	# check if data exists for previous migration 
	for cid, city in city_option.items():
		del_folder_path = os.path.join(root_output_folder, city)
		
		if os.path.exists(del_folder_path):
			start_option = '6' # delete existing data first
			break;
	
	choice = display_menu(start_option)
	while choice != 'q':
		#print('choice --> ', choice)
		
		if choice == '1': # select city 
			choice = select_city()
			
		elif choice == '2': # select survey
			choice = select_survey_type()
			
		elif choice == '3': #select action
			choice = select_action()
			
		elif choice == '4': # migrate to xml
			migreate_choice = migrate()
			if migreate_choice == 'yb':
				choice = back_menu()
			#elif migreate_choice == 'nb':
			#	display_menu(choice)
			#	choice = back_menu()
			else:
				choice = migreate_choice
				
		elif choice == '5': # upload xml file
			upload_choice = upload_xml()
			if upload_choice == 'yb':
				choice = back_menu()
			else:
				choice = upload_choice
				
		elif choice == '6': # delete data
			delete_choice = delete_existing_files()
			if delete_choice == 'yb':
				choice = back_menu()
			else:
				choice = delete_choice
		else:
			print('Invalid option')
		
		if choice == 'q':
			select_option['city'] = None
			select_option['survey_type'] = None
			select_option['action'] = None
			
		display_menu(choice)
		
		if choice == 'q':
			print('Program Terminated')

	return;


if __name__ == "__main__":
	run_program()
	






