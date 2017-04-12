from pykml import parser
from django.contrib.gis.geos import GEOSGeometry
from master.models import *
from itertools import groupby

class KMLSlumParser(object):
    def __init__(self, docFile):
        self.root = parser.fromstring(docFile.read())
        self.components = []
        self.folders = None
        self.elements={}
        self.data={}
        self.city_id = 0
        self.parser_component = {"admin": self.parse_admin,
                                 "electoral": self.parse_electoral,
                                 "slum": self.parse_slum}

    def parse(self):
        document = self.root.Document.Folder
        self.city_id = self.root.Document.id
        self.components = str(self.root.Document.components).split(',')
        for index, comp in enumerate(self.components):
            if comp in self.parser_component.keys():
                self.folders = document[index]
                self.parser_component[comp](comp)
        #return self.extract()

    def get_coordinate(self, placemark):
        coordinates=str(placemark.Polygon.outerBoundaryIs.LinearRing.coordinates)
        coordinates = coordinates.strip()
        coordinates = coordinates.split(',0')
        lst_coordinates = []

        for coordinate in coordinates[:-1]:
            lst_coordinates.append(list(map(float, coordinate.split(','))))
        lst_coordinates = [lst_coordinates]
        #Create geometry object as per type
        pnt = GEOSGeometry('{ "type": "POLYGON" , "coordinates": '+ str(lst_coordinates)+'  }')

        return pnt


    def parse_admin(self, comp):
        self.data[comp] = {}
        #Administrative ward data parsing
        for folder in self.folders.Folder:
            name = str(folder.name)
            shape = self.get_coordinate(folder.Placemark)
            self.data[comp][name] = shape

    def parse_electoral(self, comp):
        self.data[comp] = {}
        #Electoral ward data parsing
        for folder in self.folders.Placemark:
            elect = {}
            elec_ward_no = folder.name
            admin_name = folder.ExtendedData.SchemaData.SimpleData[20]
            name = folder.ExtendedData.SchemaData.SimpleData[21]
            if name == "Not Received":
                name += " (" + elec_ward_no +")"
            shape = self.get_coordinate(folder)
            elect = { "name":name , "admin_name": admin_name,
                      "ward_no":elec_ward_no, "shape":shape}
            self.data[comp][elec_ward_no] = elect


    def parse_slum(self, comp):
        self.data[comp] = []
        #Slum data parsing
        for folder in self.folders.Folder:
            ward = folder.name
            for slum in folder.Placemark:
                slum_details = {}
                name = slum.ExtendedData.SchemaData.SimpleData[16]
                if name == "":
                    name = slum.name
                ward_no = slum.ExtendedData.SchemaData.SimpleData[18]
                shape = self.get_coordinate(slum)
                slum_details = {"name":name, "ward_no":ward_no,
                                "admin_ward": ward, "shape":shape}
                self.data[comp].append(slum_details)

    def extract(self):
        city = City.objects.get(pk=self.city_id)
        if 'admin' in self.data.keys():
            for name, shape in self.data['admin'].items():
                admin, flag= AdministrativeWard.objects.update_or_create(city=city, name=name, defaults={"shape":shape, "ward_no":1})
                self.data['admin'][name] = admin

        if 'electoral' in self.data.keys():
            e =  self.data['electoral']
            e = sorted(e.values(), key=lambda x:x['admin_name'])

            for admin_ward, electorals in groupby(e, key=lambda x:x['admin_name']):

                admin_key = [x for x in self.data['admin'].keys() if x in str(admin_ward)]
                if len(admin_key) > 0:
                    admin = self.data['admin'][admin_key[0]]
                    print admin_ward
                    for electoral in electorals:
                        print "\n\t\t"+str(electoral['name'])
                        electoral_ward, flag = ElectoralWard.objects.update_or_create(administrative_ward = admin, name=electoral['name'],
                                                              ward_no=electoral['ward_no'], defaults={"shape":electoral['shape'], "ward_code":electoral['ward_no']})
                        self.data['electoral'][str(electoral['ward_no'])] = electoral_ward
                #else:
                    #print admin_ward

        if 'slum' in self.data.keys():
            for slum in self.data['slum']:
                if slum['ward_no'] != "0" and str(slum['ward_no']) in self.data['electoral'].keys():
                    electoral = self.data['electoral'][str(slum['ward_no'])]
                    #print electoral
                    slum_rec, flag = Slum.objects.update_or_create(name=slum['name'], electoral_ward=electoral, defaults={ "shape":slum['shape']})
