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

    def get_city_slum_ids(self,slum_name):
        slum = Slum.objects.filter(name=slum_name).values_list('id', 'electoral_ward_id__administrative_ward__city__id')[0]
        return (slum[0], slum[1])

    def lastModifiedDateTime(self):
        # get latest submission
        # date from household table and pass it to url
        last_submission_date = HouseholdData.objects.latest('submission_date')
        latest_date = last_submission_date.submission_date + timedelta(days=1)
        iso_format_next = latest_date.strftime('%Y-%m-%dT00:00:00.000Z')
        iso = "2020-07-01T00:00:00.000Z"
        return(iso)

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
        for k, v in change_keys.items():
            try:
                if k in a.keys() or v in b.keys():
                    a[k] = b[v]
                    a.pop(v)
                if 'Type_of_structure_occupancy' in a and a['Type_of_structure_occupancy'] == 'Occupied house' or 'Shop':
                    a.pop('Type_of_unoccupied_house') if 'Type_of_unoccupied_house' in a else None
            except Exception as e:
                print(e)
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
        occupation_str =''
        useOfToilte =''
        a.update(b)
        for k, v in change_keys.items():
            try:
                if k in a.keys() or v in b.keys():
                    a[k]=b[v]
                    a.pop(v)
                occupation = a['group_im2th52/Occupation_s_of_earning_membe'] if 'group_im2th52/Occupation_s_of_earning_membe' in a else None
                useOfToilte = a['group_ne3ao98/Use_of_toilet'] if 'group_ne3ao98/Use_of_toilet' in a else None
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
            'group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets': 'Is there availability of drainage to connect it to the toilet?',
            'group_oi8ts04/Are_you_interested_in_an_indiv':'Are you interested in an individual toilet ?',
            'group_oi8ts04/What_kind_of_toilet_would_you_like': 'What kind of toilet would you like ?',
            'group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built': 'Under what scheme would you like your toilet to be built ?',
            'group_oi8ts04/If_yes_why': 'If yes for individual toilet , why?',
            'group_oi8ts04/If_no_why': 'If no for individual toilet , why?',
            'group_rz72p62/Which_Community_Toilet_Blocks': 'Which CTB do your family members use ?',
            'group_el9cl08/Does_any_household_m_n_skills_given_below': 'Does any household member have any of the construction skills given below ?'}
        a ={}
        a.update(s)
        for k, v in map_toilet_keys.items():
            try:
                if k in a.keys() or v in s.keys():
                    a[k] = s[v]
                    a.pop(v)
                # if 'Current place of defecation' in a :
                #     a.pop('Current place of defecation')
                # else: pass
            except Exception as e:
                print(e)
        return a

    def map_water_keys(self,w):
        map_water_keys ={'group_el9cl08/Type_of_water_connection':'Type of water connection ?'}
        a = {}
        a.update(w)
        for k, v in map_water_keys.items():
            try:
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
        for k, v in map_waste_keys.items():
            try:
                if k in a.keys() or v in ws.keys():
                    a[k] = ws[v]
                    a.pop(v)
            except Exception as e:
                print(e)
        return a

    def get_household_details(self, subject_id):
        send_request = requests.get(self.base_url + 'api/subject/' + subject_id,
                                    headers={'AUTH-TOKEN': self.get_cognito_token()})
        self.get_HH_data = json.loads(send_request.text)
        self.city = self.get_HH_data['location']['City']
        self.slum = self.get_HH_data['location']['Slum']
        self.HH = str(int(self.get_HH_data['observations']['First name']))
        self.SubmissionDate = self.get_HH_data['audit']['Last modified at']

    def getHouseholdNumberFromEnrolmentID(self,enrol_id):
        send_request1 = requests.get(self.base_url + 'api/enrolment/' + enrol_id,headers={'AUTH-TOKEN': self.get_cognito_token()})
        RHS = json.loads(send_request1.text)
        self.get_household_details(RHS['Subject ID'])
        return (self.slum,self.HH)

    def create_registrationdata_url(self): #checked
        latest_date = self.lastModifiedDateTime()
        household_path = 'api/subjects?lastModifiedDateTime=' + latest_date  + '&subjectType=Household'
        result = requests.get(self.base_url + household_path,headers= {'AUTH-TOKEN':self.get_cognito_token() })
        get_text = json.loads(result.text)['content']
        pages =  json.loads(result.text)['totalPages']
        return (pages,household_path)

    def registrtation_data(self,HH_data): #checked
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
                final_rhs_data.update({'rhs_uuid': HH_data['ID']})
                update_record = HouseholdData.objects.create(household_number=household_number, slum_id=slum_id,
                city_id= city_id, submission_date=submission_date,rhs_data=final_rhs_data, created_date=created_date)
                print('Household record created for', slum_name, household_number)
            else :
                rhs_data = check_record.values_list('rhs_data',flat=True)[0]
                if rhs_data == None or len(rhs_data) == 0:
                    rhs_data ={}
                final_rhs_data = self.map_rhs_key(rhs_data, rhs_from_avni)
                final_rhs_data.update({'rhs_uuid': HH_data['ID']})
                check_record.update(submission_date=submission_date, rhs_data=final_rhs_data,
                                    created_date=created_date)
                print('Household record updated for', slum_name, household_number)
        except Exception as e:
            print('second exception',e)

    def SaveRhsData(self): # checked
        pages,path = self.create_registrationdata_url()
        for i in range(pages):
            send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_HH_data = json.loads(send_request.text)['content']
            for i in get_HH_data:
                self.registrtation_data(i)

    def update_rhs_data(self,subject_id,encounter_data): #checked
        self.get_household_details(subject_id)
        try:
            get_record = HouseholdData.objects.filter(slum_id__name =self.slum,household_number =self.HH)
            if not get_record:
                print('Record not found for',self.HH)
                self.registrtation_data(self.get_HH_data)
            get_rhs_data = get_record.values_list('rhs_data', flat=True)[0]
            get_rhs_data.update(encounter_data)
            get_record.update(rhs_data = get_rhs_data)
            print('rhs record updated for', self.HH,self.slum)
        except Exception as e:
            print(e, self.HH)

    def create_mobilization_activity_url(self):  #checked
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date + '&encounterType=' + 'Daily Mobilization Activity'
        result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count, programEncounters_path)

    def CommunityMobilizationActivityData(self, data, slum_name, HH):  #checked
        activities = {'Samiti meeting1': 'Samitee meeting 1', 'Samiti meeting2': 'Samitee meeting 2',
                      'Samiti meeting3': 'Samitee meeting 3', 'Samiti meeting4': 'Samitee meeting 4',
                      'Samiti meeting5': 'Samitee meeting 5'}  # "Workshop for Women","Workshop for Boys","Workshop for Girls"}
        try:
            slum_id, city_id = self.get_city_slum_ids(slum_name)
            if data['Type of Activity'] in activities:
                activity = ActivityType.objects.filter(name=activities[data['Type of Activity']]).values_list('key', flat=True)[0]
            else:
                activity = ActivityType.objects.filter(name=data['Type of Activity']).values_list('key', flat=True)[0]
            check = CommunityMobilizationActivityAttendance.objects.filter(slum=slum_id, city=city_id,household_number=HH,
                                                                           activity_type_id = activity)
            if not check:
                save = CommunityMobilizationActivityAttendance.objects.create(slum_id=slum_id, city_id=city_id,
                date_of_activity=dateparser.parse(data['Date of the activity conducted']).date(),activity_type_id=activity,household_number=HH,
                males_attended_activity=data['Number of Men present'] if 'Number of Men present' in data else 0,
                females_attended_activity=data['Number of Women present'] if 'Number of Women present' in data else 0,
                other_gender_attended_activity=data['Number of Other gender members present'] if 'Number of Other gender members present' in data else 0,
                girls_attended_activity=data['Number of Girls present'] if 'Number of Girls present' in data else 0,
                boys_attended_activity=data['Number of Boys present'] if 'Number of Boys present' in data else 0)
                print('record created for', HH,slum_name)
            else:
                update = check.update(date_of_activity=dateparser.parse(data['Date of the activity conducted']).date(),
                activity_type_id=activity, household_number=HH,
                males_attended_activity=data['Number of Men present'] if 'Number of Men present' in data else 0,
                females_attended_activity=data['Number of Women present'] if 'Number of Women present' in data else 0,
                other_gender_attended_activity=data['Number of Other gender members present'] if 'Number of Other gender members present' in data else 0,
                girls_attended_activity=data['Number of Girls present'] if 'Number of Girls present' in data else 0,
                boys_attended_activity=data['Number of Boys present'] if 'Number of Boys present' in data else 0)
                print('record updated for', HH,slum_name)
        except Exception as e:
            print(e, HH)

    def SaveCommunityMobilizationData(self):  #checked
        pages, path = self.create_mobilization_activity_url()
        for i in range(pages):
            send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
            data = json.loads(send_request.text)['content']
            for j in data:
                if len(j['observations']) > 0:
                    self.get_household_details(j['Subject ID'])
                    self.CommunityMobilizationActivityData(j['observations'], self.slum, self.HH)
                else:
                    print('No data')

    def SaveFamilyFactsheetData(self):#checked
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' + latest_date + '&encounterType=Family factsheet'
        result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        for i in range(get_page_count):
            send_request = requests.get(self.base_url + programEncounters_path + '&' + str(i),
                                        headers={'AUTH-TOKEN': self.get_cognito_token()})
            data = json.loads(send_request.text)['content']
            for j in data:
                slum, HH = self.getHouseholdNumberFromEnrolmentID(j['Enrolment ID'])
                self.FamilyFactsheetData(j, slum, HH)

    def FamilyFactsheetData(self, data, slum_name, HH): #checked
        try:
            slum_id, city_id =self.get_city_slum_ids(slum_name)
            check_record = HouseholdData.objects.filter(household_number=HH, city_id=city_id, slum_id=slum_id)
            factsheetDate = ToiletConstruction.objects.filter(household_number=HH,slum_id=slum_id)
            if check_record:
                ff_data = check_record.values_list('ff_data', flat=True)[0]
                if ff_data == None or len(ff_data) == 0:
                    ff_data = {}
                final_ff_data = self.map_ff_keys(ff_data, data['observations'])
                final_ff_data.update({'ff_uuid': data['ID']})
                check_record.update(ff_data=final_ff_data)
                factsheetDate.update(factsheet_done = dateparser.parse(data['Encounter datetime']))
                print('FF record updated for', slum_name, HH)
            else:
                ff_data = {}
                Enrol_id = data['Enrolment ID']
                request = requests.get(self.base_url + 'api/enrolment/' + Enrol_id,
                                    headers={'AUTH-TOKEN': self.get_cognito_token()})
                subject_id = json.loads(request.text)['Subject ID']
                send_request2 = requests.get(self.base_url + 'api/subject/' + subject_id ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                get_HH_data = json.loads(send_request2.text)
                self.registrtation_data(get_HH_data)
                get_reocrd = HouseholdData.objects.filter( household_number = HH, slum_id = slum_id, city_id= city_id)
                final_ff_data = self.map_ff_keys(ff_data, data['observations'])
                final_ff_data.update({'ff_uuid': data['ID']})
                get_reocrd.update(ff_data = final_ff_data)
                factsheetDate.update(factsheet_done=dateparser.parse(data['Encounter datetime']))
                print('FF record updated for', slum_name, HH)
        except Exception as e:
            print(e)

    def SaveDailyReportingdata(self):  # checked
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' + latest_date +'&encounterType=Daily Reporting'
        result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        for i in range(get_page_count):
            send_request = requests.get(self.base_url + programEncounters_path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
            data = json.loads(send_request.text)['content']
            for j in data:
                slum_id, HH = self.getHouseholdNumberFromEnrolmentID(j['Enrolment ID'])
                self.DailyReportingData(j['observations'],slum_id,HH)

    def get_max_date(self,dates_list):
        max = 0
        for i in dates_list:
            d = dates_list[0]
            if d > dates_list[dates_list.index(i) + 1]:
                max = d
            else:
                max = dates_list[dates_list.index(i)]
        return max

    def DailyReportingData(self, data, slum, HH): #checked
        slum_id, city_id =self.get_city_slum_ids(slum)
        phase_one_material_dates =[]
        phase_two_material_dates =[]
        phase_one_materials = ['Date on which bricks are given', 'Date on which sand is given','Date on which crush sand is given', 'Date on which river sand is given',
                               'Date on which cement is given']
        phase_two_materials = ['Date on which other hardware items are given', 'Date on which pan is given','Date on which Tiles are given']
        for j in phase_one_materials:
            if j in data:
                phase_one_material_dates.append(dateparser.parse(data[j]).replace(tzinfo=None))
        for j in phase_two_materials:
            if j in data:
                phase_two_material_dates.append(dateparser.parse(data[j]).replace(tzinfo=None))
        try:
            agreement_cancelled = True if ('Date on which agreement is cancelled' in data and data['Date on which agreement is cancelled'] != None) else False
            if 'Date on which septic tank is given' in data :
                septic_tank_date = dateparser.parse(data['Date on which septic tank is given']).date()
            else :septic_tank_date = None
            if len(phase_one_material_dates) > 0:
                phase_one_material_date = self.get_max_date(phase_one_material_dates)
            else :phase_one_material_date = None
            if len(phase_two_material_dates) > 0 :
                phase_two_material_date = self.get_max_date(phase_two_material_dates)
            else : phase_two_material_date = None
            if 'Date on which door is given' in data :
                phase_three_material_date = dateparser.parse(data['Date on which door is given']).date()
            else :phase_three_material_date = None
            if 'Date on which toilet construction is complete' in data :
                completion_date = dateparser.parse(data['Date on which toilet construction is complete']).date()
            else :completion_date= None
            if 'House numbers of houses where PHASE 1 material bricks, sand and cement is given' in data :
                p1_material_shifted_to = dateparser.parse(data['House numbers of houses where PHASE 1 material bricks, sand and cement is given']).date()
            else :p1_material_shifted_to = None
            if 'House numbers of houses where PHASE 2 material Hardware is given' in data :
                p2_material_shifted_to = dateparser.parse(data['House numbers of houses where PHASE 2 material Hardware is given']).date()
            else :p2_material_shifted_to= None
            if  'House numbers where material is shifted - 3rd Phase' in data :
                p3_material_shifted_to = dateparser.parse(data['House numbers where material is shifted - 3rd Phase']).date()
            else:p3_material_shifted_to = None
            if 'House numbers of houses where Septic Tank is given' in data :
                st_material_shifted_to = dateparser.parse(data['House numbers of houses where Septic Tank is given']).date()
            else:st_material_shifted_to= None
            if 'Date on whcih toilet is connected to drainage line' in data :
                toilet_connected_to = dateparser.parse(data['Date on whcih toilet is connected to drainage line']).date()
            else:toilet_connected_to= None
            if 'Whether toilet is in use or not?' in data :
                toilet_in_use = data['Whether toilet is in use or not?']
            else:toilet_in_use = None
            if 'Date on which toilet construction is complete' in data and toilet_in_use == 'Yes':
                use_of_toilet = dateparser.parse(data['Date on which toilet construction is complete']).date()
            else :  use_of_toilet = None
            check_record = ToiletConstruction.objects.filter(household_number=HH, slum_id= slum_id)
            if 'Date of agreement' in data:
                if not check_record:
                    create = ToiletConstruction.objects.create(household_number=HH, slum_id = slum_id,
                    agreement_date = dateparser.parse(data['Date of agreement']).date(),
                    agreement_cancelled= agreement_cancelled,septic_tank_date=septic_tank_date,
                    phase_one_material_date = phase_one_material_date,phase_two_material_date= phase_two_material_date,
                    phase_three_material_date =phase_three_material_date,completion_date=completion_date,
                    p1_material_shifted_to=p1_material_shifted_to,p2_material_shifted_to=p2_material_shifted_to,
                    p3_material_shifted_to=p3_material_shifted_to,st_material_shifted_to=st_material_shifted_to,
                    toilet_connected_to=toilet_connected_to,use_of_toilet= use_of_toilet)
                    print('Construction status created for', HH, slum_id)
                else :
                    check_record.update(agreement_date = dateparser.parse(data['Date of agreement']).date(),
                    agreement_cancelled=agreement_cancelled, septic_tank_date=septic_tank_date,
                    phase_one_material_date=phase_one_material_date,
                    phase_two_material_date=phase_two_material_date,
                    phase_three_material_date=phase_three_material_date,
                    completion_date=completion_date,
                    p1_material_shifted_to=p1_material_shifted_to,
                    p2_material_shifted_to=p2_material_shifted_to,
                    p3_material_shifted_to=p3_material_shifted_to,
                    st_material_shifted_to=st_material_shifted_to,
                    toilet_connected_to=toilet_connected_to, use_of_toilet=use_of_toilet)
                    print('Construction status updated for', HH, slum_id)
            else:pass
        except Exception as e:
            print(e,HH)

    def SanitationEncounterData(self):  # checked
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date +'&encounterType='+'Sanitation'
        result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count, programEncounters_path)

    def followup_data_sanitation(self,subject_id,sanitation_data): # checked
        self.get_household_details(subject_id)
        try:
            get_record = FollowupData.objects.filter(household_number=self.HH, slum_id__name=self.slum)
            if len(get_record) <= 0 :
                slum_id, city_id = self.get_city_slum_ids(self.slum)
                create_record = FollowupData.objects.create(household_number=self.HH, slum_id=slum_id,
                city_id=city_id, submission_date=self.SubmissionDate, followup_data = sanitation_data,
                created_date = self.get_HH_data['audit']['Created at'],flag_followup_in_rhs=False)
                print('followup record created for', self.HH)
            else:
                for i in get_record:
                    get_followup_data = i.followup_data
                    get_followup_data.update(sanitation_data)
                    get_record.update(followup_data = get_followup_data, submission_date = dateparser.parse(self.SubmissionDate))
                    print('followup record updated for', self.HH,self.slum)
        except Exception as e:
            print(e,self.HH)

    def SaveFollowupData(self): # checked
        pages,path = self.SanitationEncounterData()
        print(pages)
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    sanitation_data = self.map_sanitation_keys(j['observations'])
                    sanitation_data.update({'submission_date': j['audit']['Last modified at']})
                    self.update_rhs_data(j['Subject ID'], sanitation_data)
                    self.followup_data_sanitation(j['Subject ID'], sanitation_data)
        except Exception as e:
            print(e)

    def WaterEncounterData(self): # checked
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date +'&encounterType='+'Water'
            result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return (get_page_count, programEncounters_path)

    def SaveWaterData(self): # checked
        pages,path = self.WaterEncounterData()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    water_data = self.map_water_keys(j['observations'])
                    water_data.update({'Last_modified_date': j['audit']['Last modified at']})
                    self.update_rhs_data(j['Subject ID'], water_data)
        except Exception as e:
            print(e)

    def WasteEncounterData(self):# checked
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date +'&encounterType='+'Waste'
            result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return (get_page_count, programEncounters_path)

    def SaveWasteData(self): # checked
        pages,path = self.WasteEncounterData()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    waste_data = self.map_waste_keys(j['observations'])
                    waste_data.update({'Last_modified_date': j['audit']['Last modified at']})
                    self.update_rhs_data(j['Subject ID'], waste_data)
        except Exception as e:
            print(e)

    def PropertyTaxEncounterData(self): # checked
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date +'&encounterType='+'Property tax'
            result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return (get_page_count, programEncounters_path)

    def SavePropertyTaxData(self): # checked
        pages,path = self.PropertyTaxEncounterData()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    tax_data  = j['observations']
                    tax_data.update({'Last_modified_date': j['audit']['Last modified at']})
                    self.update_rhs_data(j['Subject ID'], tax_data)
        except Exception as e:
            print(e)

    def ElectricityEncounterData(self): # checked
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date +'&encounterType='+'Electricity'
            result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return (get_page_count, programEncounters_path)

    def SaveElectricityData(self): # checked
        pages,path = self.ElectricityEncounterData()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    electricity_data = j['observations']
                    electricity_data.update({'Last_modified_date': j['audit']['Last modified at']})
                    self.update_rhs_data(j['Subject ID'],electricity_data)
        except Exception as e:
            print(e)

    def SaveDataFromIds(self):
        IdList =['8d09d5c1-7477-4613-8372-bc4b9a29126d','4a2b7118-3615-404c-94d2-b65eb517a2f0','47d533f2-ee34-49ef-88f6-17f3e6416b0c','2e21f8fe-57d3-4f50-b067-26d61f0e080b','09c43a10-1732-419a-9bf7-49941166bd13','021f151b-ce50-437b-91e9-4c352be35b1d','eb6dc377-70cc-4ae7-a50d-e58db29318d1','878e9f66-e465-4757-88e7-a6b7734f87f5','a7ae7f23-bb08-440d-ab8f-92419085e284','9a5400c1-43bf-45b9-9c1f-9aefb5e27abd','01cd8c81-e3cf-43b7-b647-4a992a70ea1a','6affd2a8-49b8-4d30-b35a-a0bc6933188f','92a95f68-3fd9-46e1-b91b-cefbc1d1fbc6','77a70f04-6fd2-422a-aac8-22e79245d180','050f52d3-ff09-48b5-997b-1106a3be6656','fe189546-43f9-4da8-96bc-6086da494387','679a8c8a-9e1a-4f07-98a9-8f2eff45babd','06c467c3-a014-450a-858b-a5f7dbb485e4','a0a81829-5c2a-495f-8185-604c5df50a5c','1447ceea-2ef2-46c8-87fc-fcdd2c50d662','3f8b06a2-4c38-415b-a5d5-2ca148497de7','b9a40c05-aa9f-4321-ac45-fb07e4376f7f','250329f2-e2aa-4679-8731-96b831a05aa5','30c009a8-3e0b-4d5d-845d-152898218459','726e70a2-234c-461c-b148-5e6ce1ff82c8','70c34c89-df76-45d0-94c4-bb549ea630f1','ef818f08-bbf5-412e-9097-856f136672f5','5cfaf01a-5175-4774-920c-34d1031a6c20','5538e0b8-74ac-4835-9e15-688f48634ece','bd307a06-c6a3-4b7a-b08e-3a541e38f05f','1f81abfe-d03e-428f-b287-de36e082d6d4','d7867e0d-ab52-4f6b-9cac-3b177afb8402','ac161816-9e55-4a35-b92c-264864ea6861','ba16bd54-d1af-4480-b2da-a09799d5e1c0','2192dd15-a3fd-4f06-b600-e5ecc96e462c','4b40ea9d-8a59-4bdf-877c-3bc238c02cd8','c08cfb06-ebb6-4ea1-96bc-8cf238c2456a','8f70e592-ef05-4769-888d-a3fd723c211e','a832fb57-608b-4adb-a60c-a04192affdb0','c3867093-1b8f-433a-9a94-16b41caf304d','37e0a2c8-f7a9-4a4c-a652-07c6325a1e4d','bd3b0300-3e2d-43d0-b6f3-7a9f6b827c6c','001f588c-1842-4571-8435-551bdd7355c7','56ebcbde-ae15-48e5-a416-a505206f93f4','c8474788-cddd-4bd4-8d96-9538ef69aaa2','173ef256-75a0-4c6d-94a5-566e1772c962','1f6826fe-fca1-410c-a91f-d807e47e0ba4','d10120c4-498a-4ce7-8c5b-843f636fcde0','b21e35bd-59b3-4ed2-ae14-2072c4a4aef0','488d62f5-f678-4093-9b21-6943bbd72afd','b1a04304-47c9-4c31-a8ff-9c09531d5648','1323ad1c-0c3e-4c8e-a4ce-75138b50eaaf','c7af4a6c-09fe-4aa1-9349-91bac2980ab2','cfb3fb2f-4685-4756-84e0-262e9ef05143','bba64b45-88bf-45df-83f9-8b14581871b3','dfa07e9a-c6b2-4073-abf9-4af436a0455b','f9894d6b-3bb7-4e25-ac38-2455578f40ce','0a797f6b-0718-4aff-aef5-ecd5609344b0','e19108bf-997a-43c1-9bfe-2a0bfbd563d4','52e5d164-b143-49b9-9a12-777a62108256','dcbad24c-5d1b-4cde-af20-92ceea1ce320','8a557d06-cf53-486e-8c53-308cb7e6755e','5c35cddb-d37a-40ab-a131-1809f219df59','cdebdb1b-db25-4464-a1d9-23669a1c28c9','06687172-1a60-4f16-93ed-ae6772036737','d66396ea-6b6e-4358-a7f9-9193587c1156','a13bc71d-c057-4f66-94ed-cb26b79e9260','b3ab185b-8742-4084-b73b-dec3e2acb313','606bf068-3bcb-476e-ae49-aeb59b973009','b85ede87-02cf-4d5f-bc56-19450a448998','5310c531-6e49-491a-9697-6e949879c160','a3377ab3-48bd-4472-89a9-911c323ccf02','07dce9d7-31b4-4ed4-a596-79f8b3476630','4c25d040-889f-4177-864b-8e9ef1471441','38409170-73c1-4588-93dc-f7b718fc5648','ae86efd3-520c-4cbe-879a-2029bbd28c27','50ee1ae7-f8ca-448e-8f45-422588287754','55cd6350-d3eb-49bd-8667-009e6938b235','6c15a21e-a51a-4a8c-8381-4730f6a3772b','8052f15b-bef8-46f7-9fe3-2291068d163c','0959907b-416f-466e-ab60-65c4cf6b6c9a','c4edc6ee-961f-4c14-b506-e2b45d9e0ac1','ac00c25b-b17b-4a7f-9552-ffb424ded0b4','7c0e2a11-f6f8-4010-b354-0bc07d59aecb','66f443ae-7690-45e5-ad28-8d68cd8a5362','027407b7-eb2d-4986-a551-6425f946f668','fdfca3f4-84f1-44ef-b239-f754a5c85200','daa2a813-6259-4398-83b9-302b6e938202','620a018a-51e8-4a97-b896-dafffcb8362e','b772bb64-f991-4850-888f-0f3ea767dc2d','73ae9e25-d632-4213-845a-6933e84ab893','19e5437c-1f97-4aba-8ae2-a68de68fdf13','a5678f05-8377-48d7-90f3-e590c71e09af','b4e8e9b7-6cc7-45eb-918e-5fa1ceb92024','ceeb4935-98a5-40df-9f9c-7b1894a35534','33883027-9404-4b35-bd19-c9366d455a38','25301886-5edb-44b0-9a2b-18aa4d0f5d87','248f9fb2-e565-49bf-a10f-41e7c10b7247','0e96c73f-bafb-4aa9-b31f-473f91fdfa5f','7ca1b678-dab3-4058-88e7-4f2fa33b42dc','9093d29b-4fdf-456d-8931-b43d69aa4024','0962b67b-26cd-4c63-9d7c-1454145bd589','05a12170-94e9-4417-a23f-2e85666e2047','e2afe1c3-1bc9-4e49-a2cc-4525d8197302','25ec514f-0350-461e-880f-919a7dbf51ee','40299431-3226-47ce-ba2f-7b09472345da','2bb419a5-c335-4181-a624-2aba3edf23af','cb957e53-4315-48c8-8a4f-455f32b88e79','b7250a6b-2645-4402-bb0f-a47f379a827c','2ebedaab-f01e-4493-a77b-fbbe1887b376','96316df3-1ff9-49d6-854d-0a2ac70e940b','d528dd86-297d-4c48-b104-b93e31f2ed4c','852c71a2-6d8f-47b6-8e46-73c7dd779650','f185b0c1-3b23-4fce-b875-9dbedd3bcaf6','c1bb8045-a6f1-4019-9993-36865c61f24e','2d308ce1-81f2-4f73-b6d0-d7cc44e0f508','b4054755-6148-4dd4-a2a6-0297202e31d9','a8bbd995-42ac-4221-8035-6520bacbaaad','04375688-7563-4d51-be3f-380fff8f1333','49c5f6c6-668f-4874-8da7-f759d833e7a1','8091ec0a-a548-4fee-bc0f-55506483b045','07e56a10-558d-4696-a973-4e5e96428a5b','4f4c9f74-a8b4-49c4-a112-ab4a07a45b5d','ceabf28c-3fe7-447f-80e0-d41a88ce3151','db2ab94a-576d-48a9-88de-730d2f0eb406','4db8372a-2072-4c9e-80c0-d092a9a99efe','267d3593-48b8-4143-aa70-fbea75138ecb','d834333a-6cd9-43e6-a8ee-0e4d27544e5c','b5202e49-ea64-4066-a9a6-37de12bdb935','2ab2a626-820d-467b-a298-8dea2f66b200','fd45ffa0-11b5-48e2-a133-07aff6d0b33c','d9b7172e-16bc-4334-b8ed-b6cb48f87e30','86c443ce-432f-4da2-9d8c-1c0d22d4e8b0','70fb1f82-db0e-4cb6-8da2-ea3bfdfe3b2e','b03ddd51-941f-4e1c-981b-6421e880737c']
        for i in IdList[0:2]:
            # try :
            RequestProgramEncounter = requests.get(self.base_url + 'api/programEncounter/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
            RequestEncounter= requests.get(self.base_url + 'api/encounter/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
            RequestHouseholdRegistration = requests.get(self.base_url + 'api/subject/' + i ,headers={'AUTH-TOKEN': self.get_cognito_token()})
            if RequestProgramEncounter.status_code == 200:
                data = json.loads(RequestProgramEncounter.text)
                slum_name,HH = self.getHouseholdNumberFromEnrolmentID(data['Enrolment ID'])
                if data['Encounter type'] == 'Family factsheet':
                    self.FamilyFactsheetData(data,slum_name,HH)
                if data['Encounter type'] == 'Daily Reporting':
                    if 'Date of agreement' in data['observations']:
                        self.DailyReportingData(data['observations'],slum_name,HH)
            elif RequestEncounter.status_code == 200:
                data = json.loads(RequestEncounter.text)
                if data['Encounter type'] == 'Sanitation':
                    sanitation = self.map_sanitation_keys(data['observations']) # sanitation data
                    sanitation.update({'Last_modified_date': data['audit']['Last modified at']})
                    self.update_rhs_data(data['Subject ID'],sanitation)# sanitation data
                    self.followup_data_sanitation(data['Subject ID'],sanitation) # sanitation data
                if data['Encounter type'] == 'Waste':
                    waste = self.map_waste_keys(data['observations'])  # waste  data
                    waste.update({'Last_modified_date': data['audit']['Last modified at']})
                    self.update_rhs_data(data['Subject ID'], waste)  # waste  data
                    self.update_rhs_data(data['Subject ID'], waste)  # waste  data
                if data['Encounter type'] == 'Water':
                    water = self.map_water_keys(data['observations'])  # water  data
                    water.update({'Last_modified_date': data['audit']['Last modified at']})
                    self.update_rhs_data(data['Subject ID'], water) # water  data
                if data['Encounter type'] == 'Property tax':
                    tax = data['observations'] # tax  data
                    tax.update({'Last_modified_date': data['audit']['Last modified at']})
                    self.update_rhs_data(data['Subject ID'], tax)  # tax  data
                if data['Encounter type'] == 'Electricity':
                    electricity = data['observations']  # electricity  data
                    electricity.update({'Last_modified_date': data['audit']['Last modified at']})
                    self.update_rhs_data(data['Subject ID'], electricity)  # electricity data
                if data['Encounter type'] == 'Daily Mobilization Activity':
                    self.get_household_details(data['Subject ID'])
                    self.CommunityMobilizationActivityData(data['observations'],self.slum,self.HH) #CommunityMobilization
            elif RequestHouseholdRegistration.status_code == 200:
                data = json.loads(RequestHouseholdRegistration.text)
                print(RequestHouseholdRegistration.url)
                self.registrtation_data(data)
            else:
                print(i,'uuid is not accesible')
            # except Exception as e:
            #     print(e)

    # def set_mobile_number(self):
    #     get = HouseholdData.objects.all().filter(slum_id=1675)
    #     get_data = get.values('household_number','rhs_data')
    #     for i in get_data:
    #         HH = i['household_number']
    #         rhs = i['rhs_data']
    #         for k,v in rhs.items():
    #             if k == 'Enter the 10 digit mobile number':
    #                 rhs.update({'group_el9cl08/Enter_the_10_digit_mobile_number' : v})
    #                 rhs.pop(k)
    #             if k == 'Aadhar number' :
    #                 rhs.update({'group_el9cl08/Aadhar_number' :v})
    #                 rhs.pop(k)
    #         a = HouseholdData.objects.filter(slum_id=1675,household_number =HH)
    #         a.update(rhs_data= rhs)
    #         print('rhs updated for',HH)
    #
    # def changeListToStrInFfData(self):
    #
    #     getData = HouseholdData.objects.filter(slum_id=1675)
    #     for i in getData:
    #         ff  = getData.filter(household_number=i.household_number)
    #         getff = ff.values_list('ff_data', flat=True)[0]
    #         if type(getff['group_ne3ao98/Use_of_toilet']) == list:
    #             useOfToilte = getff['group_ne3ao98/Use_of_toilet']
    #             useOfToilte = ','.join(i for i in useOfToilte)
    #             getff['group_ne3ao98/Use_of_toilet']= useOfToilte
    #             ff.update(ff_data = getff)
    #             print('updated for',i.household_number)
    #         elif type(useOfToilte) == str:pass
    #         else : pass

    # def programEncounter_api_call(self):
    #     latest_date = self.lastModifiedDateTime()
    #     # programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' + latest_date +'&encounterType=Family factsheet'
    #     programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' + latest_date +'&encounterType=Daily Reporting'
    #     result = requests.get(self.base_url + programEncounters_path,headers={'AUTH-TOKEN': self.get_cognito_token()})
    #     get_page_count = json.loads(result.text)['totalPages']
    #     return (get_page_count, programEncounters_path)
    #
    # def saveProgramEncounterData(self, encounter_ids,slum_name):
    #     for i in encounter_ids:
    #         send_request = requests.get(self.base_url + 'api/programEncounter/' + i,headers={'AUTH-TOKEN': self.get_cognito_token()})
    #         get_data = json.loads(send_request.text)
    #         if 'Encounter type' in get_data.keys():
    #             if get_data['Encounter type'] == 'Family factsheet':
    #                 self.saveFamilyFactsheetData(get_data['observations'],slum_name)
    #             elif get_data['Encounter type'] == 'Daily Reporting':
    #                 HH = self.getHouseholdNumberFromEnrolmentID(get_data['Enrolment ID'])
    #                 self.saveDailyReportingData(get_data['observations'],slum_name,HH) #
    #             else : pass
    #
    # def fetch_program_encounter_data(self):
    #     totalPages, enc_path = self.programEncounter_api_call()
    #     for i in range(totalPages):
    #         send_request = requests.get(self.base_url + enc_path + '&' + str(i),headers={'AUTH-TOKEN': self.get_cognito_token()})
    #         data = json.loads(send_request.text)['content']
    #         for j in data:
    #             if j['Encounter type'] == 'Daily Reporting':
    #                 HH,slum = self.getHouseholdNumberFromEnrolmentID(j['Enrolment ID'])
    #                 self.saveDailyReportingData(j['observations'],slum,HH)
    #             encounter_data = j['observations']
    #             enrolment_id = j['Enrolment ID']
    #             send_request1 = requests.get(self.base_url + 'api/enrolment/' + enrolment_id,headers={'AUTH-TOKEN': self.get_cognito_token()})
    #             text =  json.loads(send_request1.text)
    #             subject_id = text['Subject ID']
    #             encount_ids = text['encounters']
    #             send_request2 = requests.get(self.base_url + 'api/subject/' + subject_id ,headers={'AUTH-TOKEN': self.get_cognito_token()})
    #             get_HH_data = json.loads(send_request2.text)
    #             self.registrtation_data(get_HH_data)
    #             self.saveProgramEncounterData(encount_ids, get_HH_data['location']['Slum'])
    #
    # def ShiftNativePlaceDataToFF(self,rhs_data,slum_id):
    #     HH = str(int(rhs_data['Household_number']))
    #     NativePlace = rhs_data['What is your native place (village, town, city) ?']
    #     check_record = HouseholdData.objects.filter(slum_id = slum_id, household_number= HH )
    #     if check_record:
    #         ff_data = check_record.values_list('ff_data',flat=True)[0]
    #         if ff_data and 'group_oh4zf84/Name_of_Native_villa_district_and_state' in ff_data.keys():
    #             print(HH, 'key present')
    #         else:
    #             add_place = {'group_oh4zf84/Name_of_Native_villa_district_and_state':NativePlace}
    #             ff_data.update(add_place)
    #             print('Updated FF data for', HH)

# call functions depending on required data to be saved
#     a = avni_sync()
#     a.SaveDataFromIds
#     a.SaveRhsData()
#     a.SaveWasteData()
#     a.SaveWaterData()
#     a.SaveElectricityData()
#     a.SavePropertyTaxData()
#     a.SaveFollowupData()
#     a.SaveDailyReportingdata()
#     a.SaveCommunityMobilizationData()
#     a.SaveFamilyFactsheetData()


