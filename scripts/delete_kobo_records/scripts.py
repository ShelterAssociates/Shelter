''''
    Script to delete records from kobotoolbox. 
    To run include the folder in sys path

    import sys
    sys.path.insert(0, 'scripts/delete_kobo_records/')
'''

from django.conf import settings
import json
import requests

def delete_records(kobo_form):
    headers={}
    headers["Authorization"] = settings.KOBOCAT_TOKEN
    fetchURL = '/'.join([settings.KOBOCAT_FORM_URL[:-1], 'data', str(kobo_form)])
    objresponse = requests.get(fetchURL + '?format=json&fields=["_id"]', headers=headers)
    records = objresponse.json()
    print (records)
    print ("Total number of records to be deleted : " + str(len(records)))
    count = 0
    for record in records:
        delete_record_id = record['_id']
        deleteURL = '/'.join([settings.KOBOCAT_FORM_URL[:-1],'data', str(kobo_form) , str(delete_record_id)])
        #objresponseDeleted = requests.delete(deleteURL, headers=headers)
        count += 1
        print(str(count) + ' deleted for '+str(delete_record_id) + ' with response '#+objresponseDeleted)
