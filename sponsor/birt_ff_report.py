from .models import *
from component.cipher import *
from django.conf import settings
from datetime import datetime
import subprocess
import sys
import os
import shutil

ZIP_PATH='FFReport'
class FFReport(object):
    """Class to generate family factsheet report"""
    def __init__(self, record_id):
        self.project_detail = record_id

    def generate(self):
        cipher = AESCipher()
        obj_slum = self.project_detail.slum
        logged_sponsor = self.project_detail.sponsor_project.sponsor
        sponsored_household = self.project_detail.household_code
        rp_slum_code = str(obj_slum.shelter_slum_code)
        sub_folder = str(rp_slum_code)+str(len(sponsored_household)) + str(datetime.now())
        folder_name = os.path.join(settings.BASE_DIR, 'media', ZIP_PATH, str(logged_sponsor.organization_name))
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)
        folder_name = os.path.join(folder_name, sub_folder)
        if not os.path.exists(folder_name):
            os.mkdir(folder_name)

        execute_command = []
        for household_code in sponsored_household:
            key = cipher.encrypt(str(rp_slum_code) + '|' + str(household_code) + '|' + str(logged_sponsor.user.id))
            file = os.path.join(folder_name, "/household_code_" + str(household_code) + ".pdf")
            com = settings.BIRT_REPORT_CMD.format(file , key)
            execute_command.append(com)
            p = subprocess.Popen(com,#[sys.executable, os.path.join(settings.BASE_DIR, 'sponsor', 'birt_ff_report.py')],
                              					 stdout=subprocess.PIPE,
                              					 stderr=subprocess.STDOUT)
            p.communicate()
            print p.stderr.read()
        shutil.make_archive(folder_name, 'zip', os.path.join(folder_name,'..'))
        delete_command = "rm -rf " + folder_name
        os.system(delete_command)

        self.project_detail.objects.update(zip_file=folder_name+'.zip', zip_created_on=datetime.now())
