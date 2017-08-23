''''
    Script to update PCMC RHS records for current place of defecation. 
'''

import uuid
import traceback
import copy
from sponsor.models import *
from django.conf import settings
import json
import urllib2
import itertools

kobo_survey = '54'
gl_rhs_xml_dict = {
	'formhub' : {
		'uuid' : None
	},
	'start' : None,
	'end' : None,
	'group_ce0hf58' : {
		'city' : None,
		'admin_ward' : None,
		'slum_name' : None,
		'date_of_rhs' : None,
		'name_of_surveyor_who_collected_rhs_data' : None,
		'house_no' : None,
		'Type_of_structure_occupancy' : None
	},
	'group_ye18c77' : {
		'group_ud4em45' : {
			'what_is_the_full_name_of_the_family_head_' : None,
			'mobile_number' : None,
			'adhar_card_number' : None
		},
		'group_yw8pj39' : {
			'what_is_the_structure_of_the_house' : None,
			'what_is_the_ownership_status_of_the_house' : None,
			'number_of_family_members' : None,
			'Do_you_have_a_girl_child_under' : None,
			'if_yes_how_many_' : None,
			'house_area_in_sq_ft' : None,
			'Current_place_of_defecation_toilet' : None,
			'does_any_member_of_your_family_go_for_open_defecation_' : None,
			'where_the_individual_toilet_is_connected_to_' : None,
			'type_of_water_connection' : None,
			'facility_of_waste_collection' : None,
			'Are_you_interested_in_individu' : None,
			'if_yes_why_' : None,
			'if_no_why_' : None,
			'type_of_toilet_preference' : None,
			'Have_you_applied_for_indiviual' : None,
			'How_many_installements_have_yo' : None,
			'when_did_you_receive_the_first_installment_date' : None,
			'when_did_you_receive_the_second_installment_date' : None,
			'what_is_the_status_of_toilet_under_sbm_' : None,
			'Does_any_family_members_has_co' : None
		},
	},
	'__version__' : None,
	'meta' : {
		'instanceID' : None,
        'deprecatedID' : None
	}
}

def fetch():
    sponsored_households = SponsorProjectDetails.objects.filter(sponsor__organization_name = "SBM Toilets")
    for sponsored_household in sponsored_households:
        slum_code = sponsored_household.slum.shelter_slum_code
        url = settings.KOBOCAT_FORM_URL + 'data/' + kobo_survey + '?query={"group_ce0hf58/slum_name":"' + slum_code + '"}'
        kobotoolbox_request = urllib2.Request(url)
        kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
        kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
        res = urllib2.urlopen(kobotoolbox_request)
        html = res.read()
        json_records = json.loads(html)
        grouped_records = itertools.groupby(sorted(json_records, key=lambda x: int(x['group_ce0hf58/house_no'])), key=lambda x: int(x["group_ce0hf58/house_no"]))
        records={}
        for list_record in grouped_records:
            records[list_record[0]] = list(list_record[1])
        print sponsored_household.slum.name
        rec = []
        for house in sponsored_household.household_code:
            #house = '000'.join(str(house))[-4:]
            if house in records:
                record_sorted = sorted(records[house], key=lambda x: x['end'], reverse=True)
                record = record_sorted[0]
                if 'group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet' in record and record['group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet'] in ['01', '02']:
                    rec.append(str(house) +' :: '+ str(len(record_sorted)) + ' :: '+str(record['_id']))
            else:
                print "Not found" + str(house)
        print rec