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
import urllib2
import json
from dateutil.parser import parse

from master.models import Survey, Slum, SURVEYTYPE_CHOICES
from models import *


class DDSync(object):
    def __init__(self, slum, user):
        self.slum = slum
        self.user = user
        try:
            survey_id = None
            survey = Survey.objects.filter(city=slum.electoral_ward.administrative_ward.city,
                                  survey_type=SURVEYTYPE_CHOICES[5][0])
            if len(survey) > 0:
                survey_id = survey[0].kobotool_survey_id
        except:
            survey_id = None
        self.survey_id = '129'#survey_id
        self.survey_date = self.convert_datetime("2017-01-21T01:02:03")
        self.survey_record = None

    def convert_datetime(self, date):
        return parse(date)

    def fetch_url(self, community_mobilization_flag):
        kobo_url = settings.KOBOCAT_FORM_URL + 'data/'+str(self.survey_id)
        kobo_url += '?format=json&query={"slum_name":"'+self.slum.shelter_slum_code +'"'
        kobo_url += ',"Was_any_Community_Mobilisation":"1" ' if community_mobilization_flag else ''
        kobo_url += ',"_submission_time":{"$gt":"%s"} }'
        return kobo_url

    def fetch_kobo_data(self, community_mobilization_flag=False):
        sync_info = KoboDDSyncTrack.objects.filter(slum=self.slum).order_by('-sync_date').first()
        if sync_info:
            self.survey_date = self.convert_datetime(str(sync_info.sync_date))
        url = self.fetch_url(community_mobilization_flag) % str(self.survey_date)
        kobotoolbox_request = urllib2.Request(url)
        kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
        kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)

        res = urllib2.urlopen(kobotoolbox_request)
        # Read json data from kobotoolbox API
        html = res.read()
        records = json.loads(html)
        #sorted(records, key=lambda x:x['_submission_time'])
        self.survey_record = records

    def update_sync_info(self, sync_date):
        try:
            KoboDDSyncTrack.objects.create(slum=self.slum,sync_date=sync_date,created_by=self.user)
        except:
            print "Error creating record"

class ToiletConstructionSync(DDSync):

    def __init__(self, slum, user):
        super(ToiletConstructionSync, self).__init__(slum, user)
        self.MAPPING = {"House_numbers_of_hou_Septic_Tank_is_given":"septic_tank_date", "House_numbers_of_hou_re_agreement_is_done":"agreement_date",
                        "House_numbers_of_hou_and_cement_is_given":"phase_one_material_date", "House_numbers_of_hou_al_Hardware_is_given":"phase_two_material_date",
                        "House_numbers_of_hou_HASE_3_Door_is_given":"phase_three_material_date", "House_numbers_of_hou_truction_is_complete": "completion_date",
                        #"House_numbers_where_tion_has_not_started":"", "House_numbers_where_ted_to_drainage_line":"",
                        #"House_numbers_where_reement_is_cancelled":"agreement_cancelled", "House_numbers_where_ifted_from_HH_to_HH":"material_shifted_to"
                        }

    def fetch_data(self):
        self.fetch_kobo_data()
        sync_date = ''
        flag = False
        for record in self.survey_record:
            submission_date = self.convert_datetime(record['_submission_time'])
            if not flag and '_submission_time' in record:
                sync_date = submission_date
            for kobofield, modelfield in self.MAPPING.items():
                if kobofield in record:
                    houses = record[kobofield].split(',')

                    for house in houses:
                        if len(house) < 5:
                            tc = ToiletConstruction.objects.get_or_create(slum = self.slum, household_number = house)
                    flag = True
                    query_filter = { "slum": self.slum, "household_number__in": houses, modelfield+"__isnull":True}
                    update_data={}
                    update_data[modelfield] = self.convert_datetime(record['Date_of_reporting']).date()
                    ToiletConstruction.objects.filter(**query_filter).update(**update_data)

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

