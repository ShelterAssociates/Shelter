from django.conf import settings
import requests
import json
import time
import subprocess
import dateparser
from django.http import HttpResponse
from graphs.models import *
from mastersheet.models import *
from master.models import *
from functools import wraps
from time import time
from datetime import timedelta, datetime
import dateutil.parser


direct_encountes = ['Sanitation', 'Property tax', 'Water', 'Waste', 'Electricity', 'Daily Mobilization Activity']
program_encounters = ['Daily Reporting', 'Family factsheet']


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
        cognito_details = requests.get(self.base_url + 'cognito-details')
        cognito_details = json.loads(cognito_details.text)
        self.poolId = cognito_details['poolId']
        self.clientId = cognito_details['clientId']

    def get_cognito_token(self):
        self.get_cognito_details()
        command_data = subprocess.Popen(['node', 'graphs/avni/token.js', self.poolId, self.clientId, settings.AVNI_USERNAME, settings.AVNI_PASSWORD], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = command_data.communicate()
        self.token = stdout.decode("utf-8").replace('\n', '')
        return self.token

    def get_city_slum_ids(self, slum_name):
        slum = Slum.objects.filter(name=slum_name).values_list('id', 'electoral_ward_id__administrative_ward__city__id')[0]
        return slum[0], slum[1]

    def lastModifiedDateTime(self):
        # get the latest submission
        # date from household table and pass it to url
        last_submission_date = HouseholdData.objects.latest('submission_date')
        # latest_date = last_submission_date.submission_date + timedelta(days=1)
        today = datetime.today()  # + timedelta(days= -1)
        latest_date = today.strftime('%Y-%m-%dT00:00:00.000Z')
        iso = "2022-02-01T00:00:00.000Z"
        # return(latest_date)
        return iso

    def get_image(self, image_link):
        path = 'https://app.avniproject.org/media/signedUrl?url='
        request_1 = requests.get(path + image_link, headers={'AUTH-TOKEN': self.get_cognito_token()})
        return request_1.text

    def map_rhs_key(self, a, b):
        change_keys = {'Enter_household_number_again': 'Househhold number', '_notes': 'Note',
                       'Name_s_of_the_surveyor_s': 'Name of the surveyor',
                       'Household_number': 'First name',
                       'group_el9cl08/Aadhar_number': 'Aadhar number',
                       'group_el9cl08/Enter_the_10_digit_mobile_number': 'Enter the 10 digit mobile number',
                       'group_el9cl08/Ownership_status_of_the_house': 'Ownership status of the house_1',
                       'Date_of_survey': 'Date of Survey',
                       'group_el9cl08/House_area_in_sq_ft': 'House area in square feets.',
                       'group_og5bx85/Full_name_of_the_head_of_the_household': 'Full name of the head of the household',
                       'group_el9cl08/Number_of_household_members': 'Number of household members',
                       'Type_of_unoccupied_house': 'Type of unoccupied house_1',
                       'group_el9cl08/Type_of_structure_of_the_house': 'Type of structure of the house_1',
                       'Parent_household_number': 'Parent household number',
                       'Type_of_structure_occupancy': 'Type of structure occupancy_1',
                       'group_el9cl08/Do_you_have_any_girl_child_chi': 'Do you have any girl child/children under the age of 18?_'}
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

    def map_ff_keys(self, a, b):
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
        occupation_str = ''
        useOfToilte = ''
        a.update(b)
        for k, v in change_keys.items():
            try:
                if k in a.keys() or v in b.keys():
                    a[k] = b[v]
                    a.pop(v)
                occupation = a['group_im2th52/Occupation_s_of_earning_membe'] if 'group_im2th52/Occupation_s_of_earning_membe' in a else None
                useOfToilte = a['group_ne3ao98/Use_of_toilet'] if 'group_ne3ao98/Use_of_toilet' in a else None
                if type(occupation) == list or type(useOfToilte) == list:
                    occupation_str = ','.join(i for i in occupation)
                    useOfToilte = ','.join(i for i in useOfToilte)
                elif type(occupation) == str or type(useOfToilte) == str:
                    occupation_str = occupation.replace(',', '')
                    useOfToilte = useOfToilte.replace(',', '')
                else:
                    pass
                a['group_im2th52/Occupation_s_of_earning_membe'] = occupation_str
                a['group_ne3ao98/Use_of_toilet'] = useOfToilte
            except Exception as e:
                print(e)
        return a

    def map_sanitation_keys(self, s):
        map_toilet_keys = {
            'group_oi8ts04/Have_you_applied_for_individua': 'Have you applied for an individual toilet under SBM?_1',
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
            'group_oi8ts04/Are_you_interested_in_an_indiv': 'Are you interested in an individual toilet ?',
            'group_oi8ts04/What_kind_of_toilet_would_you_like': 'What kind of toilet would you like ?',
            'group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built': 'Under what scheme would you like your toilet to be built ?',
            'group_oi8ts04/If_yes_why': 'If yes for individual toilet , why?',
            'group_oi8ts04/If_no_why': 'If no for individual toilet , why?',
            'group_oi8ts04/Which_Community_Toil_r_family_members_use': 'Which CTB do your family members use ?',
            'group_el9cl08/Does_any_household_m_n_skills_given_below': 'Does any household member have any of the construction skills given below ?'}
        a = {}
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

    def get_household_details(self, subject_id):
        send_request = requests.get(self.base_url + 'api/subject/' + subject_id,
                                    headers={'AUTH-TOKEN': self.get_cognito_token()})
        self.get_HH_data = json.loads(send_request.text)
        a_city = self.city = self.get_HH_data['location']['City']
        b_slum = self.slum = self.get_HH_data['location']['Slum']
        c_HH = self.HH = str(int(self.get_HH_data['observations']['First name']))
        d_date = self.SubmissionDate = self.get_HH_data['audit']['Last modified at']
        return a_city, b_slum, c_HH, d_date

    # This function is used to create rhs data url when we sync data page wise.
    def create_registrationdata_url(self):  # checked
        latest_date = self.lastModifiedDateTime()

        household_path = 'api/subjects?lastModifiedDateTime=' + latest_date + '&subjectType=Household'
        result = requests.get(self.base_url + household_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_text = json.loads(result.text)['content']
        pages = json.loads(result.text)['totalPages']
        return pages, household_path

    def registrtation_data(self, HH_data):  # checked
        final_rhs_data = {}
        rhs_from_avni = HH_data['observations']
        household_number = str(int(rhs_from_avni['First name']))
        created_date = HH_data['Registration date']
        submission_date = (HH_data['audit']['Last modified at'])  # use last modf date
        try:
            slum_name = HH_data['location']['Slum']
            slum_id, city_id = self.get_city_slum_ids(slum_name)
            check_record = HouseholdData.objects.filter(household_number=household_number, city_id=city_id,
                                                        slum_id=slum_id)
            if not check_record:
                rhs_data = {}
                final_rhs_data = self.map_rhs_key(rhs_data, rhs_from_avni)
                final_rhs_data.update({'rhs_uuid': HH_data['ID']})
                update_record = HouseholdData.objects.create(household_number=household_number, slum_id=slum_id, city_id=city_id, submission_date=submission_date, rhs_data=final_rhs_data, created_date=created_date)
                print('Household record created for', slum_name, household_number)
            else:
                rhs_data = check_record.values_list('rhs_data', flat=True)[0]
                if rhs_data is None or len(rhs_data) == 0:
                    rhs_data = {}
                final_rhs_data = self.map_rhs_key(rhs_data, rhs_from_avni)
                final_rhs_data.update({'rhs_uuid': HH_data['ID']})
                check_record.update(submission_date=submission_date, rhs_data=final_rhs_data, created_date=created_date)
                print('Household record updated for', slum_name, household_number)
        except Exception as e:
            print('second exception', slum_name, e)

    def SaveRhsData(self):  # checked
        pages, path = self.create_registrationdata_url()

        for i in range(pages):
            send_request = requests.get(self.base_url + path + '&page=' + str(i), headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_HH_data = json.loads(send_request.text)['content']
            for i in get_HH_data:
                if not i['Voided']:
                    self.registrtation_data(i)

    def update_rhs_data(self, subject_id, encounter_data):  # checked
        self.get_household_details(subject_id)
        try:
            get_record = HouseholdData.objects.filter(slum_id__name=self.slum, household_number=self.HH)
            if not get_record:
                print('Record not found for', self.HH)
                self.registrtation_data(self.get_HH_data)
            get_rhs_data = get_record.values_list('rhs_data', flat=True)[0]
            get_rhs_data.update(encounter_data)
            get_record.update(rhs_data=get_rhs_data)
            print('rhs record updated for', self.HH, self.slum)
        except Exception as e:
            print(e, self.HH)

    def create_mobilization_activity_url(self):  # checked
        latest_date = self.lastModifiedDateTime()
        mobilization_url_path = 'api/subjects?lastModifiedDateTime=' + latest_date + '&subjectType=New_Mobilization_Form'
        result = requests.get(self.base_url + mobilization_url_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_text = json.loads(result.text)['content']
        pages = json.loads(result.text)['totalPages']
        return pages, mobilization_url_path

    def CommunityMobilizationActivityData(self, data, slum_name, HH):  # checked

        activities = {'Samiti meeting1': 'Samitee meeting 1', 'Samiti meeting2': 'Samitee meeting 2',
                      'Samiti meeting3': 'Samitee meeting 3', 'Samiti meeting4': 'Samitee meeting 4',
                      'Samiti meeting5': 'Samitee meeting 5'}  # "Workshop for Women","Workshop for Boys","Workshop for Girls"}
        try:
            slum_id, city_id = self.get_city_slum_ids(slum_name)
            if data['Type of Activity'] in activities:
                activity = ActivityType.objects.filter(name=activities[data['Type of Activity']]).values_list('key', flat=True)[0]
            else:
                activity = ActivityType.objects.filter(name=data['Type of Activity']).values_list('key', flat=True)[0]
            check = CommunityMobilizationActivityAttendance.objects.filter(slum=slum_id, city=city_id, household_number=HH, activity_type_id=activity)
            if not check:
                save = CommunityMobilizationActivityAttendance.objects.create(slum_id=slum_id, city_id=city_id, 
                                                                                date_of_activity=dateparser.parse(data['Date of the activity conducted']).date(),
                                                                                activity_type_id=activity,
                                                                                household_number=HH,
                                                                                males_attended_activity=data['Number of Men present'] if 'Number of Men present' in data else 0,
                                                                                females_attended_activity=data['Number of Women present'] if 'Number of Women present' in data else 0,
                                                                                other_gender_attended_activity=data['Number of Other gender members present'] if 'Number of Other gender members present' in data else 0,
                                                                                girls_attended_activity=data['Number of Girls present'] if 'Number of Girls present' in data else 0,
                                                                                boys_attended_activity=data['Number of Boys present'] if 'Number of Boys present' in data else 0)
                print('record created for', HH, slum_name)
            else:
                update = check.update(date_of_activity=dateparser.parse(data['Date of the activity conducted']).date(),
                                    activity_type_id=activity, household_number=HH,
                                    males_attended_activity=data['Number of Men present'] if 'Number of Men present' in data else 0,
                                    females_attended_activity=data['Number of Women present'] if 'Number of Women present' in data else 0,
                                    other_gender_attended_activity=data['Number of Other gender members present'] if 'Number of Other gender members present' in data else 0,
                                    girls_attended_activity=data['Number of Girls present'] if 'Number of Girls present' in data else 0,
                                    boys_attended_activity=data['Number of Boys present'] if 'Number of Boys present' in data else 0)
                print('record updated for', HH, slum_name)
        except Exception as e:
            print(e, HH)

    def CommunityMobilizationData(self, data):  # checked

        try:
            slum_name = data['location']['Slum']
            activity_name = data['observations']['Type of Activity']
            date_of_activity = dateparser.parse(data['observations']['Date of Survey']).date()
            slum_id, city_id = self.get_city_slum_ids(slum_name)
            activity = ActivityType.objects.filter(name=data['observations']['Type of Activity']).values_list('key', flat=True)[0]

            l = ['Household numbers for which activity attended by girls',
                 'Household numbers for which activity attended by boys',
                 'Household numbers for which activity attended by female members',
                 'Household numbers for which activity attended by male members']
            household_list = []
            for i in l:
                if i in data['observations'] and data['observations'][i] != '0':
                    temp = data['observations'][i]
                    temp_lst = temp.split(',')
                    temp_lst = [i for i in temp_lst if i != ""]
                    household_list += temp_lst
            household_list = list(set(household_list))

            check = CommunityMobilization.objects.filter(slum=slum_id, activity_date=date_of_activity, activity_type_id=activity)
            if not check:
                save = CommunityMobilization.objects.create(slum_id=slum_id, household_number=household_list, activity_type_id=activity, activity_date=date_of_activity)
                print('record created for', slum_name)
            else:
                hh_lst = check.values_list('household_number', flat = True)[0]
                hh_lst = list(set(hh_lst))
                hh_lst = [i for i in hh_lst if i != ""]
                flag = False
                for i in household_list:
                    if i not in hh_lst:
                        flag = True
                        break
                    else:
                        continue
                if flag:
                    household_list = list(set(household_list + hh_lst))
                    check.update(household_number=household_list)
                    print('record updated for', slum_name, date_of_activity, activity_name)
                else:
                    print("Record Already Present For", slum_name)

        except Exception as e:
            print(e, data['ID'])

    def SaveCommunityMobilizationData(self):  # checked
        pages, path = self.create_mobilization_activity_url()
        for i in range(pages):
            send_request = requests.get(self.base_url + path + '&page=' + str(i), headers={'AUTH-TOKEN': self.get_cognito_token()})
            data = json.loads(send_request.text)['content']
            for j in data:
                if j['Voided'] == False:
                    self.CommunityMobilizationData(j)
                else:
                    pass

    def SaveFamilyFactsheetData(self):  # checked
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' + latest_date + '&encounterType=Family factsheet'
        result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        for i in range(get_page_count):
            send_request = requests.get(self.base_url + programEncounters_path + '&page=' + str(i), headers={'AUTH-TOKEN': self.get_cognito_token()})
            data = json.loads(send_request.text)['content']
            for j in data:
                if j['Voided'] == False and j['observations'] != {}:
                    a, slum, HH, d = self.get_household_details(j['Subject ID'])
                    self.FamilyFactsheetData(j, slum, HH)

    def FamilyFactsheetData(self, data, slum_name, HH):  # checked

        try:
            slum_id, city_id = self.get_city_slum_ids(slum_name)
            check_record = HouseholdData.objects.filter(household_number=HH, city_id=city_id, slum_id=slum_id)
            factsheetDate = ToiletConstruction.objects.filter(household_number=HH, slum_id=slum_id)
            if check_record:
                ff_data = check_record.values_list('ff_data', flat=True)[0]
                if ff_data is None or len(ff_data) == 0:
                    ff_data = {}
                else:
                    ff_data = check_record.values_list('ff_data', flat=True)[0]

                final_ff_data = self.map_ff_keys(ff_data, data['observations'])
                final_ff_data.update({'ff_uuid': data['ID']})
                check_record.update(ff_data=final_ff_data)
                factsheet_done_date = dateparser.parse(data['audit']['Last modified at']).date()
                if 'Where the individual toilet is connected ?' in data['observations']:
                    if data['observations']['Where the individual toilet is connected ?'] != 'Not connected':
                        toilet_connected_to = factsheet_done_date
                    else:
                        toilet_connected_to = None
                if 'Use of toilet' in data['observations']:
                    if data['observations']['Use of toilet'] != None:
                        use_of_toilet = factsheet_done_date
                    else:
                        use_of_toilet = None
                factsheetDate.update(factsheet_done=factsheet_done_date, toilet_connected_to=toilet_connected_to, use_of_toilet=use_of_toilet)
                print('FF record updated for', slum_name, HH)
            else:
                ff_data = {}
                subject_id = data['Subject ID']
                send_request2 = requests.get(self.base_url + 'api/subject/' + subject_id, headers={'AUTH-TOKEN': self.get_cognito_token()})
                get_HH_data = json.loads(send_request2.text)
                self.registrtation_data(get_HH_data)
                get_reocrd = HouseholdData.objects.filter(household_number=HH, slum_id=slum_id, city_id=city_id)
                final_ff_data = self.map_ff_keys(ff_data, data['observations'])
                final_ff_data.update({'ff_uuid': data['ID']})
                get_reocrd.update(ff_data=final_ff_data)
                factsheet_done_date = dateparser.parse(data['audit']['Last modified at']).date()
                if 'Where the individual toilet is connected ?' in data['observations']:
                    if data['observations']['Where the individual toilet is connected ?'] != 'Not connected':
                        toilet_connected_to = factsheet_done_date
                    else:
                        toilet_connected_to = None
                if 'Use of toilet' in data['observations']:
                    if data['observations']['Use of toilet'] != None:
                        use_of_toilet = factsheet_done_date
                    else:
                        use_of_toilet = None

                factsheetDate.update(factsheet_done=factsheet_done_date, toilet_connected_to=toilet_connected_to, use_of_toilet=use_of_toilet)
                print('FF record updated for', slum_name, HH)
        except Exception as e:
            print(e)

    def SaveDailyReportingdata(self):  # checked
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/programEncounters?lastModifiedDateTime=' + latest_date + '&encounterType=Daily Reporting'
        result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})

        get_page_count = json.loads(result.text)['totalPages']
        for i in range(get_page_count):
            send_request = requests.get(self.base_url + programEncounters_path + '&page=' + str(i), headers={'AUTH-TOKEN': self.get_cognito_token()})

            data = json.loads(send_request.text)['content']
            for j in data:
                if j['Voided'] == False and j['observations'] != {}:
                    a, slum_id, HH, d = self.get_household_details(j['Subject ID'])
                    self.DailyReportingData(j['observations'], slum_id, HH)


    def DailyReportingData(self, data, slum, HH):  # checked
        slum_id, city_id = self.get_city_slum_ids(slum)

        phase_one_materials = ['Date on which bricks are given', 'Date on which sand is given',
                            'Date on which crush sand is given', 'Date on which river sand is given',
                            'Date on which cement is given']
        phase_two_materials = ['Date on which other hardware items are given', 'Date on which pan is given',
                            'Date on which Tiles are given']

        phase_one_material_dates = [data[i] for i in phase_one_materials if i in data]
        phase_two_material_dates = [data[i] for i in phase_two_materials if i in data]

        try:
            if 'Date on which agreement is cancelled' in data:
                agreement_cancelled = True
            else:
                agreement_cancelled = False

            if 'Date of agreement' in data:
                agreement_date = dateparser.parse(data['Date of agreement']).date()
            else:
                agreement_date = None
            if 'Date on which septic tank is given' in data:
                septic_tank_date = dateparser.parse(data['Date on which septic tank is given']).date()
            else:
                septic_tank_date = None

            if len(phase_one_material_dates) > 0 and not(agreement_cancelled): # Checking if agreement not cancelled.
                phase_one_material_dates.sort(reverse = True)
                phase_one_material_date = dateparser.parse(phase_one_material_dates[0]).replace(tzinfo=None)
            else:
                phase_one_material_date = None

            if len(phase_two_material_dates) > 0 and not agreement_cancelled:  # Checking if agreement not cancelled.
                phase_two_material_dates.sort(reverse = True)
                phase_two_material_date = dateparser.parse(phase_two_material_dates[0]).replace(tzinfo=None)
            else:
                phase_two_material_date = None

            if 'Date on which door is given' in data and not agreement_cancelled:    # Checking if agreement not cancelled.
                phase_three_material_date = dateparser.parse(data['Date on which door is given']).date()
            else:
                phase_three_material_date = None

            if 'Date on which toilet construction is complete' in data:
                completion_date = dateparser.parse(data['Date on which toilet construction is complete']).date()
            else:
                completion_date = None

            # Checking if agreement cancelled because sifting data question appears only when the agreement cancelled .

            if agreement_cancelled:

                # if only phase 1 material is given.
                if 'House numbers of houses where PHASE 1 material bricks, sand and cement is given' in data: 
                    p1_material_shifted_to = int(data['House numbers of houses where PHASE 1 material bricks, sand and cement is given'])
                else:
                    p1_material_shifted_to = None

                # if only phase 2 material is given.
                if 'House numbers of houses where PHASE 2 material Hardware is given' in data :
                    p2_material_shifted_to = int(data['House numbers of houses where PHASE 2 material Hardware is given'])
                else:
                    p2_material_shifted_to = None

                # if only phase 3 material is given.
                if 'House numbers where material is shifted - 3rd Phase' in data:
                    p3_material_shifted_to = int(data['House numbers where material is shifted - 3rd Phase'])
                else:
                    p3_material_shifted_to = None

                # if only Septic Tank is given.
                if 'House numbers of houses where Septic Tank is given' in data:
                    st_material_shifted_to = int(data['House numbers of houses where Septic Tank is given'])
                else:
                    st_material_shifted_to = None
            else:
                # if Agreement not cancel then all shifting question having None as answer.
                p1_material_shifted_to = p2_material_shifted_to = p3_material_shifted_to = st_material_shifted_to = None

            if 'Comment if any ?' in data:
                comment_ = data['Comment if any ?']
            else:
                comment_ = None

            # if 'Date on whcih toilet is connected to drainage line' in data and data['Date on whcih toilet is connected to drainage line'] != None:
            #    toilet_connected_to = dateparser.parse(data['Date on whcih toilet is connected to drainage line']).date()
            # else:toilet_connected_to= None
            # if 'Whether toilet is in use or not?' in data :
            #    toilet_in_use = data['Whether toilet is in use or not?']
            # else:toilet_in_use = None
            # if 'Date on which toilet construction is complete' in data and data['Date on which toilet construction is complete'] != None and toilet_in_use == 'Yes':
            #    use_of_toilet = dateparser.parse(data['Date on which toilet construction is complete']).date()
            # else :  use_of_toilet = None
            if completion_date is not None:
                status = 6  # completed
            elif (phase_one_material_date != None or phase_two_material_date != None or phase_three_material_date != None) and not(agreement_cancelled):
                status = 5  # under construction
            elif (agreement_date is not None and (phase_one_material_date == None and phase_two_material_dates == None and phase_three_material_date == None) and not(agreement_cancelled)):
                status = 3  # material not given
            elif agreement_cancelled == True:
                status = 2  # agreement cancle
            else:
                status = None
            check_record = ToiletConstruction.objects.filter(household_number=HH, slum_id=slum_id)
            if len(data) > 1:
                if not check_record:
                    create = ToiletConstruction.objects.create(household_number=HH, slum_id=slum_id,
                                                               agreement_date=agreement_date,
                                                               agreement_cancelled=agreement_cancelled,
                                                               septic_tank_date=septic_tank_date,
                                                               phase_one_material_date=phase_one_material_date,
                                                               phase_two_material_date=phase_two_material_date,
                                                               phase_three_material_date=phase_three_material_date,
                                                               completion_date=completion_date,
                                                               status=status,
                                                               p1_material_shifted_to=p1_material_shifted_to,
                                                               p2_material_shifted_to=p2_material_shifted_to,
                                                               p3_material_shifted_to=p3_material_shifted_to,
                                                               st_material_shifted_to=st_material_shifted_to,
                                                               comment=comment_)
                    print('Construction status created for', HH, slum_id)
                else:
                    check_record.update(agreement_date=agreement_date,
                                        agreement_cancelled=agreement_cancelled,
                                        septic_tank_date=septic_tank_date,
                                        phase_one_material_date=phase_one_material_date,
                                        phase_two_material_date=phase_two_material_date,
                                        phase_three_material_date=phase_three_material_date,
                                        completion_date=completion_date,
                                        status=status,
                                        p1_material_shifted_to=p1_material_shifted_to,
                                        p2_material_shifted_to=p2_material_shifted_to,
                                        p3_material_shifted_to=p3_material_shifted_to,
                                        st_material_shifted_to=st_material_shifted_to,
                                        comment=comment_)

                    print('Construction status updated for', HH, slum_id)
        except Exception as e:
            print(e, HH)

    def update_construction_status(self, slum_id):

        slum_list = ToiletConstruction.objects.filter(slum_id=slum_id)
        # __electoral_ward_id__administrative_ward_id__city_id =city_id)
        for i in slum_list:
            if i.completion_date != '':
                h = ToiletConstruction.objects.filter(household_number=i.household_number, slum_id=i.slum_id).update(
                    status='06')
            if i.phase_one_material_date != '' or i.phase_two_material_date != '' or i.phase_three_material_date != '':
                h = ToiletConstruction.objects.filter(household_number=i.household_number, slum_id=i.slum_id).update(
                    status='05')
            if i.phase_one_material_date != '' and (
                    i.phase_two_material_date == '' and i.phase_three_material_date == ''):
                h = ToiletConstruction.objects.filter(household_number=i.household_number, slum_id=i.slum_id).update(
                    status='04')
            if i.agreement_date != '' and (
                    i.phase_one_material_date == '' and i.phase_two_material_date == '' and i.phase_three_material_date == ''):
                h = ToiletConstruction.objects.filter(household_number=i.household_number, slum_id=i.slum_id).update(
                    status='03')
        print('done')

    def SanitationEncounterData(self):  # checked
        latest_date = self.lastModifiedDateTime()
        programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date + '&encounterType=' + 'Sanitation'
        result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        try:
            get_page_count = json.loads(result.text)['totalPages']
        except Exception as e:
            get_page_count = 0
            print(e, result.status_code, ', No data for date -', latest_date)
        return get_page_count, programEncounters_path

    def followup_data_sanitation(self, subject_id, sanitation_data):  # checked
        self.get_household_details(subject_id)
        try:
            get_record = FollowupData.objects.filter(household_number=self.HH, slum_id__name=self.slum)
            if len(get_record) <= 0:
                slum_id, city_id = self.get_city_slum_ids(self.slum)
                create_record = FollowupData.objects.create(household_number=self.HH, slum_id=slum_id,
                                                            city_id=city_id, submission_date=self.SubmissionDate,
                                                            followup_data=sanitation_data,
                                                            created_date=self.get_HH_data['audit']['Created at'],
                                                            flag_followup_in_rhs=False)
            else:
                for i in get_record:
                    get_followup_data = i.followup_data
                    get_followup_data.update(sanitation_data)
                    get_record.update(followup_data=get_followup_data, submission_date=dateparser.parse(self.SubmissionDate))
        except Exception as e:
            print(e, self.HH)

    def SaveFollowupData(self):  # checked
        pages, path = self.SanitationEncounterData()

        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&page=' + str(i),
                                            headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                if len(data) > 0:
                    for j in data:
                        if not j['Voided'] and j['observations'] != {}:
                            sanitation_data = self.map_sanitation_keys(j['observations'])
                            sanitation_data.update({'submission_date': j['audit']['Last modified at']})
                            self.update_rhs_data(j['Subject ID'], sanitation_data)
                            self.followup_data_sanitation(j['Subject ID'], sanitation_data)
                else:
                    print('No data')
        except Exception as e:
            print(e)

    def WaterEncounterData(self):  # checked
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date + '&encounterType=' + 'Water'
            result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return get_page_count, programEncounters_path

    def SaveWaterData(self):  # checked
        pages, path = self.WaterEncounterData()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&page=' + str(i),
                                            headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    if not j['Voided'] and j['observations'] != {}:
                        water_data = j['observations']
                        if 'Type of water connection ?' in water_data:
                            water_data['group_el9cl08/Type_of_water_connection'] = water_data[
                                'Type of water connection ?']
                            del water_data['Type of water connection ?']
                        water_data.update({'Last_modified_date': j['audit']['Last modified at']})
                        self.update_rhs_data(j['Subject ID'], water_data)
        except Exception as e:
            print(e)

    def WasteEncounterData(self):  # checked
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date + '&encounterType=' + 'Waste'
            result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return get_page_count, programEncounters_path

    def SaveWasteData(self):  # checked
        pages, path = self.WasteEncounterData()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&page=' + str(i), headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    if not j['Voided'] and j['observations'] != {}:
                        waste_data = j['observations']
                        if 'How do you dispose your solid waste ?' in waste_data:
                            waste_data['group_el9cl08/Facility_of_solid_waste_collection'] = waste_data[
                                'How do you dispose your solid waste ?']
                            del waste_data['How do you dispose your solid waste ?']
                        waste_data.update({'Last_modified_date': j['audit']['Last modified at']})
                        self.update_rhs_data(j['Subject ID'], waste_data)
        except Exception as e:
            print(e)

    def PropertyTaxEncounterData(self):  # checked
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date + '&encounterType=' + 'Property tax'
            result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return (get_page_count, programEncounters_path)

    def SavePropertyTaxData(self):  # checked
        pages, path = self.PropertyTaxEncounterData()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&page=' + str(i), headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    if not j['Voided'] and j['observations'] != {}:
                        tax_data = j['observations']
                        tax_data.update({'Last_modified_date': j['audit']['Last modified at']})
                        self.update_rhs_data(j['Subject ID'], tax_data)
        except Exception as e:
            print(e)

    def ElectricityEncounterData(self):  # checked
        latest_date = self.lastModifiedDateTime()
        for i in direct_encountes:
            programEncounters_path = 'api/encounters?lastModifiedDateTime=' + latest_date + '&encounterType=' + 'Electricity'
            result = requests.get(self.base_url + programEncounters_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
            get_page_count = json.loads(result.text)['totalPages']
            return get_page_count, programEncounters_path

    def SaveElectricityData(self):  # checked
        pages, path = self.ElectricityEncounterData()
        try:
            for i in range(pages):
                send_request = requests.get(self.base_url + path + '&page=' + str(i), headers={'AUTH-TOKEN': self.get_cognito_token()})
                data = json.loads(send_request.text)['content']
                for j in data:
                    if not j['Voided'] and j['observations'] != {}:
                        electricity_data = j['observations']
                        electricity_data.update({'Last_modified_date': j['audit']['Last modified at']})
                        self.update_rhs_data(j['Subject ID'], electricity_data)
        except Exception as e:
            print(e)

    def SaveDataFromIds(self):

        IdList = ['673a778a-1a39-4708-9415-4755ee0143aa']  # 'cda4ce0e-f05c-4b49-ac6e-ed160eba1940']

        ''' There Are Three Types Of Flag We Use
        1 - Subject Type
        2 - Encounters
        3 - Program Encounter
        Please provide flag when sync data using UUIDs'''

        flag = 'Subject Type'

        for i in IdList:
            try:
                if flag == 'Subject Type':
                    RequestHouseholdRegistration = requests.get(self.base_url + 'api/subject/' + i, headers={'AUTH-TOKEN': self.get_cognito_token()})
                    if RequestHouseholdRegistration.status_code == 200:
                        data = json.loads(RequestHouseholdRegistration.text)
                        if data['Subject type'] == 'Household':
                            if not data['Voided']:
                                self.registrtation_data(data)
                        if data['Subject type'] == 'New_Mobilization_Form':
                            if not data['Voided']:
                                self.CommunityMobilizationData(data)
                    else:
                        print(i, 'uuid is not accessible')
                elif flag == 'Encounters':
                    RequestEncounter = requests.get(self.base_url + 'api/encounter/' + i, headers={'AUTH-TOKEN': self.get_cognito_token()})
                    if RequestEncounter.status_code == 200:
                        data = json.loads(RequestEncounter.text)
                        if data['Encounter type'] == 'Sanitation' and (
                                data['observations'] != {} and data['Voided'] == False):
                            sanitation = self.map_sanitation_keys(data['observations'])  # sanitation data
                            sanitation.update({'Last_modified_date': data['audit']['Last modified at']})
                            self.update_rhs_data(data['Subject ID'], sanitation)  # sanitation data
                            self.followup_data_sanitation(data['Subject ID'], sanitation)  # sanitation data

                        elif data['Encounter type'] == 'Waste' and (
                                data['observations'] != {} or data['Voided'] == False):
                            waste = data['observations']
                            if 'How do you dispose your solid waste ?' in waste:
                                waste['group_el9cl08/Facility_of_solid_waste_collection'] = waste['How do you dispose your solid waste ?']
                                del waste['How do you dispose your solid waste ?']
                            waste.update({'Last_modified_date': data['audit']['Last modified at']})
                            self.update_rhs_data(data['Subject ID'], waste)  # waste  data

                        elif data['Encounter type'] == 'Water' and (
                                data['observations'] != {} or data['Voided'] == False):
                            water = data['observations']
                            if 'Type of water connection ?' in water:
                                water['group_el9cl08/Type_of_water_connection'] = water['Type of water connection ?']
                                del water['Type of water connection ?']
                            water.update({'Last_modified_date': data['audit']['Last modified at']})
                            self.update_rhs_data(data['Subject ID'], water)  # water  data

                        elif data['Encounter type'] == 'Property tax' and (
                                data['observations'] != {} or data['Voided'] == False):
                            tax = data['observations']  # tax  data
                            tax.update({'Last_modified_date': data['audit']['Last modified at']})
                            self.update_rhs_data(data['Subject ID'], tax)  # tax  data

                        elif data['Encounter type'] == 'Electricity' and (
                                data['observations'] != {} or data['Voided'] == False):
                            electricity = data['observations']  # electricity  data
                            electricity.update({'Last_modified_date': data['audit']['Last modified at']})
                            self.update_rhs_data(data['Subject ID'], electricity)  # electricity data

                        elif data['Encounter type'] == 'Daily Mobilization Activity' and (
                                data['observations'] != {} or data['Voided'] == False):
                            self.get_household_details(data['Subject ID'])
                            self.CommunityMobilizationActivityData(data['observations'], self.slum, self.HH)  # CommunityMobilization
                    else:
                        print(i, 'uuid is not accessible')
                elif flag == 'Program Encounter':
                    RequestProgramEncounter = requests.get(self.base_url + 'api/programEncounter/' + i, headers={'AUTH-TOKEN': self.get_cognito_token()})

                    if RequestProgramEncounter.status_code == 200:
                        data = json.loads(RequestProgramEncounter.text)
                        a, slum_name, HH, d = self.get_household_details(data['Subject ID'])
                        if data['Encounter type'] == 'Family factsheet' and (
                                data['observations'] != {} or data['Voided'] == False):
                            self.FamilyFactsheetData(data, slum_name, HH)
                        elif (data['Encounter type'] == 'Daily Reporting' or data[
                            'Encounter type'] == 'Household Level Daily Reporting') and (
                                data['observations'] != {} or data['Voided'] == False):
                            self.DailyReportingData(data['observations'], slum_name, HH)
                    else:
                        print(i, 'uuid is not accessible')

                else:
                    print("Invalid_Flag")
            except Exception as e:
                print(e)

    # methods for covid data >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    def SaveCovidData(self):  # checked
        self.SaveRhsData('covid')

    def ProcessCovidData(self, HH_data):

        covid_uuid = HH_data['ID']
        slum_name = HH_data['location']['Slum']
        slum_id, city_id = self.get_city_slum_ids(slum_name)
        audit = HH_data['audit']
        date_of_survey = dateparser.parse(audit['Created at']).date()
        last_modified_date = dateparser.parse(audit['Last modified at']).date()

        observation = HH_data['observations']

        for i in observation.keys():
            if i == 'Gender_n':
                observation['Gender'] = observation['Gender_n']
                del observation['Gender_n']
            elif i == 'Mobile number used for vaccination registration':
                observation['Registered Phone Number'] = observation['Mobile number used for vaccination registration'][
                    'phoneNumber']
                del observation['Mobile number used for vaccination registration']
            elif i == 'Do you have any disease?':
                temp = " ".join(observation['Do you have any disease?'])
                observation['Do you have any disease?'] = temp
            elif i == 'Have you registered for covid vaccination?':
                observation['Have you registered for covid vaccination?'] = observation[
                    'Have you registered for covid vaccination?'].capitalize()
            elif i == 'Have you even been infected with corona?':
                observation['Have you even been infected with corona?'] = observation[
                    'Have you even been infected with corona?'].capitalize()
            elif i == 'Have you taken first dose?':
                observation['Have you taken first dose?'] = observation['Have you taken first dose?'].capitalize()
            elif i == 'Have you taken second dose?':
                observation['Have you taken second dose?'] = observation['Have you taken second dose?'].capitalize()

        observation['date_of_survey'] = date_of_survey
        observation['last_modified_date'] = last_modified_date

        observation['Covid_uuid'] = covid_uuid
        observation['city_id'] = city_id
        observation['slum_id'] = slum_id

        lst = ['Aadhar number', 'Name of the surveyor', 'Family member name', 'Persons age',
               'Are you pregnant or lactating mother?', 'Have you registered for covid vaccination?',
               'Have you taken first dose?', 'Date of first dose.', 'Have you taken second dose?',
               'Second dose date.', 'Have you even been infected with corona?',
               'If corona infected, how many days it had been since infection?',
               'Are you willing to get vaccinated?', 'If not willing to take vaccine, why?', 'Note',
               'Do you have any disease?',
               'If yes for other disease, please mention here', 'Registered Phone Number',
               'Which of the below vaccine taken?']

        for i in lst:
            if i not in observation:
                observation[i] = None

        if observation['Date of first dose.'] != None:
            observation['Date of first dose.'] = dateparser.parse(observation['Date of first dose.']).date()
        if observation['Second dose date.'] != None:
            observation['Second dose date.'] = dateparser.parse(observation['Second dose date.']).date()

        del observation['First name']
        return (observation)

    def RegistrationCovidData(self, HH_data):  # checked

        if len(HH_data['Groups']) > 0:
            household_number1 = self.SaveCovidDataFromIds1(HH_data['Groups'])
        else:
            household_number1 = 9999

        final_dict = self.ProcessCovidData(HH_data)
        self.slum = final_dict['slum_id']

        try:
            if CovidData.objects.filter(covid_uuid=final_dict['Covid_uuid']).exists() == False:

                c = CovidData(household_number=household_number1,
                              slum=Slum.objects.get(id=self.slum),
                              city=final_dict['city_id'],
                              covid_uuid=final_dict['Covid_uuid'],
                              surveyor_name=final_dict['Name of the surveyor'],
                              date_of_survey=final_dict['date_of_survey'],
                              last_modified_date=final_dict['last_modified_date'],
                              family_member_name=final_dict['Family member name'],
                              gender=final_dict['Gender'], age=final_dict['Persons age'],
                              aadhar_number=final_dict['Aadhar number'],
                              do_you_have_any_other_disease=final_dict['Do you have any disease?'],
                              if_any_then_which_disease=final_dict['If yes for other disease, please mention here'],
                              preganant_or_lactating_mother=final_dict['Are you pregnant or lactating mother?'],
                              registered_for_covid_vaccination=final_dict['Have you registered for covid vaccination?'],
                              registered_phone_number=final_dict['Registered Phone Number'],
                              take_first_dose=final_dict['Have you taken first dose?'],
                              first_dose_date=final_dict['Date of first dose.'],
                              vaccine_name=final_dict['Which of the below vaccine taken?'],
                              take_second_dose=final_dict['Have you taken second dose?'],
                              second_dose_date=final_dict['Second dose date.'],
                              corona_infected=final_dict['Have you even been infected with corona?'],
                              if_corona_infected_days=final_dict[
                                  'If corona infected, how many days it had been since infection?'],
                              willing_to_vaccinated=final_dict['Are you willing to get vaccinated?'],
                              if_not_why=final_dict['If not willing to take vaccine, why?'], note=final_dict['Note'])

                c.save()
                print("Record save successfully", self.slum)

            elif CovidData.objects.filter(covid_uuid=final_dict['Covid_uuid'],
                                          last_modified_date=final_dict['last_modified_date']).exists() == False:

                c = CovidData(household_number=household_number1,
                              slum=Slum.objects.get(id=self.slum),
                              city=final_dict['city_id'],
                              covid_uuid=final_dict['Covid_uuid'],
                              surveyor_name=final_dict['Name of the surveyor'],
                              date_of_survey=final_dict['date_of_survey'],
                              last_modified_date=final_dict['last_modified_date'],
                              family_member_name=final_dict['Family member name'],
                              gender=final_dict['Gender'], age=final_dict['Persons age'],
                              aadhar_number=final_dict['Aadhar number'],
                              do_you_have_any_other_disease=final_dict['Do you have any disease?'],
                              if_any_then_which_disease=final_dict['If yes for other disease, please mention here'],
                              preganant_or_lactating_mother=final_dict['Are you pregnant or lactating mother?'],
                              registered_for_covid_vaccination=final_dict['Have you registered for covid vaccination?'],
                              registered_phone_number=final_dict['Registered Phone Number'],
                              take_first_dose=final_dict['Have you taken first dose?'],
                              first_dose_date=final_dict['Date of first dose.'],
                              vaccine_name=final_dict['Which of the below vaccine taken?'],
                              take_second_dose=final_dict['Have you taken second dose?'],
                              second_dose_date=final_dict['Second dose date.'],
                              corona_infected=final_dict['Have you even been infected with corona?'],
                              if_corona_infected_days=final_dict[
                                  'If corona infected, how many days it had been since infection?'],
                              willing_to_vaccinated=final_dict['Are you willing to get vaccinated?'],
                              if_not_why=final_dict['If not willing to take vaccine, why?'], note=final_dict['Note'])

                c.save()
                print("Record save successfully", self.slum)

            else:
                print("Record Already Present")

        except Exception as e:
            print(e)

    def SaveCovidDataFromIds1(self, id):
        i = id[0]
        dct = dict()
        if i in dct:
            houshold_number = dct[i]
        else:
            RequestHouseholdRegistration = requests.get(self.base_url + 'api/subject/' + i,
                                                        headers={'AUTH-TOKEN': self.get_cognito_token()})
            if RequestHouseholdRegistration.status_code == 200:
                data = json.loads(RequestHouseholdRegistration.text)

                slum_name = data['location']['Slum']
                s_id, c_id = self.get_city_slum_ids(slum_name)

                dct[i] = data['observations']['First name']
                record_f = HouseholdData.objects.filter(slum_id=s_id, city_id=c_id, household_number=str(
                    int(data['observations']['First name']))).exists()

                if record_f == False:
                    self.registrtation_data(data)

                return (int(data['observations']['First name']))

            else:
                return 'error'

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
