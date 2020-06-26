from django.apps import apps
from pykml import parser
from django.contrib.gis.geos import GEOSGeometry
from .models import *

base_filter_data = {"City":("id","city"),
                    "AdministrativeWard": ("city__id", "administrative_ward"),
                    "ElectoralWard": ("administrative_ward__city__id", "electoral_ward"),
                    "Slum": ("electoral_ward__administrative_ward__city__id", "slum")}
parse_link = {"AdministrativeWard": "ElectoralWard", "ElectoralWard": "Slum"}

class KMLLevelParser(object):
    def __init__(self, docFile, city_id,chk_delete, action_title):
        root = parser.fromstring(docFile)
        self.city_id = int(city_id)
        self.chk_delete = chk_delete
        self.folders = []
        self.action_title = action_title
        try:
            self.folders = root.Document.Folder
        except:
            self.folders = root.Folder.Document.Folder

        self.parent_model = apps.get_model('master', action_title)

    def parse_placemark(self, placemark):
        ''' Get latlong and data from the placemark object
        '''
        # Get household number
        name = str(placemark.name)

        #Get lat long coordinates as per the type of shape(polygon, point and linestring)
        POLYGON = "Polygon"
        geometry_data= []
        if hasattr(placemark, POLYGON):
            geometry_data.append(str(placemark[POLYGON].outerBoundaryIs.LinearRing.coordinates))
        else:
            if hasattr(placemark, "MultiGeometry"):
                for coord in placemark['MultiGeometry'][POLYGON]:
                    geometry_data.append(str(coord.outerBoundaryIs.LinearRing.coordinates))

        pnt=[]

        for geometry in geometry_data:
            coordinates = geometry.strip()
            coordinates = coordinates.split(',0')
            lst_coordinates = []

            for coordinate in coordinates[:-1]:
                lst_coordinates.append(list(map(float, coordinate.split(','))))

            lst_coordinates = [lst_coordinates]

            #Create geometry object as per type
            pnt.append(GEOSGeometry('{ "type": "'+ POLYGON +'" , "coordinates": '+ str(lst_coordinates)+'  }'))

        return name, pnt

    def delete_history(self):
        """
        Delete all the level records. Before deleting make the reference fields empty.
        :return: 
        """
        parent_filter = {}
        parent_filter[base_filter_data[self.action_title][0]] = self.city_id
        parent_model_data = self.parent_model.objects.filter(**parent_filter)
        if self.action_title in parse_link.keys():
            child_model = apps.get_model('master', parse_link[self.action_title])
            child_filter = {}
            child_filter[base_filter_data[self.action_title][1]] = parent_model_data
            child_update = {}
            child_update[base_filter_data[self.action_title][1]] = None
            child_model.objects.filter(**child_filter).update(**child_update)
            parent_model_data.delete()

    def parse_kml(self):
        if self.chk_delete == "true":
            self.delete_history()
        cnt = {'updated': 0, 'created': 0}
        parent_filter = {'defaults':{}}
        parent_filter[base_filter_data[self.action_title][0]] = self.city_id
        if self.action_title == "AdministrativeWard":
            parent_filter['defaults'][base_filter_data['City'][1]] = \
            City.objects.filter(id=self.city_id)[0]

        if self.action_title == "ElectoralWard":
            parent_filter['defaults'][base_filter_data['AdministrativeWard'][1]] = \
            AdministrativeWard.objects.filter(city__id=self.city_id)[0]

        if self.action_title == "Slum":
            parent_filter['defaults'][base_filter_data['ElectoralWard'][1]] = \
                ElectoralWard.objects.filter(administrative_ward__city__id=self.city_id)[0]

        for folder in self.folders:
            for pm in folder.Placemark:
                (name, coordinates) = self.parse_placemark(pm)
                for count_c, coordinate in enumerate(coordinates):
                    if self.action_title == "ElectoralWard":
                        name += " "+base_filter_data[self.action_title][1].replace("_", " ").title()
                    if len(coordinates) > 1:
                        level_name =  'Part '+str(count_c+1) +' '+ name
                    else:
                        level_name = name
                    if self.action_title != "City":
                        parent_filter['name'] = level_name.strip()
                    parent_filter['defaults']['shape']= coordinate
                    obj, created = self.parent_model.objects.update_or_create(**parent_filter)
                    if created == True:
                        cnt['created'] += 1
                    else:
                        cnt['updated'] += 1
        if self.action_title in parse_link.values():
            linking = LinkingLevels(self.city_id)
            linking.linking()
        return cnt

class LinkingLevels(object):
    def __init__(self, city_id):
        self.city_id = city_id

    def linking(self):
        try:
            for parent_level,child_level in parse_link.items():
                child_level_model = apps.get_model('master', child_level)
                filter_level = {}
                filter_level[base_filter_data[child_level][0]] = self.city_id
                update_level = {}
                update_level[base_filter_data[parent_level][1]] = None
                child_level_model.objects.filter(**filter_level).update(**update_level)

                parent_level_model = apps.get_model('master', parent_level)
                parent_level_filter ={}
                parent_level_filter[base_filter_data[parent_level][0]] = self.city_id
                parent_level_objects = parent_level_model.objects.filter(**parent_level_filter)

                for parent_level_object in parent_level_objects:
                    child_level_objects = child_level_model.objects.filter(**update_level)
                    for child_level_object in child_level_objects:
                        if parent_level_object.shape.intersects(child_level_object.shape):
                            filter_data_child={}
                            filter_data_child[base_filter_data[parent_level][1]] = parent_level_object
                            child_level_model.objects.filter(id=child_level_object.id).update(**filter_data_child)
        except:
            return False
        return True
