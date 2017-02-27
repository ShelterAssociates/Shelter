#	Script written on Python 3.6
# 	Author : Parag Fulzele
#	Description : Methods to upload xml to Kobo Tool Box
#

import traceback
from multiprocessing import Pool
import http.client

from common import *


# folder path where xml file are store for upload
xml_upload_folder_path = None

xml_upload_details = {
	'upload_url': None,
	'auth_user': None,
	'auth_password': None,
}

process_file_count = 0
success_file_upload_count = 0
fail_file_upload_count = 0

def upload_xml(upload_option):
	
	global xml_upload_details
	
	global process_file_count
	global success_file_upload_count
	global fail_file_upload_count
	
	global kobotoolbox_url
	global kobotoolbox_user
	global kobotoolbox_password
	
	response_obj = None
	
	xml_file = upload_option['xml_file']
	photo_dict = upload_option['xml_photo']
	
	try:
		xml_upload_folder_path = os.path.dirname(xml_file)
		xml_file_name = os.path.basename(xml_file)
		
		# set xml file to upload
		upload_files = {
			'xml_submission_file': (xml_file, open(xml_file, 'rb'), 'text/xml')
		}
		
		# add photos if exists for xml to upload
		if photo_dict:
			for key, val in photo_dict.items():
				file_ext = os.path.splitext(xml_file)[1].lower()
				upload_files[key] = (val, open(val, 'rb'), 'image')
		
		process_file_count += 1
		#print(process_file_count)
		
		#print(process_file_count, '  file => ',xml_file_name, '  upload_files => ',upload_files)
		
		response_obj = requests.post(kobotoolbox_url, auth=(kobotoolbox_user, kobotoolbox_password), files = upload_files)
		
		#print('after process ', xml_file_name, ' response_obj.response_obj.status_code -> ', response_obj.status_code, ' response_obj.text -> ', response_obj.text)
		#write_log(xml_upload_folder_path +' \t\t status code= ' + str(response_obj.status_code) +' \t\t\t response text= ' + response_obj.text)
		
		if response_obj.status_code == 201: #success status
			success_file_upload_count += 1
		else:
			fail_file_upload_count += 1
			
			write_log(xml_upload_folder_path +' \t\t status code= ' + str(response_obj.status_code) +' \t\t\t response text= ' + response_obj.text)
		
	except Exception as ex:
		exception_log = 'Exception occurred for uploading xml file \t  exception : '+ str(ex) +' \t  traceback : '+ traceback.format_exc()
		write_log(exception_log)
	
	return response_obj

def upload_to_kobotoolbox(survey_photo_mapping, select_option):
	
	global process_file_count
	global success_file_upload_count
	global fail_file_upload_count
	
	xml_root_path = get_survey_option_output_path()
	
	upload_option = []
	
	xml_photo_element_name = survey_photo_mapping[select_option['survey_type']]
	
	# get list of xml files to upload with root folder path
	for dirpath, dirs, files in os.walk(xml_root_path):
		for filename in files:
			if filename.endswith('.xml'):
				upload_option.append({
					'xml_file': os.path.join(dirpath, filename),
					'xml_photo': get_xml_photo_value(dirpath, filename, xml_photo_element_name),
				})
	
	upload_file_count = len(upload_option)
	
	process_file_count = 0
	success_file_upload_count = 0
	fail_file_upload_count = 0
	
	#print('upload_option => ', upload_option)
	print('Start Uploading xml files to KoboToolBox')
	write_log('Start Uploading xml files to KoboToolBox')
	
	
	# use threading to upload file faster
	pool_obj = Pool(processes=5)
	
	response_obj = pool_obj.map(upload_xml, upload_option)
	
	pool_obj.close()
	pool_obj.join()
	
	
	print('Finish upload to KoboToolBox')
	write_log('Finish upload to KoboToolBox')
	#result_log = 'Total xml files to upload : '+str(upload_file_count) + ' \t process files : '+str(total_process)  + ' \t total success : '+str(total_success) + ' \t fail to upload : '+str(total_fail)
	#print(result_log)
	#write_log(result_log)
	
	return;









