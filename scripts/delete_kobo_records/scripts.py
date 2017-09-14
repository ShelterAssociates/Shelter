''''
    Script to delete records from kobotoolbox. 
    To run include the folder in sys path

    import sys
    sys.path.insert(0, 'scripts/delete_kobo_records/')
'''

from django.conf import settings
import json
import requests
from multiprocessing import Pool
kobo_form = 41
headers={}
headers["Authorization"] = settings.KOBOCAT_TOKEN

def fetch_records(formID):
    global kobo_form
    if formID:
        kobo_form = formID
    fetchURL = '/'.join([settings.KOBOCAT_FORM_URL[:-1], 'data', str(kobo_form)])
    objresponse = requests.get(fetchURL + '?format=json&fields=["_id"]', headers=headers)
    records = objresponse.json()
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
