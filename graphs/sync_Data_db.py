
from logging import exception
from operator import rshift
from urllib import response
from django.conf import settings
from numpy import record
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
from time import time, sleep
from datetime import timedelta,datetime, date
import dateutil.parser
import itertools
import traceback
import pandas as pd
import os 
import wget
import shutil
from PIL import Image
import sqlite3  
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import jwt


class avni_sync():
    def __init__(self):
        self.base_url = settings.AVNI_URL
        self.token_lock = threading.Lock()
        self.token = self.get_cognito_token()
        self.token_expiry = self.get_token_expiry(self.token)
        
    def get_cognito_details(self):
        cognito_details = requests.get(self.base_url+'cognito-details')
        cognito_details = json.loads(cognito_details.text)
        self.poolId = cognito_details['poolId']
        self.clientId = cognito_details['clientId']

    def get_token_expiry(self, token):
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload['exp'] 

    def get_cognito_token(self):
        self.get_cognito_details()
        command_data = subprocess.Popen(['node', 'graphs/avni/token.js',self.poolId, self.clientId, settings.AVNI_USERNAME, settings.AVNI_PASSWORD], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = command_data.communicate()
        self.token = stdout.decode("utf-8").replace('\n','')
        self.token_expiry = self.get_token_expiry(self.token)
        return self.token
    
    def make_request(self, method, url, data=None):
        headers = {'auth-token': self.ensure_token(), 'Content-Type': 'application/json'}
        response = requests.request(method, url, headers=headers, data=data)
        if response.status_code == 401:
            # Token expired, refresh once
            headers['auth-token'] = self.get_cognito_token()
            response = requests.request(method, url, headers=headers, data=data)
        return response
    
    def ensure_token(self):
        import time
        import threading
        if not hasattr(self, 'token_lock'):
            self.token_lock = threading.Lock()
        with self.token_lock:
            if not hasattr(self, 'token') or time.time() > self.token_expiry - 30:
                self.token = self.get_cognito_token()
        return self.token    
    
    # --- Process a single record ---
    def process_record(self, r , record_num, total_records):
        result = {"uuid": r['uuid'], "status": None, "not_found": False}
        uuid = r['uuid']

        print(f"[{record_num}/{total_records}] Processing UUID: {uuid}")

        table_name = "digipin"
        try:
            subject_id = r['uuid']
            req = self.make_request("GET", self.base_url + 'api/subject/' + subject_id)

            if req.status_code != 200:
                result['status'] = 2  # GET failed
                return result

            data = req.json()

            # Build address
            loc = data['location']
            address = ''
            if 'Admin' in loc and 'Ward' in loc:
                address = f"{loc['City']}, {loc['Admin']}, {loc['Ward']}, {loc['Slum']}"
            elif 'Admin' in loc:
                address = f"{loc['City']}, {loc['Admin']}, {loc['Slum']}"
            else:
                address = f"{loc['City']}, {loc['Ward']}, {loc['Slum']}"

            del data['location']
            data['Address'] = address

            data["First name"] = data['observations']["First name"]
            del data['observations']["First name"]
            if "Last name" in data['observations']:
                del data['observations']["Last name"]

            if not r['digipin']:
                result['not_found'] = True
                return result

            data['observations']['Digipin of the structure'] = r['digipin']
            payload = json.dumps(data)

            put_response = self.make_request("PUT", self.base_url + 'api/subject/' + subject_id, data=payload)
            if put_response.status_code != 200:
                result['status'] = 4  # PUT failed
            else:
                print(f"Record {uuid} updated successfully.")

                result['status'] = 3  # Success

        except Exception as e:
            print(subject_id, "Error:", e)
            result['status'] = 5  # Exception
        return result

    # --- Main update function ---
    def subject_data_update_parallel(self):
        db_name = "/home/shelterassociate/Desktop/scriptsPython/digipin.db"
        table_name = "digipin"
        conn = sqlite3.connect(db_name)
        df = pd.read_sql_query(f'SELECT * FROM "{table_name}" WHERE status != 3', conn)
        total_records = len(df)        
        print(f"Total records to process: {total_records}")

        final_list = []
        not_found = []

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.process_record, r ,i+1, total_records) for i, r in df.iterrows()]
            for future in as_completed(futures):
                res = future.result()
                uuid = res['uuid']
                status = res['status']
                if status:
                    conn.execute(f'UPDATE "{table_name}" SET status = ? WHERE uuid = ?', (status, uuid))
                    conn.commit()
                if res['not_found']:
                    not_found.append(uuid)
                else:
                    final_list.append(uuid)

        conn.commit()
        conn.close()

        print("Records updated successfully:", len(final_list))
        print("Records not found:", len(not_found))
        print("List of records not found:", not_found)

    def subject_data_update(self):
        db_name = "/home/shelterassociate/Desktop/scriptsPython/digipin.db"
        conn = sqlite3.connect(db_name)
        table_name = "digipin"
        df = pd.read_sql_query(f"SELECT * FROM \"{table_name}\" where status != 3", conn)
        #print(df)
        cur = conn.cursor()
        count = 1
        final_list = []
        not_found = []
        for i, r in df.iterrows():
            print(f"Processing {i} record from length {len(df)}")
            try:
                subject_id = r['uuid']
                Request = requests.get(self.base_url + 'api/subject/' + subject_id ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                
                if Request.status_code == 200:
                    # Get success status = 1
                    cur.execute(f"Update \"{table_name}\" set status = 1 where uuid = '{subject_id}'")
                    data = json.loads(Request.text)
                    #print(data)
                    # demo = json.dumps(data)
                    # print("Data fetched from AVNI")
                    # print(demo)
                    ''' For every subject we have to provide the address. You can get the address from location data i the response data.'''
                    location_cred = data['location']
                    address = ''
                    if 'Admin' in location_cred and 'Ward' in location_cred:
                        address += location_cred['City'] + ', ' + location_cred['Admin'] + ', ' + location_cred['Ward'] + ', ' + location_cred['Slum']
                    elif 'Admin' in location_cred:
                        address += location_cred['City'] + ', ' + location_cred['Admin']  + ', ' + location_cred['Slum']
                    else:
                        address += location_cred['City'] + ', ' + location_cred['Ward']  + ', ' + location_cred['Slum']

                    del data['location']
                    data['Address'] = address # r['address']
                    
                    data["First name"] = data['observations']["First name"]
                    del data['observations']["First name"]

                    if "Last name" in data['observations']:
                        del data['observations']["Last name"]
                    
                    # END
                    # # Add/Update other fields if required
                    if r['digipin'] == None or r['digipin'] == '':
                        print(f"Digipin not present for {r['uuid']}")
                        not_found.append(r['uuid'])
                        continue
                    else:
                        # print(f"Digipin present for {r['uuid']}")
                        data['observations']['Digipin of the structure'] = r['digipin']
                        final_list.append(r['uuid'])    
                    
                    payload = json.dumps(data)
                    # print(payload)

                    url = self.base_url +  'api/subject/' + subject_id
                    headers={'auth-token': self.get_cognito_token(),
                            'Content-Type': 'application/json',
                            }

                    response = requests.request("PUT", url, headers = headers, data = payload)

                    if response.status_code != 200:
                        # Put Failed status = 4
                        print("Record", subject_id, "Update Failed")
                        print(response.text)
                        cur.execute(f"Update \"{table_name}\" set status = 4 where uuid = '{subject_id}'")
                        print(response.text)
                        print("check", i)
                        final_list.append(subject_id)
                    else:
                        # print("Record", subject_id, "Updated Successfully")
                        cur.execute(f"Update \"{table_name}\" set status = 3 where uuid = '{subject_id}'")
                        count += 1
                else:
                    # Get failed
                    cur.execute(f"Update \"{table_name}\" set status =2  where uuid = '{subject_id}'")
                conn.commit()

            except Exception as e:
                print(e)
                # traceback.print_exc()
        conn.commit()
        conn.close()
        print("Number of records updated successfully", count)
        print(final_list)
        print("Number of records not found", len(not_found))
        print("List of records not found", not_found)
        print("Total records updated with digipin", len(final_list))

    def subject_data_update_JICA(self):
        db_name = "/home/shelterassociate/Desktop/scriptsPython/missing_location.db"
        conn = sqlite3.connect(db_name)
        table_name = "missing_location"
        df = pd.read_sql_query(f"SELECT * FROM \"{table_name}\"", conn)
        #print(df)
        cur = conn.cursor()
        count = 1
        final_list = []
        for i, r in df.iterrows():
            try:
                subject_id = r['uuid']
                Request = requests.get(self.base_url + 'api/subject/' + subject_id ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                
                if Request.status_code == 200:
                    # Get success status = 1
                    cur.execute(f"Update \"{table_name}\" set status = 1 where uuid = '{subject_id}'")
                    data = json.loads(Request.text)
                    #print(data)
                    #demo = json.dumps(data)
                    #print("Data fetched from AVNI")
                    #print(demo)
                    # Start compulsory for every API whil sending payload call
                    ''' For every subject we have to provide the address. You can get the address from location data i the response data.'''
                    location_cred = data['location']
                    address = ''
                    if 'Admin' in location_cred and 'Ward' in location_cred:
                        address += location_cred['City'] + ', ' + location_cred['Admin'] + ', ' + location_cred['Ward'] + ', ' + location_cred['Slum']
                    elif 'Admin' in location_cred:
                        address += location_cred['City'] + ', ' + location_cred['Admin']  + ', ' + location_cred['Slum']
                    else:
                        address += location_cred['City'] + ', ' + location_cred['Ward']  + ', ' + location_cred['Slum']

                    del data['location']
                    data['Address'] = address # r['address']
                    
                    data["First name"] = data['observations']["First name"]
                    del data['observations']["First name"]

                    if "Last name" in data['observations']:
                        del data['observations']["Last name"]
                    
                    # END
                    # # Add/Update other fields if required
                    data['Registration location'] = { 'x': r['latitude'], 'y': r['longitude'] }
                    members = data['observations'].get('Total Number of Members', {})
                    mapping = {
                        '088fa808-7013-4f4b-8e1b-80c2fc77add0': 'Number of Children/Girls',
                        '399d35e0-d496-49b1-a13c-65510cee632d': 'Number of Male members',
                        '9f35ecab-41af-4abc-b97c-08817ebacdba': 'Number of Female members'
                    }
                    updated = False
                    for old_key, new_key in mapping.items():
                        value = members.get(old_key)
                        if value is not None:
                            members[new_key] = value
                            del members[old_key]
                            updated = True
                    if updated:
                        data['observations']['Total Number of Members'] = members
                    
                    
                    #print(f"data is {data}")
                    payload = json.dumps(data)
                    print(payload)

                    url = self.base_url +  'api/subject/' + subject_id
                    headers={'auth-token': self.get_cognito_token(),
                            'Content-Type': 'application/json',
                            }

                    response = requests.request("PUT", url, headers = headers, data = payload)

                    if response.status_code != 200:
                        # Put Failed status = 4
                        print("Record", subject_id, "Update Failed")
                        print(response.text)
                        cur.execute(f"Update \"{table_name}\" set status = 4 where uuid = '{subject_id}'")
                        print(response.text)
                        print("check", i)
                        final_list.append(subject_id)
                    else:
                        print("Record", subject_id, "Updated Successfully")
                        cur.execute(f"Update \"{table_name}\" set status = 3 where uuid = '{subject_id}'")
                        count += 1
                else:
                    # Get failed
                    cur.execute(f"Update \"{table_name}\" set status =2  where uuid = '{subject_id}'")
                conn.commit()
            except Exception as e:
                print(e)
                # traceback.print_exc()
        conn.commit()
        conn.close()
        print("Number of records updated successfully", count)
        print(final_list)
        
    def subject_data_update_MOBILIZATION(self, sheet_name):
        db_name = "/home/shelterassociate/Downloads/mobilization.db"
        conn = sqlite3.connect(db_name)
        table_name = "mobilization"

        df = pd.read_sql_query(f"SELECT * FROM \"{table_name}\" where status != 3", conn)
        cur = conn.cursor()
        count = 1
        final_list = []
        # hh_dict = {}
        for i, r in df.iterrows():
            try:
                subject_id = r['uuid']
                # print(subject_id)
                Request = requests.get(self.base_url + 'api/subject/' + subject_id ,headers={'AUTH-TOKEN': self.get_cognito_token()})
                if Request.status_code == 200:
                    # Get success status = 1
                    cur.execute(f"Update \"{table_name}\" set status = 1 where uuid = '{subject_id}'")
                    data = json.loads(Request.text)
                    #print(data)
                    if data['observations'].get('Activity conducted for project ?'):
                        print(f"Activity conducted for project already present {r['uuid']}")
                        continue
                    else:
                        print(f"Activity conducted for project not present {r['uuid']}")
                        data['observations']['Activity conducted for project ?'] = r['Activity conducted for project ?']

                    # Start compulsory for every API whil sending payload call
                    ''' For every subject we have to provide the address. You can get the address from location data i the response data.'''
                    location_cred = data['location']
                    address = ''
                    if 'Admin' in location_cred and 'Ward' in location_cred:
                        address += location_cred['City'] + ', ' + location_cred['Admin'] + ', ' + location_cred['Ward'] + ', ' + location_cred['Slum']
                    elif 'Admin' in location_cred:
                        address += location_cred['City'] + ', ' + location_cred['Admin']  + ', ' + location_cred['Slum']
                    else:
                        address += location_cred['City'] + ', ' + location_cred['Ward']  + ', ' + location_cred['Slum']
                    del data['location']
                    data['Address'] = address # r['address']

                    data["First name"] = data['observations']["First name"]
                    del data['observations']["First name"]

                    if "Last name" in data['observations']:
                        del data['observations']["Last name"]
                    # END
                    # # Add/Update other fields if required
                    #print(f"data is {data}") 
                    payload = json.dumps(data)
                    #print(payload)
                    url = self.base_url +  'api/subject/' + subject_id
                    headers={'auth-token': self.get_cognito_token(),
                            'Content-Type': 'application/json',
                            }
                    response = requests.request("PUT", url, headers = headers, data = payload)
                    if response.status_code != 200:
                        # Put Failed status = 4
                        cur.execute(f"Update \"{table_name}\" set status = 4 where uuid = '{subject_id}'")
                        print(response.text)
                        print("check", i)
                        final_list.append(subject_id)
                    else:
                        
                         cur.execute(f"Update \"{table_name}\" set status = 3 where uuid = '{subject_id}'")
                         count += 1

                else:
                    # Get failed
                    cur.execute(f"Update \"{table_name}\" set status =2  where uuid = '{subject_id}'")
                conn.commit()
            except Exception as e:
                print(e)
                # traceback.print_exc()
        conn.commit()
        conn.close()
        print(final_list)