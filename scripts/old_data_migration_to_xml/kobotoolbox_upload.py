#	Script written on Python 3.6
# 	Author : Parag Fulzele
#	Description : Methods to upload xml to Kobo Tool Box
#

import traceback
from multiprocessing import Pool

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

def upload_xml(xml_file):
	
	global xml_upload_details
	
	global process_file_count
	global success_file_upload_count
	global fail_file_upload_count
	
	global kobotoolbox_url
	global kobotoolbox_user
	global kobotoolbox_password
	
	response_obj = None
	
	try:
		xml_upload_folder_path = os.path.dirname(xml_file)
		xml_file_name = os.path.basename(xml_file)
		
		#print(process_file_count, ' path -> ', xml_upload_folder_path, '  file => ',xml_file_name)
		#print(' url -> ', kobotoolbox_url, '  user => ', kobotoolbox_user, '  password => ', kobotoolbox_password)
		
		upload_file_handler = open(xml_file, 'rb')
			
		process_file_count += 1
		#print(process_file_count)
		
		response_obj = requests.post(kobotoolbox_url, auth=(kobotoolbox_user, kobotoolbox_password), files={"xml_submission_file": upload_file_handler})
		
		#print(xml_file_name, ' response_obj.response_obj.status_code -> ', response_obj.status_code, ' requests.codes.ok -> ', requests.codes.ok)
		
		if response_obj.status_code == 201: #success status
			success_file_upload_count += 1
		else:
			fail_file_upload_count += 1
			
			write_log(xml_upload_folder_path +' \t\t' + xml_file +' \t\t' + (str(response_obj.status_code) if response_obj.status_code else "") +' \t\t\t' + (response_obj.text if response_obj.text else ""))
		
		upload_file_handler.close()
	except Exception as ex:
		exception_log = 'Exception occurred for uploading xml file \t  exception : '+ str(ex) +' \t  traceback : '+ traceback.format_exc()
		write_log(exception_log)
	
	return response_obj

def upload_to_kobotoolbox(url, user, password):
	
	global process_file_count
	global success_file_upload_count
	global fail_file_upload_count
	
	xml_root_path = get_survey_option_output_path()
	
	xml_file_list = []
	
	# get list of xml files to upload with root folder path
	for dirpath, dirs, files in os.walk(xml_root_path):
		for filename in files:
			if filename.endswith('.xml'):
				xml_file_list.append(os.path.join(dirpath, filename))

	
	upload_file_count = len(xml_file_list)
	
	process_file_count = 0
	success_file_upload_count = 0
	fail_file_upload_count = 0
	
	#print('xml_file_list => ', xml_file_list)
	
	write_log('Start Uploading xml files to KoboToolBox')
	
	# use threading to upload file faster
	pool_obj = Pool(processes=5)
	
	response_obj = pool_obj.map(upload_xml, xml_file_list)
	
	pool_obj.close()
	pool_obj.join()
	
	write_log('Finish upload to KoboToolBox')
	#result_log = 'Total xml files to upload : '+str(upload_file_count) + ' \t process files : '+str(total_process)  + ' \t total success : '+str(total_success) + ' \t fail to upload : '+str(total_fail)
	#print(result_log)
	#write_log(result_log)
	
	return;









