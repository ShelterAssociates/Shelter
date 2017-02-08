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

# upload xml to Kobo Tool Box 
def set_upload_xml_details(url, user, password):
	global xml_upload_details
	
	xml_upload_details['upload_url'] = url
	xml_upload_details['auth_user'] = user
	xml_upload_details['auth_password'] = password
	
	return;

def reset_upload_xml_details():
	global xml_upload_details
	
	xml_upload_details['upload_url'] = None
	xml_upload_details['auth_user'] = None
	xml_upload_details['auth_password'] = None
	
	return;

def upload_xml(xml_file):
	
	global xml_upload_details
	
	global process_file_count
	global success_file_upload_count
	global fail_file_upload_count
	
	url = xml_upload_details['upload_url']
	user = xml_upload_details['auth_user']
	password = xml_upload_details['auth_password']
	
	try:
		xml_upload_folder_path = os.path.dirname(xml_file)
		xml_file_name = os.path.basename(xml_file)
		
		print(process_file_count, ' path -> ', xml_upload_folder_path, '  file => ',xml_file_name)
		
		upload_file_handler = open(xml_file, 'rb')
			
		process_file_count += 1
		
		response_obj = None # requests.post(url, auth=(user, password), files={"xml_submission_file": upload_file_handler})
		
		if False:#response_obj.status_code == requests.codes.ok:
			success_file_upload_count += 1
		else:
			fail_file_upload_count += 1
			
			write_log(xml_upload_folder_path +' \t\t' + xml_file +' \t\t' + (response_obj.status_code if response_obj.status_code else "") +' \t\t\t' + (response_obj.text if response_obj.text else ""))
		
		upload_file_handler.close()
	except Exception as ex:
		exception_log = 'Exception occurred for uploading xml file \t  exception : '+ str(ex) +' \t  traceback : '+ traceback.format_exc()
		write_log(exception_log)
	
	return response_obj;

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
	
	set_upload_xml_details(url, user, password)
	
	# use threading to upload file faster
	pool_obj = Pool(processes=5)
	
	result = pool_obj.map(upload_xml, xml_file_list)
	
	pool_obj.close()
	pool_obj.join()
	
	reset_upload_xml_details()
	
	result_log = 'Total xml files to upload : '+str(upload_file_count) + ' \t process files : '+str(process_file_count) + ' \t fail to upload : '+str(fail_file_upload_count) + ' \t total success : '+str(success_file_upload_count)
	print(result_log)
	write_log(result_log)
	
	return;









