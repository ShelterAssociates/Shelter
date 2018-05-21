from pykml import parser
from .models import Component, Metadata
from master.models import Slum
from django.contrib.gis.geos import GEOSGeometry

POINT = 'Point'
POLYGON = 'Polygon'
LINESTRING = 'LineString'

class KMLParser(object):
    ''' KML file parser to fetch component data and shape
    '''
    component_data = []

    def __init__(self, docFile, slum, delete_flag):
        self.slum = slum
        self.delete_flag = delete_flag
        self.root = parser.fromstring(docFile)

    def component_latlong(self, placemark):
        ''' Get latlong and data from the placemark object
        '''
        # Get household number
        extendeddata = list(placemark.ExtendedData.SchemaData.iterchildren())
        household_no = extendeddata[len(extendeddata)-1]

        #Get lat long coordinates as per the type of shape(polygon, point and linestring)
        key = LINESTRING
        if hasattr(placemark, POLYGON):
            coordinates=str(placemark[POLYGON].outerBoundaryIs.LinearRing.coordinates)
            key = POLYGON
        elif hasattr(placemark, POINT):
            coordinates=str(placemark[POINT].coordinates)
            key = POINT
        else:
            coordinates=str(placemark[LINESTRING].coordinates)

        coordinates = coordinates.strip()
        coordinates = coordinates.split(',0')
        lst_coordinates = []

        for coordinate in coordinates[:-1]:
            lst_coordinates.append(list(map(float, coordinate.split(','))))

        if key == POLYGON:
            lst_coordinates = [lst_coordinates]
        elif key == POINT:
            lst_coordinates = lst_coordinates[0]

        #Create geometry object as per type
        pnt = GEOSGeometry('{ "type": "'+ key +'" , "coordinates": '+ str(lst_coordinates)+'  }')

        return household_no, pnt

    def bulk_update_or_create(self, metadata_code):
        '''update or create records in the table accordingly
        '''
        for component in self.component_data:
            pnt = component['coordinates']

            metadata = Metadata.objects.get(code = metadata_code, type='C')
            val = {'shape':pnt}
            #Create or update in component
            obj, created = Component.objects.update_or_create(housenumber=component['house_no'], slum=self.slum, metadata = metadata, defaults=val)

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
            Component.objects.filter(slum = self.slum).delete()

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
