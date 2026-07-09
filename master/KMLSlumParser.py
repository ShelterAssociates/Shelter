import re
from pykml import parser
from django.contrib.gis.geos import GEOSGeometry
from master.models import *
from itertools import groupby


class KMLSlumParser(object):
    def __init__(self, docFile):
        self.root = parser.fromstring(docFile.read())
        self.components = []
        self.folders = None
        self.elements = {}
        self.data = {}
        self.city_id = 0
        self.parser_component = {
            "admin": self.parse_admin,
            "electoral": self.parse_electoral,
            "slum": self.parse_slum,
        }

    def parse(self):
        document = self.root.Document.Folder
        self.city_id = self.root.Document.id
        self.components = str(self.root.Document.components).split(",")
        for index, comp in enumerate(self.components):
            if comp in self.parser_component.keys():
                self.folders = document[index]
                self.parser_component[comp](comp)
        # return self.extract()

    def get_coordinate(self, placemark):
        coordinates = str(placemark.Polygon.outerBoundaryIs.LinearRing.coordinates)
        coordinates = coordinates.strip()
        coordinates = coordinates.split(",0")
        lst_coordinates = []

        for coordinate in coordinates[:-1]:
            lst_coordinates.append(list(map(float, coordinate.split(","))))
        lst_coordinates = [lst_coordinates]
        pnt = GEOSGeometry(
            '{ "type": "POLYGON" , "coordinates": ' + str(lst_coordinates) + "  }"
        )

        return pnt

    @staticmethod
    def _extended_data_dict(placemark):
        """Build a {field_name_lower: value} lookup from SchemaData,
        instead of relying on fixed index positions which break the
        moment a file has a different field count/order."""
        return {
            sd.get("name").lower(): str(sd)
            for sd in placemark.ExtendedData.SchemaData.SimpleData
        }

    @staticmethod
    def _ward_number(text):
        """Extract the numeric ward number embedded in a name like
        'Admin Boundary 8' or 'Ward 8' or '8', for robust matching."""
        match = re.search(r"\d+", str(text))
        return match.group() if match else None

    def parse_admin(self, comp):
        self.data[comp] = {}
        # Administrative ward data parsing
        for folder in self.folders.Folder:
            name = str(folder.name)
            shape = self.get_coordinate(folder.Placemark)
            self.data[comp][name] = shape

    def parse_electoral(self, comp):
        self.data[comp] = {}
        # Electoral ward data parsing
        for folder in self.folders.Placemark:
            elec_ward_no = str(folder.name)
            extendeddata = self._extended_data_dict(folder)

            # 'Admin' field auto-detects the administrative ward this
            # electoral boundary belongs to; 'Ward_No' is the electoral
            # ward number/id
            admin_name = extendeddata.get("admin", "")
            ward_no = extendeddata.get("ward_no", elec_ward_no)
            name = extendeddata.get("name") or admin_name or "Not Received"

            if name == "Not Received":
                name += " (" + str(elec_ward_no) + ")"

            shape = self.get_coordinate(folder)
            elect = {
                "name": name,
                "admin_name": admin_name,
                "ward_no": ward_no,
                "shape": shape,
            }
            self.data[comp][ward_no] = elect

    def parse_slum(self, comp):
        self.data[comp] = []
        # Slum data parsing
        for folder in self.folders.Folder:
            ward = folder.name
            for slum in folder.Placemark:
                extendeddata = self._extended_data_dict(slum)
                name = extendeddata.get("name") or str(slum.name)
                ward_no = extendeddata.get("ward_no", "0")
                shape = self.get_coordinate(slum)
                slum_details = {
                    "name": name,
                    "ward_no": ward_no,
                    "admin_ward": ward,
                    "shape": shape,
                }
                self.data[comp].append(slum_details)

    def extract(self):
        city = City.objects.get(pk=self.city_id)
        if "admin" in self.data.keys():
            for name, shape in self.data["admin"].items():
                admin, flag = AdministrativeWard.objects.update_or_create(
                    city=city, name=name, defaults={"shape": shape, "ward_no": 1}
                )
                self.data["admin"][name] = admin

        if "electoral" in self.data.keys():
            e = self.data["electoral"]
            e = sorted(e.values(), key=lambda x: x["admin_name"])

            for admin_ward, electorals in groupby(e, key=lambda x: x["admin_name"]):
                # Match electoral -> administrative ward by ward number
                # instead of raw substring text, so formatting
                # differences ("Admin Boundary 8" vs "Ward 8" vs "8")
                # no longer cause a silent match failure
                admin_num = self._ward_number(admin_ward)
                admin_key = [
                    x
                    for x in self.data["admin"].keys()
                    if self._ward_number(x) == admin_num and admin_num is not None
                ]
                if len(admin_key) > 0:
                    admin = self.data["admin"][admin_key[0]]
                    for electoral in electorals:
                        electoral_ward, flag = ElectoralWard.objects.update_or_create(
                            administrative_ward=admin,
                            name=electoral["name"],
                            ward_no=electoral["ward_no"],
                            defaults={
                                "shape": electoral["shape"],
                                "ward_code": electoral["ward_no"],
                            },
                        )
                        self.data["electoral"][
                            str(electoral["ward_no"])
                        ] = electoral_ward
                else:
                    print(
                        "No matching administrative ward found for: "
                        + str(admin_ward)
                    )

        if "slum" in self.data.keys():
            for slum in self.data["slum"]:
                if (
                    slum["ward_no"] != "0"
                    and str(slum["ward_no"]) in self.data["electoral"].keys()
                ):
                    electoral = self.data["electoral"][str(slum["ward_no"])]
                    slum_rec, flag = Slum.objects.update_or_create(
                        name=slum["name"],
                        electoral_ward=electoral,
                        defaults={"shape": slum["shape"]},
                    )