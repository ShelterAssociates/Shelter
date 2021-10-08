"""
Classes for data sync for toilet construction and community mobilization.
Sample:
from mastersheet.daily_reporting_sync import *
from django.contrib.auth.models import User
from master.models import *
user = User.objects.all().first()
slum = Slum.objects.filter(shelter_slum_code='273425261201').first()
t = ToiletConstructionSync(slum, user)

"""
from django.conf import settings
import datetime
from urllib import request as urllib2
import json
import re
from dateutil.parser import parse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from master.models import Survey, Slum, SURVEYTYPE_CHOICES
from .models import *


class DDSync(object):
    def __init__(self, slum, user):
        self.slum = slum
        self.user = user
        survey_id = '129'
        ff_survey_id = None
        try:
            surveys = Survey.objects.filter(city=slum.electoral_ward.administrative_ward.city,
                                           survey_type__in=[SURVEYTYPE_CHOICES[3][0]])
            if len(surveys) > 0:
                ff_survey_id = surveys[0].kobotool_survey_id
        except:
            pass
        self.survey_id = survey_id
        self.ff_survey_id = ff_survey_id
        self.survey_date = self.convert_datetime("2017-01-21T01:02:03")
        sync_info = KoboDDSyncTrack.objects.filter(slum=self.slum).order_by('-sync_date').first()
        if sync_info:
            self.survey_date = self.convert_datetime(str(timezone.localtime(sync_info.sync_date)))
        self.survey_record = None

    def convert_datetime(self, date_str):
        ret = parse_datetime(date_str)
        return ret

    def fetch_url(self, community_mobilization_flag):
        kobo_url = settings.KOBOCAT_FORM_URL + 'data/'+str(self.survey_id)
        kobo_url += '?format=json&query={"slum_name":"'+self.slum.shelter_slum_code +'"'
        kobo_url += ',"Was_any_Community_Mobilisation":"1" ' if community_mobilization_flag else ''
        kobo_url += ',"_submission_time":{"$gt":"%s"}}'
        return kobo_url

    def fetch_url_data(self, url):
        url = url.replace(" ",'')
        kobotoolbox_request = urllib2.Request(url)
        kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
        kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)

        res = urllib2.urlopen(kobotoolbox_request)
        # Read json data from kobotoolbox API
        html = res.read()
        records = json.loads(html)
        return records

    def fetch_kobo_data(self, community_mobilization_flag=False):
        url = self.fetch_url(community_mobilization_flag) % (str(self.survey_date).replace(' ','T'))
        self.survey_record = self.fetch_url_data(url)

    def fetch_kobo_FF_data(self):
        url_family_factsheet = settings.KOBOCAT_FORM_URL + 'data/' + str(self.ff_survey_id) + '?format=json'
        url_family_factsheet += '&query={"group_vq77l17/slum_name":"'+str(self.slum.shelter_slum_code)+'"'
        #url_family_factsheet += ',"_submission_time":{"$gt":"'+str(self.survey_date)+'"}'
        url_family_factsheet += '}&fields=["_submission_time","group_vq77l17/Household_number","group_ne3ao98/Where_the_individual_ilet_is_connected_to","group_ne3ao98/Use_of_toilet"]'
        formdict_family_factsheet = self.fetch_url_data(url_family_factsheet)
        return formdict_family_factsheet

    def update_sync_info(self, sync_date):
        try:
            KoboDDSyncTrack.objects.create(slum=self.slum,sync_date=sync_date,created_by=self.user)
        except Exception as e:
            print("Error creating record" + str(e))

