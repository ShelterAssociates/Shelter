from django.conf import settings
import requests
import json
import subprocess
from django.http import HttpResponse
from graphs.models import *
from functools import wraps
from time import time
from datetime import timedelta
import dateutil.parser

direct_encountes =['Sanitation','Property tax','Water','Waste','Electricity','Daily Mobilization Activity']
program_encounters =['Daily Reporting','Family factsheet']

class avni_sync():
    def __init__(self):
        self.base_url = settings.AVNI_URL

    def timing(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start = time()
            result = f(*args, **kwargs)
            end = time()
            print('Elapsed time: {}'.format(end - start))
            return result
        return wrapper

    def get_cognito_details(self):
        cognito_details = requests.get(self.base_url+'cognito-details')
        cognito_details = json.loads(cognito_details.text)
        self.poolId = cognito_details['poolId']
        self.clientId = cognito_details['clientId']

    def get_cognito_token(self):
        self.get_cognito_details()
        command_data = subprocess.Popen(['node', 'graphs/avni/token.js',self.poolId, self.clientId, settings.AVNI_USERNAME, settings.AVNI_PASSWORD], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = command_data.communicate()
        self.token = stdout.decode("utf-8").replace('\n','')
        return self.token

    def lastModifiedDateTime(self):
        # get latest submission date from household table and pass it to url
        last_submission_date = HouseholdData.objects.latest('submission_date')
        latest_date = last_submission_date.submission_date + timedelta(days=5)
        iso_format_next = latest_date.strftime('%Y-%m-%dT00:00:00.000Z')
        return( iso_format_next )

    def create_final_rhs_data(self,a, b):
        change_keys = {'Enter_household_number_again': 'Househhold number',#'_notes': 'Note',
               'Name_s_of_the_surveyor_s': 'Name of the surveyor',
               'Household_number': 'First name',
               'group_el9cl08/Ownership_status_of_the_house': 'Ownership status of the house_1',
               'Date_of_survey': 'Date of Survey',
               'group_el9cl08/House_area_in_sq_ft':'House area in square feets.',
               'group_og5bx85/Full_name_of_the_head_of_the_household':'Full name of the head of the household',
               'group_el9cl08/Number_of_household_members':'Number of household members',
               'Type_of_unoccupied_house': 'Type of unoccupied house_1',
               'group_el9cl08/Type_of_structure_of_the_house': 'Type of structure of the house_1',
               'Parent_household_number': 'Parent household number',
               'Type_of_structure_occupancy': 'Type of structure occupancy_1',
               'group_el9cl08/Do_you_have_any_girl_child_chi':'Do you have any girl child/children under the age of 18?_'}
        a.update(b)
        for k, v in change_keys.items():
            if k in a.keys() and v in b.keys():
                a[k] = b[v]
                a.pop(v)
        return a

    def create_final_ff_data(self,a,b):
        change_keys = {
            "Note": 'Note',
            "group_im2th52/Number_of_Children_under_5_years_of_age": "Number of Children under 5 years of age",
            "group_ne3ao98/Cost_of_upgradation_in_Rs": 'Cost of upgradation',
            "group_oh4zf84/Duration_of_stay_in_settlement_in_Years": "Duration of stay in this current settlement (in Years)",
            "group_oh4zf84/Ownership_status": "Ownership status of the house_1",
            "group_im2th52/Number_of_earning_members": "Number of earning members",
            "group_im2th52/Occupation_s_of_earning_membe": "Occupation(s) of earning members",
            "Family_Photo": "Family Photo",
            "group_ne3ao98/Who_has_built_your_toilet": "Who has built your toilet ?",
            "group_im2th52/Approximate_monthly_family_income_in_Rs": "Approximate monthly family income (in Rs.)",
            "group_vq77l17/Household_number": "Househhold number",
            "group_im2th52/Total_family_members": "Total family members",
            "group_oh4zf84/Type_of_house": "Type of house*",
            "group_im2th52Number_of_members_over_60_years_of_age": "Number of members over 60 years of age",
            "group_ne3ao98/Where_the_individual_ilet_is_connected_to": "Where the individual toilet is connected ?",
            "group_vq77l17/Settlement_address": "Settlement address",
            "group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet": "Have you upgraded your toilet/bathroom/house while constructing individual toilet?",
            "group_im2th52/Number_of_disabled_members": "Number of Disabled members",
            "group_oh4zf84/Duration_of_stay_in_the_city_in_Years": "Duration of stay in the city (in Years)",
            "group_im2th52/Number_of_Male_members": "Number of Male members",
            "group_oh4zf84/Name_of_the_family_head": "Name of the family head",
            "Toilet_Photo": "Toilet Photo",
            "group_ne3ao98/Use_of_toilet": "Use of toilet",
            "group_im2th52/Number_of_Girl_children_between_0_18_yrs": "Number of Girl children between 0-18 yrs",
            "group_im2th52/Number_of_Female_members": "Number of Female members"
            }
        a.update(b)
        for k, v in change_keys.items():
            if k in a.keys() and v in b.keys():
                a[k]=b[v]
                a.pop(v)
        return a

    # def create_registrationdata_url(self):
    #     latest_date = self.lastModifiedDateTime()
    #     household_path = 'api/subjects?lastModifiedDateTime=' + latest_date + '&subjectType=Household'
    #     result = requests.get(self.base_url + household_path,headers= {'AUTH-TOKEN':self.get_cognito_token() })
    #     get_page_count = json.loads(result.text)['totalPages']
    #     return (get_page_count, household_path)

    def create_programEncounter_url(self):  #need to run for every program encounter type
        latest_date = self.lastModifiedDateTime()
        # programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' +latest_date +'&encounter%20type=Daily Mobilization Activity Encounter' #works
        # programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' +latest_date +'&encounter%20type=Family factsheet form' #works
        programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' +latest_date +'&encounter%20type=Family factsheet form'
        result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count, programEncounters_path)

    def saveDailyReportingData(self,data):
        pass

    def saveProgramEncounterData(self, encounter_ids,slum_name, city_name):
        for i in encounter_ids:
            send_request = requests.get(self.base_url + 'api/programEncounter/' + i,headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_data = json.loads(send_request.text)
            if 'Encounter type' in get_data.keys():
                if get_data['Encounter type'] == 'Family factsheet':
                    self.saveFamilyFactsheetData(get_data['observations'],slum_name)
                elif get_data['Encounter type'] == 'Daily Reporting':
                    self.saveDailyReportingData(get_data['observations'])
                else : pass

    def saveFamilyFactsheetData(self, data,slum_name):
        final_ff_data = {}
        HH = str(data["Househhold number"])
        try:
            slum = Slum.objects.filter(name= slum_name).values_list('id', 'electoral_ward_id__administrative_ward__city__id')[0]
            slum_id, city_id = slum[0],slum[1]
            check_record = HouseholdData.objects.filter(household_number=HH,city_id=city_id,slum_id=slum_id)
            if check_record:
                ff_data = check_record.values_list('ff_data',flat= True)[0]
                if ff_data == None or len(ff_data) == 0:
                    ff_data = {}
                final_ff_data = self.create_final_ff_data(ff_data,data)
                check_record.update(ff_data = final_ff_data )
                print('FF record updated for',slum_name, HH)
            else :
                print('record not found')
        except Exception as e:
            print(e,HH)

    # def saveEnrolmentData(self,id,household_number,slum_name):
    #     enrolementId, HH,slum = id,household_number,slum_name
    #     # if len(enrolment_id) > 0:
    #     #     for i in enrolment_id:
    #     send_request = requests.get(self.base_url + 'api/enrolment/' + 'c5835e47-964d-4929-9193-7bfff6df35c2' ,headers={'AUTH-TOKEN': self.get_cognito_token()})
    #     text = json.loads(send_request.text)
    #     program_encounter_ids = text['encounters']
    #     self.saveProgramEncounterData(program_encounter_ids,household_number,slum_name)

    def save_registrtation_data(self,HH_data):
        final_rhs_data ={}
        rhs_from_avni = HH_data['observations']
        household_number = str(int(rhs_from_avni['First name']))
        created_date = HH_data['Registration date']
        submission_date = (HH_data['audit']['Last modified at'])  # use last modf date
        slum_name = HH_data['location']['Slum']
        try:
            slum = Slum.objects.filter(name=slum_name).values_list('id','electoral_ward_id__administrative_ward__city__id')[0]
            slum_id, city_id = slum[0],slum[1]
            check_record = HouseholdData.objects.filter(household_number=household_number,city_id=city_id,slum_id=slum_id)
            rhs_data = check_record.values_list('rhs_data',flat=True)[0]
            if len(rhs_data) == 0:
                rhs_data ={}
            final_rhs_data = self.create_final_rhs_data(rhs_data, rhs_from_avni)
            check_record.update(submission_date=submission_date, rhs_data=final_rhs_data,
                                created_date=created_date)
            print('Household record updated for', slum_name, household_number)
        except Exception as e :
            rhs_data = {}
            final_rhs_data = self.create_final_rhs_data(rhs_data, rhs_from_avni)
            update_record = HouseholdData.objects.create(household_number=household_number, slum_id=slum_id,
            city_id=city_id, submission_date=submission_date,rhs_data=final_rhs_data, created_date=created_date)
            print('Household record created for', slum_name, household_number)
        except Exception as e:
            print('second exception',e)

    # def saveDirectEncountersData(self,encounter_ids):
    #     for k in encounter_ids:
    #         try:
    #             send_request1 = requests.get(self.base_url + 'api/encounter/' + k,headers={'AUTH-TOKEN': self.get_cognito_token()})
    #             # text1 = json.loads(send_request1.text)
    #         except Exception as e:
    #             print(e)
    #
    # def create_encounterData_url(self):  #need to run for every encounter type
    #     latest_date = self.lastModifiedDateTime()
    #     encounter_path = 'api/subjects?lastModifiedDateTime=' + latest_date +'&encounter%20type=Water'
    #     result = requests.get(self.base_url + encounter_path,
    #                           headers={'AUTH-TOKEN': self.get_cognito_token()})
    #     get_page_count = json.loads(result.text)['totalPages']
    #     return (get_page_count,encounter_path)
    #
    # def create_enrolmentData_url(self):  #need to run for every enrolment type
    #     latest_date = self.lastModifiedDateTime()
    #     # registration_with_id= 'api/subject/d65afb9f-d025-4982-af04-addbbee0216f' #(require uuid of any registration record)
    #     # programEncounter_with_id = 'api/programEncounter/' #(require uuid of any programEncounter record)
    #     # directEncounter_with_id = 'api/encounter/e92ec2d8-6e04-465d-80f1-f19bba4b7ee1' # (require uuid of any directEncounter record)
    #     # programEnrolment_with_id = 'api/enrolment/8' #(require uuid of any enrolment record)
    #     enrolments_path = 'api/enrolments?lastModifiedDateTime=' + latest_date +'&program=Property Tax' #works
    #     result = requests.get(self.base_url + enrolments_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
    #     get_page_count = json.loads(result.text)['totalPages']
    #     return (get_page_count, enrolments_path)
    @timing
    def access_program_encounter_data(self):
        totalPages, enc_path = self.create_programEncounter_url()
        for i in range(totalPages)[0:1]:
            send_request = requests.get(self.base_url + enc_path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
            data = json.loads(send_request.text)['content']
            for j in data:
                encounter_data = j['observations']
                enrolment_id = j['Enrolment ID']
                send_request1 = requests.get(self.base_url + 'api/enrolment/' + enrolment_id,headers={'AUTH-TOKEN': self.get_cognito_token()})
                text =  json.loads(send_request1.text)
                subject_id = text['Subject ID']
                encount_ids = text['encounters']
                send_request2 = requests.get(self.base_url + 'api/subject/' + subject_id ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                get_HH_data = json.loads(send_request2.text)
                self.save_registrtation_data(get_HH_data)
                self.saveProgramEncounterData(encount_ids, get_HH_data['location']['Slum'], get_HH_data['location']['City'])
