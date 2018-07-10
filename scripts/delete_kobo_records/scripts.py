''''
Script to delete records from kobotoolbox. 
To run include the folder in sys path

import sys
sys.path.insert(0, 'scripts/delete_kobo_records/')
from scripts import *
'''

from django.conf import settings
import json
import requests
import urllib2
from multiprocessing import Pool
kobo_form = 133
headers={}
headers["Authorization"] = settings.KOBOCAT_TOKEN
# SBM PCMC v1 = 103 local
# SBM_KMC_v1 = 107 local
# PMC_SBM_FOLLOWUP_abhijit = 108 local
def fetch_records(formID):
    global kobo_form
    if formID:
        kobo_form = formID
    fetchURL = '/'.join([settings.KOBOCAT_FORM_URL[:-1], 'data', str(kobo_form)])
    print fetchURL
    # objresponse = requests.get(fetchURL + '?format=json&fields=["_id"]', headers=headers)
    # records = objresponse.json()
    kobotoolbox_request = urllib2.Request(fetchURL + '?format=json&fields=["_id"]')
    #kobotoolbox_request = urllib2.Request(fetchURL + '?format=json&query={"slum_name":"272538756304"}&fields=["_id"]')
    kobotoolbox_request.add_header('User-agent', 'Mozilla 5.10')
    kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
    res = urllib2.urlopen(kobotoolbox_request)
    html = res.read()
    records = json.loads(html)

    print (records)
    print ("Total number of records to be deleted : " + str(len(records)))

    pool_obj = Pool(processes=5)
    response_obj = pool_obj.map(delete_record, records)
    print (response_obj)
    pool_obj.close()
    pool_obj.join()

# Creating subprocess
def delete_record(records):
    objresponseDeleted=None
    record = records
    if record:
        delete_record_id = record['_id']
        deleteURL = '/'.join([settings.KOBOCAT_FORM_URL[:-1],'data', str(kobo_form) , str(delete_record_id)])
        objresponseDeleted = requests.delete(deleteURL, headers=headers)

        print(' deleted for '+str(delete_record_id) + ' with response '+str(objresponseDeleted))
    return objresponseDeleted
