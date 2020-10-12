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

direct_encountes =['Sanitation','Property tax','Water','Waste','Electricity'] #,'Daily Mobilization Activity']
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
        latest_date = last_submission_date.submission_date + timedelta(days=1)
        iso_format_next = latest_date.strftime('%Y-%m-%dT00:00:00.000Z')
        return( iso_format_next )

    def create_final_rhs_data(self,a,b):
        change_keys = {'Enter_household_number_again': 'Househhold number',#'_notes': 'Note',
               'Name_s_of_the_surveyor_s': 'Name of the surveyor',
               'Household_number': 'First name',
               'group_el9cl08/Aadhar_number':'Aadhar number',
               'group_el9cl08/Enter_the_10_digit_mobile_number':'Enter the 10 digit mobile number',
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
            if k in a.keys() or v in b.keys():
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
            if k in a.keys() or v in b.keys():
                a[k]=b[v]
                a.pop(v)
        occupation = a['group_im2th52/Occupation_s_of_earning_membe']
        if type(occupation) == list:
            occupation_str = ','.join(i for i in occupation)
        elif type(occupation) == str :
            occupation_str =occupation.replace(',','')
        else : pass
        a['group_im2th52/Occupation_s_of_earning_membe'] = occupation_str
        return a

    def map_sanitation_keys(self,s):
        map_toilet_keys = {'group_oi8ts04/Have_you_applied_for_individua': 'Have you applied for an individual toilet under SBM?_1',
            'group_oi8ts04/Status_of_toilet_under_SBM': 'Status of toilet under SBM ?',
            'group_oi8ts04/What_is_the_toilet_connected_to': 'Where the individual toilet is connected to ?',
            'group_oi8ts04/Who_all_use_toilets_in_the_hou': 'Who all use toilets in the household ?',
            'group_oi8ts04/What_was_the_cost_in_to_build_the_toilet': 'What was the cost incurred to build the toilet?',
            'group_oi8ts04/Type_of_SBM_toilets': 'Type of SBM toilets ?',
            'group_oi8ts04/Reason_for_not_using_toilet': 'Reason for not using toilet ?',
            'group_oi8ts04/How_many_installments_have_you': 'How many installments have you received ?',
            'group_oi8ts04/When_did_you_receive_ur_first_installment': 'When did you receive your first SBM installment?',
            'group_oi8ts04/When_did_you_receive_r_second_installment': 'When did you receive your second SBM installment?',
            'group_oi8ts04/When_did_you_receive_ur_third_installment': 'When did you receive your third SBM installment?',
            'group_oi8ts04/If_built_by_contract_ow_satisfied_are_you': 'If built by contractor, how satisfied are you?',
            'group_oi8ts04/OD1': 'Does any member of the household go for open defecation ?',
            'group_oi8ts04/Current_place_of_defecation': 'Final current place of defecation',
            'group_oi8ts04/Is_there_availabilit_onnect_to_the_toilet': 'Is there availability of drainage to connect it to the toilet?',
            'group_oi8ts04/Are_you_interested_in_an_indiv': 'Are you interested in an individual toilet ?',
            'group_oi8ts04/What_kind_of_toilet_would_you_like': 'What kind of toilet would you like ?',
            'group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built': 'Under what scheme would you like your toilet to be built ?',
            'group_oi8ts04/If_yes_why': 'If yes for individual toilet , why?',
            'group_oi8ts04/If_no_why': 'If no for individual toilet , why?',
            'group_el9cl08/Does_any_household_m_n_skills_given_below': 'Does any household member have any of the construction skills given below ?'}
        a ={}
        a.update(s)
        for k, v in map_toilet_keys.items():
            if k in a.keys() or v in s.keys():
                a[k] = s[v]
                a.pop(v)
        a.pop('Current place of defecation') if 'Current place of defecation' in a else None
        return a

    def map_water_keys(self,w):
        map_water_keys ={'group_el9cl08/Type_of_water_connection':'Type of water connection ?'}
        a = {}
        a.update(w)
        for k, v in map_water_keys.items():
            if k in a.keys() or v in w.keys():
                a[k] = w[v]
                a.pop(v)
        return a

    def map_waste_keys(self,ws):
        map_waste_keys = {'group_el9cl08/Facility_of_solid_waste_collection':'How do you dispose your solid waste ?'}
        a = {}
        a.update(ws)
        for k, v in map_waste_keys.items():
            if k in a.keys() or v in ws.keys():
                a[k] = ws[v]
                a.pop(v)
        return a

    def create_registrationdata_url(self):
        latest_date = self.lastModifiedDateTime()
        household_path = 'api/subjects?lastModifiedDateTime=' + latest_date  + '&subjectType=Household'
        result = requests.get(self.base_url + household_path,headers= {'AUTH-TOKEN':self.get_cognito_token() })
        get_text = json.loads(result.text)['content']
        pages =  json.loads(result.text)['totalPages']
        return (pages,get_text)

    # def get_registration_data(self):
    #     pages ,data = self.create_registrationdata_url()
    #     for i in data[2:3]:
    #         # self.save_registrtation_data(i)
    #         slum_name = i['location']['Slum']
    #         Household_number = i['observations']['First name']
    #         Encounter_ids = i['encounters']
    #         self.saveDirectEncounterData(Encounter_ids,Household_number,slum_name)

    # def saveDirectEncounterData(self,Encounter_ids):
    #     for id in Encounter_ids:
    #         send_request = requests.get(self.base_url + 'api/encounter/' + id,headers={'AUTH-TOKEN': self.get_cognito_token()})
    #         text = json.loads(send_request.text)
    #         Encounter_type = text['Encounter type']
    #         encounter_data = text['observations']
    #         last_modified_data = text['audit']['Last modified at']
    #         if Encounter_type == 'Sanitation':
    #             # toilet_data = {'Toilet': }
    #             new_dict = self.map_sanitation_keys(encounter_data)
    #         else:pass

    def create_programEncounter_url(self):
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' +latest_date+'&encounterType=Family factsheet'
        result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count, programEncounters_path)

    def create_directEncounter_url(self):  #need to run for every program encounter type
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes[0:1]:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date  +'&encounterType='+ i #'2020-08-25T00:00:00.000Z'
            result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return(get_page_count, programEncounters_path)

    def update_rhs_data(self,sub_id,data):
        send_request = requests.get(self.base_url + 'api/subject/' + sub_id, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_HH_data = json.loads(send_request.text)
        slum = get_HH_data['location']['Slum']
        HH = str(int(get_HH_data['observations']['First name']))
        try:
            get_record = HouseholdData.objects.filter(slum_id__name =slum,household_number =HH)
            if not get_record:
                self.save_registrtation_data(get_HH_data)
            get_rhs_data = get_record.values_list('rhs_data', flat=True)[0]
            get_rhs_data.update(data)
            get_record.update(rhs_data = get_rhs_data)
            print('record updated for', HH)
        except Exception as e:
            print(e, HH)

    def get_direct_encounter_data(self):  # use this function when using direct encounter data(check encound id and subject id is not same in data fetched)
        pages,path = self.create_directEncounter_url()
        for i in range(pages)[0:1]:
            send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
            data = json.loads(send_request.text)['content']
            for j in data[0:1]:
                if j['Encounter type'] in [ 'Property tax' , 'Electricity']:
                    j['observations'].update({'Last_modified_date': j['audit']['Last modified at']})
                    self.update_rhs_data(j['Subject ID'], j['observations'])
                waste_data = self.map_waste_keys(j['observations'])
                waste_data.update({'Last_modified_date': j['audit']['Last modified at']})
                self.update_rhs_data(j['Subject ID'], waste_data)
                water_data = self.map_water_keys(j['observations'])
                water_data.update({'Last_modified_date':j['audit']['Last modified at']})
                self.update_rhs_data( j['Subject ID'],water_data)
                sanitation_data = self.map_sanitation_keys(j['observations'])
                sanitation_data.update({'Last_modified_date':j['audit']['Last modified at']})
                self.update_rhs_data( j['Subject ID'],sanitation_data)

    def saveDailyReportingData(self,data,slum_name):
        pass

    def saveFamilyFactsheetData(self,avni_ff_data,slum_name):
        # final_ff_data = {}
        HH = str(avni_ff_data["Househhold number"])
        try:
            slum = Slum.objects.filter(name= slum_name).values_list('id', 'electoral_ward_id__administrative_ward__city__id')[0]
            slum_id, city_id = slum[0],slum[1]
            check_record = HouseholdData.objects.filter(household_number = HH,city_id=city_id,slum_id=slum_id)
            if check_record:
                ff_data = check_record.values_list('ff_data',flat= True)[0]
                if ff_data == None or len(ff_data) == 0:
                    ff_data = {}
                final_ff_data = self.create_final_ff_data(ff_data,avni_ff_data)
                check_record.update(ff_data = final_ff_data )
                print('FF record updated for',slum_name, HH)
            else :
                ff_data = {}
                enrolment_id = avni_ff_data['Enrolment ID']
                send_request1 = requests.get(self.base_url + 'api/enrolment/' + enrolment_id,headers={'AUTH-TOKEN': self.get_cognito_token()})
                RHS = json.loads(send_request1.text)
                subject_id = RHS['Subject ID']
                send_request2 = requests.get(self.base_url + 'api/subject/' + subject_id,headers={'AUTH-TOKEN': self.get_cognito_token()})
                get_HH_data = json.loads(send_request2.text)
                self.save_registrtation_data(get_HH_data)
                final_ff_data = self.create_final_ff_data(ff_data, avni_ff_data)
                check_record.update(ff_data=final_ff_data)
                print('FF record updated for', slum_name, HH)
        except Exception as e:
            print(e)

    def saveProgramEncounterData(self, encounter_ids,slum_name):
        for i in encounter_ids:
            send_request = requests.get(self.base_url + 'api/programEncounter/' + i,headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_data = json.loads(send_request.text)
            if 'Encounter type' in get_data.keys():
                if get_data['Encounter type'] == 'Family factsheet':
                    self.saveFamilyFactsheetData(get_data['observations'],slum_name)
                elif get_data['Encounter type'] == 'Daily Reporting':
                    self.saveDailyReportingData(get_data['observations'],slum_name)
                else : pass

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
            if not check_record:
                rhs_data = {}
                final_rhs_data = self.create_final_rhs_data(rhs_data, rhs_from_avni)
                update_record = HouseholdData.objects.create(household_number=household_number, slum_id=slum_id,
                city_id=city_id, submission_date=submission_date,rhs_data=final_rhs_data, created_date=created_date)
                print('Household record created for', slum_name, household_number)
            else :
                rhs_data = check_record.values_list('rhs_data',flat=True)[0]
                if rhs_data == None or len(rhs_data) == 0:
                    rhs_data ={}
                final_rhs_data = self.create_final_rhs_data(rhs_data, rhs_from_avni)
                check_record.update(submission_date=submission_date, rhs_data=final_rhs_data,
                                    created_date=created_date)
                print('Household record updated for', slum_name, household_number)
        except Exception as e:
            print('second exception',e)

    def access_program_encounter_data_all(self):
        totalPages, enc_path = self.create_programEncounter_url()
        for i in range(totalPages):
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
                slum = get_HH_data['location']['Slum']
                self.save_registrtation_data(get_HH_data)
                # self.saveProgramEncounterData(encount_ids, get_HH_data['location']['Slum'], get_HH_data['location']['City'])

    def ShiftNativePlaceDataToFF(self,rhs_data,slum_id):
        HH = str(int(rhs_data['Household_number']))
        NativePlace = rhs_data['What is your native place (village, town, city) ?']
        check_record = HouseholdData.objects.filter(slum_id = slum_id, household_number= HH )
        if check_record:
            ff_data = check_record.values_list('ff_data',flat=True)[0]
            if ff_data and 'group_oh4zf84/Name_of_Native_villa_district_and_state' in ff_data.keys():
                print(HH, 'key present')
            else:
                add_place = {'group_oh4zf84/Name_of_Native_villa_district_and_state':NativePlace}
                ff_data.update(add_place)
                print('Updated FF data for', HH)

    def SaveDataFromIds(self):
        IdList = ['0b9dd881-6cfb-4f2d-a6b3-57c8594f6e2e','f6242dfc-5eaf-4073-b0dc-dcb678111a75']
            # ['78fe282a-e38f-4e5e-aed9-0ab954fef27d','c5a6e4b7-64ab-4b25-b570-e54dacbd1bf0',
            #       '7c490add-fee1-4b93-9efc-879826464e1a','3ce4087e-6e6d-4c7e-aade-c5a42355e159']
        slum_name ='Ambedkar vasahat, R K Colony' # set slum name here
        for i in IdList:
            try :
                RequestProgramEncounter = requests.get(self.base_url + 'api/programEncounter/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                RequestEncounter= requests.get(self.base_url + 'api/encounter/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                RequestEnrolment = requests.get(self.base_url + 'api/enrolment/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                RequestHouseholdRegistration = requests.get(self.base_url + 'api/subject/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                if RequestProgramEncounter.status_code == 200:
                    print('ProgramEncounter')
                    # self.saveProgramEncounterData([i],slum_name)
                elif RequestEncounter.status_code == 200:#pass
                    print('Encounter')
                    # self.access_encounter_data()
                elif RequestEnrolment.status_code == 200:#pass
                    print('enrol')
                    # self.access_enrolment_data()
                elif RequestHouseholdRegistration.status_code == 200:
                    print('Regestation')
                    # self.save_registrtation_data(json.loads(RequestHouseholdRegistration.text))
                else:
                    print(i,'uuid is not accesible')
            except Exception as e:
                print(e)

    def set_mobile_number(self):
        get = HouseholdData.objects.all().filter(slum_id=1675)
        get_data = get.values('household_number','rhs_data')
        for i in get_data:
            HH = i['household_number']
            rhs = i['rhs_data']
            for k,v in rhs.items():
                if k == 'Enter the 10 digit mobile number':
                    rhs.update({'group_el9cl08/Enter_the_10_digit_mobile_number' : v})
                    rhs.pop(k)
                if k == 'Aadhar number' :
                    rhs.update({'group_el9cl08/Aadhar_number' :v})
                    rhs.pop(k)
            a = HouseholdData.objects.filter(slum_id=1675,household_number =HH)
            a.update(rhs_data= rhs)
            print('rhs updated for',HH)

