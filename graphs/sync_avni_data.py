from django.conf import settings
import requests
import json
import subprocess
import dateparser
from django.http import HttpResponse
from graphs.models import *
from mastersheet.models import *
from functools import wraps
from time import time
from datetime import timedelta,datetime
import dateutil.parser

direct_encountes =['Sanitation','Property tax','Water','Waste','Electricity']
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

    def get_city_slum_ids(self,slum_name):
        slum = Slum.objects.filter(name=slum_name).values_list('id', 'electoral_ward_id__administrative_ward__city__id')[0]
        return (slum[0], slum[1])

    def lastModifiedDateTime(self):
        # get latest submission date from household table and pass it to url
        last_submission_date = HouseholdData.objects.latest('submission_date')
        latest_date = last_submission_date.submission_date + timedelta(days=1)
        iso_format_next = latest_date.strftime('%Y-%m-%dT00:00:00.000Z')
        return( iso_format_next )

    def map_rhs_key(self,a,b):
        change_keys = {'Enter_household_number_again': 'Househhold number','_notes': 'Note',
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
        try:
            for k, v in change_keys.items():
                if k in a.keys() or v in b.keys():
                    a[k] = b[v]
                    a.pop(v)
                if 'Type_of_unoccupied_house' and 'Type_of_structure_occupancy' in a and a['Type_of_structure_occupancy'] == 'Occupied house':
                        a.pop('Type_of_unoccupied_house')
        except Exception as e:
            print(e)
        print(a)
        return a

    def map_ff_keys(self,a,b):
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
        try:
            for k, v in change_keys.items():
                if k in a.keys() or v in b.keys():
                    a[k]=b[v]
                    a.pop(v)
                occupation = a['group_im2th52/Occupation_s_of_earning_membe']
                useOfToilte = a['group_ne3ao98/Use_of_toilet']
                if type(occupation) == list or type(useOfToilte) == list:
                    occupation_str = ','.join(i for i in occupation)
                    useOfToilte = ','.join(i for i in useOfToilte)
                elif type(occupation) == str or type(useOfToilte) == str:
                    occupation_str =occupation.replace(',','')
                    useOfToilte = useOfToilte.replace(',','')
                else : pass
                a['group_im2th52/Occupation_s_of_earning_membe'] = occupation_str
                a['group_ne3ao98/Use_of_toilet'] = useOfToilte
        except Exception as e:
            print(e)
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
        try:
            for k, v in map_toilet_keys.items():
                if k in a.keys() or v in s.keys():
                    a[k] = s[v]
                    a.pop(v)
                a.pop('Current place of defecation') if 'Current place of defecation' in a else None
                a.pop('Final current place of defecation') if 'Final current place of defecation' in a else None
        except Exception as e:
            print(e)
        return a

    def map_water_keys(self,w):
        map_water_keys ={'group_el9cl08/Type_of_water_connection':'Type of water connection ?'}
        a = {}
        a.update(w)
        try:
            for k, v in map_water_keys.items():
                if k in a.keys() or v in w.keys():
                    a[k] = w[v]
                    a.pop(v)
        except Exception as e:
            print(e)
        return a

    def map_waste_keys(self,ws):
        map_waste_keys = {'group_el9cl08/Facility_of_solid_waste_collection':'How do you dispose your solid waste ?'}
        a = {}
        a.update(ws)
        try:
            for k, v in map_waste_keys.items():
                if k in a.keys() or v in ws.keys():
                    a[k] = ws[v]
                    a.pop(v)
        except Exception as e:
            print(e)
        return a

    # def create_registrationdata_url(self):
    #     latest_date = self.lastModifiedDateTime()
    #     household_path = 'api/subjects?lastModifiedDateTime=' + latest_date  + '&subjectType=Household'
    #     result = requests.get(self.base_url + household_path,headers= {'AUTH-TOKEN':self.get_cognito_token() })
    #     get_text = json.loads(result.text)['content']
    #     pages =  json.loads(result.text)['totalPages']
    #     return (pages,get_text)

    def get_household_details(self,subject_id):
        send_request = requests.get(self.base_url + 'api/subject/' + subject_id,headers={'AUTH-TOKEN': self.get_cognito_token()})
        self.get_HH_data = json.loads(send_request.text)
        self.city = self.get_HH_data['location']['City']
        self.slum = self.get_HH_data['location']['Slum']
        self.HH = str(int(self.get_HH_data['observations']['First name']))
        self.SubmissionDate = self.get_HH_data['audit']['Last modified at']

    def programEncounter_api_call(self):
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' +'2020-09-05T00:00:00.000Z'+'&encounterType=Family factsheet'
        result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count, programEncounters_path)

    def directEncounter_api_call(self):  #need to run for every program encounter type
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date  +'&encounterType='+ i #'2020-08-25T00:00:00.000Z'
            result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return(get_page_count, programEncounters_path)

    def mobilization_activity_api_call(self):
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date + '&encounterType=' + 'Daily Mobilization Activity'
        result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count,programEncounters_path)

    def SaveDailyMobilizationData(self): #save only house number and activity type in mobilization table
        # {'ID': '613b0435-b13f-4356-8081-5d3232f8d6c9', 'Encounter type': 'Daily Mobilization Activity',
        #  'Subject ID': '7e01693c-e0ea-443d-9d7d-f36b074dbf56', 'Subject type': 'Household',
        #  'Encounter date time': '2020-09-23T13:48:03.000Z', 'Earliest scheduled date': None, 'Max scheduled date': None,
        #  'observations': {'Number of Men present': 0, 'Date of the activity conducted': '2020-09-21T18:30:00.000Z',
        #                   'Number of Boys present': 0, 'Type of Activity': 'Samiti meeting1',
        #                   'Number of Other gender members present': 0, 'Number of Women present': 1},
        #  'Cancel date time': None, 'cancelObservations': {},
        #  'audit': {'Created at': '2020-09-24T08:50:41.185Z', 'Last modified at': '2020-09-24T08:50:41.185Z',
        #            'Created by': 'sanjay@shelter', 'Last modified by': 'sanjay@shelter'}}
        HH_list = []
        to_db ={}
        activities ={'Samiti meeting1':'Samitee meeting 1','Samiti meeting2':'Samitee meeting 2',
                     'Samiti meeting3':'Samitee meeting 3','Samiti meeting4':'Samitee meeting 4',
                     'Samiti meeting5':'Samitee meeting 5'} # "Workshop for Women","Workshop for Boys","Workshop for Girls"}
        pages, path = self.GetMobilizationPage()
        for i in range(pages)[5:6]:
            send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
            data = json.loads(send_request.text)['content']
            for i in data[0:5]:
                ActivityDate = i['observations']['Date of the activity conducted']
                typeOfActivity = i['observations']['Type of Activity']
                if typeOfActivity in activities :
                    typeOfActivity == activities[typeOfActivity]
                ActivityId = ActivityType.objects.filter(name=typeOfActivity)[0]
                self.get_household_details(i['Subject ID'])
                HH_list.append(self.HH)
                slum_id,city_id = self.get_city_slum_ids(self.slum)
                to_db = { 'slum_id': slum_id, 'activity_type_id' :ActivityId.key, 'HH_list' :HH_list}
        # CommunityMobilization.objects.filter(household_number=,activity_date,activity_type_id ,slum_id)

    def save_registrtation_data(self,HH_data):
        final_rhs_data ={}
        rhs_from_avni = HH_data['observations']
        household_number = str(int(rhs_from_avni['First name']))
        created_date = HH_data['Registration date']
        submission_date = (HH_data['audit']['Last modified at'])  # use last modf date
        slum_name = HH_data['location']['Slum']
        try:
            slum_id, city_id = self.get_city_slum_ids(slum_name)
            check_record = HouseholdData.objects.filter(household_number=household_number,city_id=city_id,slum_id=slum_id)
            if not check_record:
                rhs_data = {}
                final_rhs_data = self.map_rhs_key(rhs_data, rhs_from_avni)
                update_record = HouseholdData.objects.create(household_number=household_number, slum_id=slum_id,
                city_id=city_id, submission_date=submission_date,rhs_data=final_rhs_data, created_date=created_date)
                print('Household record created for', slum_name, household_number)
            else :
                rhs_data = check_record.values_list('rhs_data',flat=True)[0]
                if rhs_data == None or len(rhs_data) == 0:
                    rhs_data ={}
                final_rhs_data = self.map_rhs_key(rhs_data, rhs_from_avni)
                check_record.update(submission_date=submission_date, rhs_data=final_rhs_data,
                                    created_date=created_date)
                print('Household record updated for', slum_name, household_number)
        except Exception as e:
            print('second exception',e)

    def update_rhs_data(self,subject_id,encounter_data):
        self.get_household_details(subject_id)
        try:
            get_record = HouseholdData.objects.filter(slum_id__name =self.slum,household_number =self.HH)
            if not get_record:
                print('Record not found for',self.HH)
                self.save_registrtation_data(self.get_HH_data)
            get_rhs_data = get_record.values_list('rhs_data', flat=True)[0]
            get_rhs_data.update(encounter_data)
            get_record.update(rhs_data = get_rhs_data)
            print('rhs record updated for', self.HH)
        except Exception as e:
            print(e, self.HH)

    def save_followup_data(self,subject_id,encounter_data):
        self.get_household_details(subject_id)
        try:
            get_record = FollowupData.objects.filter(household_number=self.HH, slum_id__name=self.slum)
            if len(get_record) <= 0 :
                slum_id, city_id = self.get_city_slum_ids(self.slum)
                update_record = FollowupData.objects.create(household_number=self.HH, slum_id=slum_id,
                city_id=city_id, submission_date=self.SubmissionDate, followup_data=encounter_data,
                created_date=self.get_HH_data['audit']['Created at'],flag_followup_in_rhs=False)
                print('followup record created for', self.HH)
            else:
                for i in get_record:
                    if i.submission_date == dateparser.parse(self.SubmissionDate) :
                        get_followup_data = i.followup_data
                        get_followup_data.update(encounter_data)
                        get_followup_data.update(followup_data=get_followup_data)
                        print('followup record updated for', self.HH)
        except Exception as e:
            print(e,self.HH)

    def save_direct_encounter_data(self):
        pages,path = self.directEncounter_api_call()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
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
                    sanitation_data.update({'submission_date':j['audit']['Last modified at']})
                    self.update_rhs_data(j['Subject ID'],sanitation_data)
                    self.save_followup_data( j['Subject ID'],sanitation_data)
        except Exception as e:
            print(e)

    def saveDailyReportingData(self,data,slum_name):
        pass

    def saveFamilyFactsheetData(self,avni_ff_data,slum_name):
        HH = str(avni_ff_data["Househhold number"])
        try:
            slum = Slum.objects.filter(name= slum_name).values_list('id', 'electoral_ward_id__administrative_ward__city__id')[0]
            slum_id, city_id = slum[0],slum[1]
            check_record = HouseholdData.objects.filter(household_number = HH,city_id=city_id,slum_id=slum_id)
            if check_record:
                ff_data = check_record.values_list('ff_data',flat= True)[0]
                if ff_data == None or len(ff_data) == 0:
                    ff_data = {}
                final_ff_data = self.map_ff_keys(ff_data,avni_ff_data)
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
                final_ff_data = self.map_ff_keys(ff_data, avni_ff_data)
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

    def fetch_program_encounter_data(self):
        totalPages, enc_path = self.programEncounter_api_call()
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
                self.save_registrtation_data(get_HH_data)
                self.saveProgramEncounterData(encount_ids, get_HH_data['location']['Slum'])

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
        IdList = ['14889bfa-78e4-487a-afb5-d60f8c407759']
        slum_name ='Rajendra Nagar' # set slum name here
        for i in IdList:
            try :
                RequestProgramEncounter = requests.get(self.base_url + 'api/programEncounter/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                RequestEncounter= requests.get(self.base_url + 'api/encounter/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                RequestEnrolment = requests.get(self.base_url + 'api/enrolment/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                RequestHouseholdRegistration = requests.get(self.base_url + 'api/subject/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                if RequestProgramEncounter.status_code == 200:
                    print('ProgramEncounter')
                    self.saveProgramEncounterData([i],slum_name)
                elif RequestEncounter.status_code == 200:
                    print('Encounter')
                    self.access_encounter_data()
                elif RequestEnrolment.status_code == 200:
                    print('enrol')
                    self.access_enrolment_data()
                elif RequestHouseholdRegistration.status_code == 200:
                    print(RequestHouseholdRegistration.text)
                    self.save_registrtation_data(json.loads(RequestHouseholdRegistration.text))
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

    def changeListToStrInFfData(self):

        getData = HouseholdData.objects.filter(slum_id=1675)
        for i in getData:
            ff  = getData.filter(household_number=i.household_number)
            getff = ff.values_list('ff_data', flat=True)[0]
            if type(getff['group_ne3ao98/Use_of_toilet']) == list:
                useOfToilte = getff['group_ne3ao98/Use_of_toilet']
                useOfToilte = ','.join(i for i in useOfToilte)
                getff['group_ne3ao98/Use_of_toilet']= useOfToilte
                ff.update(ff_data = getff)
                print('updated for',i.household_number)
            elif type(useOfToilte) == str:pass
            else : pass

# call functions depending on required data to be saved
    # a = avni_sync()
    # a.fetch_program_encounter_data() # save program encounter data and registration data
    # a.save_direct_encounter_data() # save direct encounter data (eg. sanitation, water etc)
    # a.SaveDailyMobilizationData() # save daily mobilization data
    # a.SaveDataFromIds() # save data from uuids for perticular records if required
