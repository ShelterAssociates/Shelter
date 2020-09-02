from pykml import parser
from .models import Component, Metadata
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.contenttypes.models import ContentType
POINT = 'Point'
POLYGON = 'Polygon'
LINESTRING = 'LineString'

class KMLParser(object):
    ''' KML file parser to fetch component data and shape
    '''
    component_data = []

    def __init__(self, docFile, object_type, delete_flag):
        self.object_type = object_type
        self.delete_flag = delete_flag
        self.root = parser.fromstring(docFile)

    def component_latlong(self, placemark):
        ''' Get latlong and data from the placemark object
        '''
        # Get household number
        household_no = ''
        extendeddata = {marker_place.get('name').lower():marker_place for marker_place in placemark.ExtendedData.SchemaData.iterchildren()}
        if 'id' in  extendeddata.keys():
            household_no = extendeddata['id']
        if 'houseno' in  extendeddata.keys():
            household_no = extendeddata['houseno']
        if household_no == "" and len(extendeddata.keys()) > 0:
            household_no = extendeddata[extendeddata.keys()[0]]

        #Get lat long coordinates as per the type of shape(polygon, point and linestring)
        key = LINESTRING
        geometry_data= []
        if hasattr(placemark, POLYGON):
            geometry_data.append(str(placemark[POLYGON].outerBoundaryIs.LinearRing.coordinates))
            key = POLYGON
        elif hasattr(placemark, POINT):
            geometry_data.append(str(placemark[POINT].coordinates))
            key = POINT
        else:
            if hasattr(placemark, "MultiGeometry"):
                for coord in placemark['MultiGeometry'][LINESTRING]:
                    geometry_data.append(str(coord.coordinates))
            else:
                geometry_data.append(str(placemark[LINESTRING].coordinates))
        pnt=[]

        for geometry in geometry_data:
            coordinates = geometry.strip()
            coordinates = coordinates.split(' ')
            lst_coordinates = []

            for coordinate in coordinates:
                if coordinate:
                    lst_coordinates.append(list(map(float, coordinate.split(',')[:2])))
            #print(lst_coordinates, key)
            if key == POLYGON:
                lst_coordinates = [lst_coordinates]
            elif key == POINT:
                lst_coordinates = lst_coordinates[0]

            #Create geometry object as per type
            pnt.append(GEOSGeometry('{ "type": "'+ key +'" , "coordinates": '+ str(lst_coordinates)+'  }'))

        return household_no, pnt

    def bulk_update_or_create(self, metadata_code):
        '''update or create records in the table accordingly
        '''
        metadata = Metadata.objects.get(code=metadata_code, type='C')
        temp_component = self.object_type.components.filter(metadata = metadata).values('id','housenumber')
        temp_component = {x['housenumber']:x['id'] for x in temp_component}
        content_type = ContentType.objects.filter(model=self.object_type.__class__.__name__.lower())[0]
        create_bulk = []
        for component in self.component_data:
            coordinates = component['coordinates']
            key = key_no =str(component['house_no'])
            for index, pnt in enumerate(coordinates):
                val = {'shape':pnt}
                #Create or update in component
                #obj, created = self.object_type.components.update_or_create(housenumber=key_no, metadata = metadata, defaults=val)
                #Below code is the replacement for above code as it takes time to execute
                if key_no in temp_component.keys():
                    updated = Component.objects.filter(id=temp_component[key_no]).update(**val)
                else:
                    create_bulk.append(Component(housenumber=key_no, object_id=self.object_type.id, content_type=content_type, metadata = metadata, shape=pnt))
                key_no = key + '.'+str(index+1)
        if len(create_bulk) > 0:
            Component.objects.bulk_create(create_bulk)

    def other_components(self):
        ''' Iterate through each document folder and process the data
        '''
        folders=[]
        kml_folder={}
        try:
            folders = self.root.Document.Folder
        except:
            folders = self.root.Folder.Document.Folder
        metadata_component = Metadata.objects.filter(type='C').values_list('code', flat=True)

        if self.delete_flag:
            self.object_type.components.all().delete()

        for folder in folders:
          try:
            kml_name = str(folder.name).split('(')[0]
            kml_name = kml_name.replace(' ','')
            kml_folder[kml_name] = False
            if kml_name in metadata_component:
                self.component_data = []
                for pm in folder.Placemark:
                    #Fetch household number from extended data
                    try:
                        (household_no, coordinates) = self.component_latlong(pm)
                        self.component_data.append({'house_no':household_no, 'coordinates':coordinates})

                    except Exception as ex:
                        raise Exception(" -> "+str(pm.name) +' ]] '+ str(ex))
                self.bulk_update_or_create(kml_name)
                kml_folder[kml_name] = True
          except Exception as e:
            raise Exception("[[ " + str(folder.name) +  str(e))
        return kml_folder
