
import urllib3
import json
from master.models import ElectoralWard,AdministrativeWard
from django.contrib.gis.geos import GEOSGeometry

PUNE= 14
SANGLI = 15
PIMPARI = 197
KOLHAPUR = 279
SHELTER='http://slum.shelter-associates.org/'
http = urllib3.PoolManager()

def get_admin_wards(city):
    url = SHELTER + 'ward-data/' + str(city)
    response = http.request('GET', url)
    list_admin={}
    for n in json.loads(response.data)['nodes']:
        list_admin[n['node']['id']] = n['node']['name']
    return list_admin

def get_electoral_wards(drupal_admin_id,local_ward_id):
    url = SHELTER + 'electoral-ward-data/' + str(drupal_admin_id)
    response = http.request('GET', url)
    
    for n in json.loads(response.data)['nodes']: 
        coordinates = n['node']['shape'].split(',0')
        lst_coordinates = []

        for coordinate in coordinates[:-1]:
            lst_coordinates.append(list(map(float, coordinate.split(','))))
        
        lst_coordinates = [lst_coordinates]
        key="Polygon"
        pnt = GEOSGeometry('{ "type": "'+ key +'" , "coordinates": '+ str(lst_coordinates)+'  }')
                
        admin_data = AdministrativeWard.objects.get(id=local_ward_id)
        obj, created = ElectoralWard.objects.update_or_create(name= n['node']['name'],administrative_ward = admin_data ,shape=pnt,extra_info=n['node']['description'], defaults={'name': n['node']['name']})
        print created
