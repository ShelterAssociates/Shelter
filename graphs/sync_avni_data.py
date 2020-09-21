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

final_rhs_data = {"_notes": [], # Note // Comment if any ?
            "group_el9cl08/Number_of_household_members": "", # Number of household members
            "group_oi8ts04/OD1": "",
            "_bamboo_dataset_id":"",
            "_tags": [],
            "group_oi8ts04/Have_you_applied_for_individua":"",
            "_xform_id_string": "",
            "meta/instanceID":"",
            "end": "",
            "Enter_household_number_again":"", # Househhold number
            "group_oi8ts04/Current_place_of_defecation": "",
            "start": "",
            "_geolocation": [],
            "group_el9cl08/Type_of_structure_of_the_house":"", # Type of structure of the house_1
            "_status": "",
            "formhub/uuid": "",
            "meta/deprecatedID": "",
            "Name_s_of_the_surveyor_s": "", # Name of the surveyor
            "Household_number": "", # First name
            "group_el9cl08/Type_of_water_connection": "",
            "_uuid": "",
            "group_el9cl08/Facility_of_solid_waste_collection": "",
            "group_el9cl08/Ownership_status_of_the_house": "", # Ownership status of the house_1
            "_submitted_by": "",
            "group_el9cl08/Does_any_household_m_n_skills_given_below": "",
            "Date_of_survey": "", # Date of Survey
            "admin_ward": "",
            "slum_name": "",
            "group_el9cl08/House_area_in_sq_ft": "", # House area in sq.ft.
            "group_oi8ts04/C3": "",
            "group_oi8ts04/C2": "",
            "__version__": "",
            "group_og5bx85/Type_of_survey": "RHS",
            "_submission_time": "",
            "group_og5bx85/Full_name_of_the_head_of_the_household": "", # Full name of the head of the household
            "_attachments": [],
            "group_el9cl08/Do_you_have_any_girl_child_chi": "", # Do you have any girl child / children under the age of 18?
            "Type_of_structure_occupancy": "", # Type of structure occupancy_1
            "group_oi8ts04/Are_you_interested_in_an_indiv": "",
            "_id": int ,
            "group_oi8ts04/If_no_why": "",
            "Type_of_unoccupied_house":"", # Type of unoccupied house_1
            "Parent_household_number": "", # Parent household number
            "Plus code of the house":"",
            "Name of surveyor who updated the data":"",
            "If shop, type of occupancy ?":"",
            "Type of shop":"",
            "If tenant, write name of owner.":"",
            "Enter the 10 digit mobile number":"",
            "Do you have addhar card?":"",
            "Aadhar number":"",
            "Relation of aadhar card holder with head of the family.":"",
            "Photo of Adhar card":"",
            "What is your native place (village / town / city) ?":"",
            "What is your native state?":"",
            "Colour of ration card":"",
            "Photo of ration card,":"",
            "Do you have a Zopadpatti card ?":"",
            "Write Zopadpatti card number":"",
            "Zopadpatti card number (text)":"",
            "Total number of male members (including children)":"",
            "Total number of female members (including children)":"",
            "Total number of third gender members (including children)":"",
            "Number of children under 5 yrs.":"",
            "Number of persons above 60 yrs.":"",
            "How many ? ( Count )":"",
            "Is any family member physically / mentally challenged?":"",
            "Is there any widow woman in the household?":"",
            "Is there any seperated woman in the household ?":"",
           " Number of rooms ?":"",
        }

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

    def create_registrationdata_url(self):
        latest_date = self.lastModifiedDateTime()
        household_path = 'api/subjects?lastModifiedDateTime=' + latest_date + '&subjectType=Household'
        result = requests.get(self.base_url + household_path,
                         headers= {'AUTH-TOKEN':self.get_cognito_token() })
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count, household_path)

    def access_registrtation_data(self):
        totalPages,path = self.create_registrationdata_url()
        for i in range(totalPages)[1:2]:
            send_request = requests.get(self.base_url+ path +'&'+ str(i),headers={'AUTH-TOKEN':self.get_cognito_token()})
            household_data = json.loads(send_request.text)['content']
            for j in household_data[1:5]:
                rhs_data = j['observations']
                household_number = str(int(rhs_data['First name']))
                created_date = j['Registration date']
                submission_date = (j['audit']['Last modified at']) # use last modf date
                slum_name = j['location']['Slum']
                for k,v in final_rhs_data.items():
                    if k == '_notes' and 'Note' in rhs_data:
                        final_rhs_data[k] = rhs_data['Note']
                    elif k == 'Enter_household_number_again' and 'Househhold number' in rhs_data:
                        final_rhs_data[k] = rhs_data['Househhold number']
                    elif k == 'Name_s_of_the_surveyor_s' and 'Name of the surveyor' in rhs_data:
                        final_rhs_data[k] = rhs_data['Name of the surveyor']
                    elif k == "Household_number" and 'First name' in rhs_data:
                        final_rhs_data[k] = rhs_data['First name']
                    elif k == 'group_el9cl08 / Ownership_status_of_the_house' and 'Ownership status of the house_1' in rhs_data:
                        final_rhs_data[k] = rhs_data['Ownership status of the house_1']
                    elif k == 'Date_of_survey' and 'Date of Survey' in rhs_data:
                        final_rhs_data[k] = rhs_data['Date of Survey']
                    elif k == 'group_el9cl08/House_area_in_sq_ft' and 'House area in sq.ft.' in rhs_data:
                        final_rhs_data[k] = rhs_data['House area in sq.ft.']
                    elif k == 'group_og5bx85/Full_name_of_the_head_of_the_household' and 'Full name of the head of the household' in rhs_data:
                        final_rhs_data[k] = rhs_data['Full name of the head of the household']
                    elif k == 'group_el9cl08/Number_of_household_members' and 'Number of household members' in rhs_data:
                        final_rhs_data[k] = rhs_data['Number of household members']
                    elif k == 'Type_of_unoccupied_house' and 'Type of unoccupied house_1' in rhs_data:
                        final_rhs_data[k] = rhs_data['Type of unoccupied house_1']
                    elif k == 'group_el9cl08 / Type_of_structure_of_the_house' and ' Type of structure of the house_1' in rhs_data:
                        final_rhs_data[k] = rhs_data[' Type of structure of the house_1']
                    elif k == "Parent_household_number" and 'Parent household number' in rhs_data:
                        final_rhs_data[k] = rhs_data['Parent household number']
                    elif k == 'Type_of_structure_occupancy' and 'Type of structure occupancy_1' in rhs_data:
                        final_rhs_data[k] = rhs_data['Type of structure occupancy_1']
                    elif k == 'group_el9cl08/Do_you_have_any_girl_child_chi' and 'Do you have any girl child / children under the age of 18?' in rhs_data:
                        final_rhs_data[k] = rhs_data['Do you have any girl child / children under the age of 18?']
                    elif k in final_rhs_data and k in rhs_data:
                        final_rhs_data[k] = rhs_data[k]
                    else:
                        pass
                        # print(k,' not present in reocrd')
                try:
                    slum = Slum.objects.filter(name=slum_name).values_list('id','electoral_ward_id__administrative_ward__city__id')[0]
                    if slum :
                        slum_id, city_id = slum[0],slum[1]
                        # check_record = HouseholdData.objects.filter(household_number=household_number,city_id=city_id,slum_id=slum_id)
                        # if check_record:
                        #     pass
                        #     # get_record = HouseholdData.objects.get(household_number=household_number,city_id=city_id,slum_id=slum_id)
                        #     # get_record.submission_date = submission_date
                        #     # get_record.rhs_data = str(final_rhs_data)
                        #     # get_record.created_date = created_date
                        #     # get_record.save()
                        #     # print('record saved for',slum_name, household_number)
                        # else:
                        #     create_record = HouseholdData(household_number=household_number,slum_id=slum_id, city_id=city_id,
                        #             submission_date=submission_date,rhs_data=str(final_rhs_data),created_date=created_date)
                        #     create_record.save()
                        #     print('record created for ',household_number)
                except Exception as e:
                    print('4', e,slum_name, household_number)

    def create_encounterData_url(self):  #need to run for every encounter type
        encounter_path = 'api/encounters?lastModifiedDateTime=2020-07-01T00:00:00.000Z&encounter%20type=Water'
        result = requests.get(self.base_url + encounter_path,
                              headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count,encounter_path)

    def create_programEncounter_url(self):  #need to run for every program encounter type
        programEncounters_path = 'api/programEncounters?lastModifiedDateTime=2018-02-01T00:00:00.000Z&encounter%20type=Sanitation' #works
        result = requests.get(self.base_url + programEncounters_path,
                              headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count, programEncounters_path)

    def create_enrolmentData_url(self):  #need to run for every enrolment type
        # registration_with_id= 'api/subject/d65afb9f-d025-4982-af04-addbbee0216f' #(require uuid of any registration record)
        # programEncounter_with_id = 'api/programEncounter/' #(require uuid of any programEncounter record)
        # directEncounter_with_id = 'api/encounter/e92ec2d8-6e04-465d-80f1-f19bba4b7ee1' # (require uuid of any directEncounter record)
        # programEnrolment_with_id = 'api/enrolment/8' #(require uuid of any enrolment record)
        enrolments_path = 'api/enrolments?lastModifiedDateTime=2018-02-01T00:00:00.000Z&program=Property Tax' #works
        result = requests.get(self.base_url + enrolments_path, headers={'AUTH-TOKEN': self.get_cognito_token()})
        get_page_count = json.loads(result.text)['totalPages']
        return (get_page_count, enrolments_path)


# def send_request(request):
#     a = avni_sync()
#     z = a.access_registrtation_data()
#     return HttpResponse(json.dumps(z))