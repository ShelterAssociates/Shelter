from pykml import parser
from .models import Component, Metadata
from master.models import Slum
from django.contrib.gis.geos import GEOSGeometry

POINT = ['garbagebins', 'opengarbage', 'manholes', 'waterstandpost', 'chambers']
POLYGON = ['opendefecationarea', 'communitytoiletblock', 'houses']
LINESTRING = ['tarroad', 'coba', 'farshi', 'kutcha', 'drainageline18inch', 'drainageline12inch', 'drainageline10inch', 'drainageline24inch']

class KMLParser(object):
    ''' KML file parser to fetch component data and shape
    '''
    component_data = []

    #Constants to parse polygon, point and linestring
    KML_SHAPE = {
        'Polygon': POLYGON,
        'Point':POINT,
        'LineString': LINESTRING
    }
    #Database constants for adding components
    metadata_component = {  'houses' : 1, 'communitytoiletblock': 2, 'opendefecationarea': 3,
                            'garbagebins': 4, 'opengarbage': 5, 'tarroad': 6,
                            'manholes': 7, 'drainageline10inch' :8,'drainageline12inch' :9,
                            'drainageline18inch':10, 'coba': 11, 'farshi':12, 'waterstandpost':13,
                            'drainageline24inch':14, 'chambers':15, 'kutcha':16
                            }

    def __init__(self, docFile, slum):
        self.slum = slum
        self.root = parser.fromstring(docFile)
        self.other_components()

    def component_latlong(self, placemark, key):
        ''' Get latlong and data from the placemark object
        '''
        # Get household number
        extendeddata = list(placemark.ExtendedData.SchemaData.iterchildren())
        household_no = extendeddata[len(extendeddata)-1]

        #Get lat long coordinates as per the type of shape(polygon, point and linestring)
        try:
            coordinates=str(placemark[key].outerBoundaryIs.LinearRing.coordinates)
        except:
            coordinates=str(placemark[key].coordinates)
        return household_no, coordinates

    def bulk_update_or_create(self, key, metadata_id):
        '''update or create records in the table accordingly
        '''
        for component in self.component_data:
            coordinates = component['coordinates'].strip()
            coordinates = coordinates.split(',0')
            lst_coordinates = []

            for coordinate in coordinates[:-1]:
                lst_coordinates.append(list(map(float, coordinate.split(','))))

            if key == "Polygon":
                lst_coordinates = [lst_coordinates]
            elif key == "Point":
                lst_coordinates = lst_coordinates[0]

            #Create geometry object as per type
            pnt = GEOSGeometry('{ "type": "'+ key +'" , "coordinates": '+ str(lst_coordinates)+'  }')
            metadata = Metadata.objects.get(pk = metadata_id)
            val = {'housenumber':component['house_no'],
                    'slum': self.slum,
                    'metadata' : metadata}
            #Create or update in component
            obj, created = Component.objects.update_or_create(housenumber=component['house_no'], shape=pnt, slum=self.slum, metadata = metadata, defaults=val)

    def other_components(self):
        ''' Iterate through each document folder and process the data
        '''
        folders=[]
        try:
            folders = self.root.Document.Folder
        except:
            folders = self.root.Folder.Document.Folder
        for folder in folders:
            shape = self.KML_SHAPE.items()[0][0]
            kml_name = str(folder.name).split('(')[0]
            kml_name = kml_name.replace(' ','').lower()
            
	    if kml_name in self.metadata_component.keys():
	    	for key, val in self.KML_SHAPE.items():
                    if kml_name in val:
                    	shape = key
            	self.component_data = []
            	for pm in folder.Placemark:
                    #Fetch household number from extended data
                    (household_no, coordinates) = self.component_latlong(pm, shape)
                    self.component_data.append({'house_no':household_no, 'coordinates':coordinates})

            	self.bulk_update_or_create(shape, self.metadata_component[kml_name])
