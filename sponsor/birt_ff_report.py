from component.cipher import *
from django.conf import settings
from datetime import datetime
import subprocess
import sys
import os
import shutil
from multiprocessing import Pool
#import datetime
from concurrent import futures

ZIP_PATH='FFReport'
def report_exec(cmd):
    try:
        pass#os.system(cmd)
    except Exception as e:
        print e
    p = subprocess.Popen(cmd, shell = True,#[sys.executable, os.path.join(settings.BASE_DIR, 'sponsor', 'birt_ff_report.py')],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    x,y = p.communicate()
    return (x,y)

class FFReport(object):
    """Class to generate family factsheet report"""
    def __init__(self, record_id):
        self.project_detail = record_id

    #def report_exec(self, cmd):
    #	os.system(cmd)

    def generate(self):
        cipher = AESCipher()
        obj_slum = self.project_detail.sponsor_project_details.slum
        logged_sponsor = self.project_detail.sponsor_project_details.sponsor_project.sponsor
        sponsored_household = self.project_detail.household_code
        rp_slum_code = str(obj_slum.shelter_slum_code)
        sub_folder = (str(rp_slum_code)+str(len(sponsored_household)) + str(datetime.now())).replace(' ','_')
        folder_name = os.path.join(settings.BASE_DIR, 'media', ZIP_PATH, str(logged_sponsor.organization_name).replace(' ', '_'))
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        folder_name = os.path.join(folder_name, sub_folder)
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        execute_command = []
        for household_code in sponsored_household:
            key = cipher.encrypt(str(rp_slum_code) + '|' + str(household_code) + '|' + str(logged_sponsor.user.id))
            file = os.path.join(folder_name, "household_code_" + str(household_code) + ".pdf")
            com = settings.BIRT_REPORT_CMD.format(file , key)
            #print com
            execute_command.append(com)
            #p = subprocess.Popen(com, shell = True,#[sys.executable, os.path.join(settings.BASE_DIR, 'sponsor', 'birt_ff_report.py')],
            #                                stdout=subprocess.PIPE,
            #                                stderr=subprocess.PIPE)
            #x,y = p.communicate()

            #print x,y
            #os.system(com)
        #print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
	try:
	    with futures.ThreadPoolExecutor(max_workers=3) as pool:
                pool.map(report_exec, execute_command)
            #p = Pool(2)
	    #p.map(report_exec, execute_command)
	    #p.close()
	    #p.join()
	except Exception as e:
            print e
        #print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        shutil.make_archive(folder_name, 'zip',folder_name)
        delete_command = "rm -rf " + folder_name
        os.system(delete_command)

        if self.project_detail.zip_file:
            storage, path = self.project_detail.zip_file.storage, self.project_detail.zip_file.path
            storage.delete(path)

        #self.project_detail.zip_file=os.path.join('media', ZIP_PATH, str(logged_sponsor.organization_name).replace(' ','_'),sub_folder+'.zip')
        #self.project_detail.zip_created_on=datetime.now()
        self.project_detail.__class__.objects.filter(pk=self.project_detail.id).update(zip_created_on=datetime.now(),zip_file=os.path.join( ZIP_PATH, str(logged_sponsor.organization_name).replace(' ','_'),sub_folder+'.zip'))