class ToiletConstructionSync(DDSync):

    def __init__(self, slum, user):
        super(ToiletConstructionSync, self).__init__(slum, user)
        self.MAPPING = {"House_numbers_of_hou_Septic_Tank_is_given":"septic_tank_date", "House_numbers_of_hou_re_agreement_is_done":"agreement_date",
                        "House_numbers_of_hou_and_cement_is_given":"phase_one_material_date", "House_numbers_of_hou_al_Hardware_is_given":"phase_two_material_date",
                        "House_numbers_of_hou_HASE_3_Door_is_given":"phase_three_material_date", "House_numbers_of_hou_truction_is_complete": "completion_date",
                        #"House_numbers_where_tion_has_not_started":"", "House_numbers_where_ted_to_drainage_line":"",
                        "House_numbers_where_reement_is_cancelled":"agreement_cancelled"
                        }
        self.REGX_CHECK = {"House_numbers_where_ifted_from_HH_to_HH":"p1_material_shifted_to", "House_numbers_where_ifted_from_002":"p2_material_shifted_to","House_numbers_where_ifted_from_001":"p3_material_shifted_to","House_numbers_where_ifted_from":"st_material_shifted_to"}
        self.BOOL_CHECK = ["House_numbers_where_reement_is_cancelled"]

    def fetch_FF_data(self):
        formdict_family_factsheet = self.fetch_kobo_FF_data()
        for tmp_ff in formdict_family_factsheet:
            update_data = {}
            check_list = {'slum': self.slum, 'household_number': tmp_ff['group_vq77l17/Household_number']}
            tc, created = ToiletConstruction.objects.get_or_create(**check_list)
            if ('group_ne3ao98/Use_of_toilet' in tmp_ff and tmp_ff['group_ne3ao98/Use_of_toilet'] in ['01','02' ,'03', '04', '05', '06']):
                update_data['use_of_toilet'] = self.convert_datetime(tmp_ff['_submission_time'])
            if ('group_ne3ao98/Where_the_individual_ilet_is_connected_to' in tmp_ff and tmp_ff['group_ne3ao98/Where_the_individual_ilet_is_connected_to'] in ['01', '03']):
                update_data['toilet_connected_to'] = self.convert_datetime(tmp_ff['_submission_time'])
            if not tc.factsheet_done:
                update_data['factsheet_done'] = self.convert_datetime(tmp_ff['_submission_time'])
            ToiletConstruction.objects.filter(**check_list).update(**update_data)

    def fetch_data(self):
        #Fetch family factsheet data and store to ToiletConstruciton
        self.fetch_FF_data()
        #Fetch Daily reporting data and store to ToiletConstruction
        self.fetch_kobo_data()
        sync_date = ''
        flag = False
        for record in self.survey_record:
            submission_date = self.convert_datetime(record['_submission_time'])
            if not flag and '_submission_time' in record:
                sync_date = submission_date

            for kobofield,modelfield in self.REGX_CHECK.items():
                if kobofield in record:
                    houses = record[kobofield].split(',')
                    for house in houses:
                        house_data = re.findall('from([0-9]{1,4})to([0-9]{1,4})', house)
                        if len(house_data[0][0]) < 5:
                            check_list = {'slum':self.slum, 'household_number':house_data[0][0]}
                            tc, created = ToiletConstruction.objects.get_or_create(**check_list)
                            update_data ={}
                            update_data[modelfield] = house_data[0][1]
                            tc = ToiletConstruction.objects.filter(**check_list)
                            ToiletConstruction.objects.filter(**check_list).update(**update_data)
                            for toilet_const in tc:
                                toilet_const.save()
                        flag=True

            for kobofield, modelfield in self.MAPPING.items():
                if kobofield in record:
                    houses = record[kobofield].split(',')

                    for house in houses:
                        if len(house) < 5:
                            tc = ToiletConstruction.objects.get_or_create(slum = self.slum, household_number = house)
                    flag = True
                    query_filter = { "slum": self.slum, "household_number__in": houses}
                    update_data={}
                    if kobofield in self.BOOL_CHECK:
                        update_data[modelfield] = True
                    else:
                        update_data[modelfield] = self.convert_datetime(record['Date_of_reporting']).date()
                    tc = ToiletConstruction.objects.filter(**query_filter)
                    query_filter[modelfield+"__isnull"]=True
                    ToiletConstruction.objects.filter(**query_filter).update(**update_data)
                    for toilet_const in tc:
                        toilet_const.save()

            if '_submission_time' in record and submission_date > sync_date :
                sync_date = submission_date

        # if flag:
        #     self.update_sync_info(sync_date, self.user)
        data_len = len(self.survey_record)
        if not flag:
            sync_date=''
            data_len = 0
        return (data_len, flag, sync_date)

class CommunityMobilizaitonSync(DDSync):
    def __init__(self, slum, user):
        super(CommunityMobilizaitonSync, self).__init__(slum, user)

    def fetch_data(self):
        self.fetch_kobo_data(True)
        flag = False
        sync_date = ''
        for record in self.survey_record:
            submission_date = self.convert_datetime(record['_submission_time'])
            if not flag and '_submission_time' in record:
                sync_date = submission_date
            activity_type = record['group_wo9hi88/Type_of_Activity']
            houses = record['group_wo9hi88/House_numbers_whose_ended_above_activity']
            activity_date = self.convert_datetime(record['Date_of_reporting']).date()
            activity_type = ActivityType.objects.get(key=activity_type)
            cm,created = CommunityMobilization.objects.get_or_create(slum=self.slum, activity_type=activity_type, activity_date=activity_date)

            for house in houses.split(','):
                if len(house) < 5:
                    flag = True
                    com_mobs = CommunityMobilization.objects.filter(slum=self.slum,activity_type=activity_type, household_number__contains=house)
                    if len(com_mobs) <= 0:
                        if not cm.household_number:
                            cm.household_number=[]
                        if house not in cm.household_number:
                            cm.household_number.append(house)

            if cm.household_number:
                cm.household_number.sort()
                cm.save()
            else:
                cm.delete()
            if '_submission_time' in record and submission_date > sync_date :
                sync_date = submission_date
        data_len = len(self.survey_record)
        if not flag:
            sync_date = ''
            data_len = 0
        return (data_len, flag, sync_date)

