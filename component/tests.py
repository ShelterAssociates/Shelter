"""component.avni_map: the endpoints the Avni mobile app's map picker calls."""

import gzip
import json
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Polygon
from django.test import SimpleTestCase, TestCase, override_settings

from avni.models import AvniForm, AvniFormQuestion, AvniMapFilter
from avni.tests.support import make_city, make_slum
from component.kmlparser import (
    HOUSE_BASE_LAYER_CODE,
    KMLParser,
    KMLValidationError,
    quoted_examples,
    usable_house_no,
)
from component.models import Component, Metadata, Section, SubjectStructureMapping
from survey.models import SlumAlias

SLUM_UUID = "e275c12b-149e-485a-a9db-93f02a10547c"
KEY = "test-gis-key"
STRUCTURES_URL = "/component/get_structures_for_avni/"
MAPPING_URL = "/component/map_subject_to_structure/"


def footprint(x, y):
    return Polygon(((x, y), (x, y + 0.001), (x + 0.001, y + 0.001), (x + 0.001, y), (x, y)))


def make_metadata(name, section, code=None):
    return Metadata.objects.create(
        name=name, section=section, level="S", type="C", display_type="M", visible=True, order=1, blob={}, code=code,
    )


def make_component(slum, metadata, housenumber, x=0.5, y=0.5):
    return Component.objects.create(
        metadata=metadata, housenumber=housenumber, shape=footprint(x, y),
        content_type=ContentType.objects.get_for_model(slum), object_id=slum.id,
    )


@override_settings(AVNI_GIS_API_KEY=KEY)
class AvniMapTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        section = Section.objects.create(name="Structures", order=1)
        self.structure = make_metadata("Structure", section)
        self.road = make_metadata("Road", section)
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id=SLUM_UUID)

    def get_structures(self, avni_uuid=SLUM_UUID, key=KEY, **extra):
        query = {"avni_uuid": avni_uuid} if avni_uuid is not None else {}
        headers = {"HTTP_X_AVNI_GIS_KEY": key} if key is not None else {}
        headers.update(extra)
        return self.client.get(STRUCTURES_URL, query, **headers)

    def post_mapping(self, body, key=KEY, raw=None):
        headers = {"HTTP_X_AVNI_GIS_KEY": key} if key is not None else {}
        data = raw if raw is not None else json.dumps(body)
        return self.client.post(MAPPING_URL, data=data, content_type="application/json", **headers)


class GetStructuresTests(AvniMapTestCase):
    def setUp(self):
        super(GetStructuresTests, self).setUp()
        make_component(self.slum, self.structure, "1", 0.1, 0.1)
        make_component(self.slum, self.structure, "35", 0.2, 0.2)
        make_component(self.slum, self.road, "R1", 0.3, 0.3)  # not a Structure: excluded
        other_slum = make_slum(self.city, name="Elsewhere", code="EL1")
        make_component(other_slum, self.structure, "1", 0.4, 0.4)  # other slum: excluded

    def test_returns_only_the_slums_structures_as_geojson(self):
        response = self.get_structures()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        collection = json.loads(response.content.decode("utf-8"))
        self.assertEqual(collection["type"], "FeatureCollection")
        self.assertEqual(collection["slum_id"], self.slum.id)
        self.assertEqual(collection["slum_name"], self.slum.name)
        self.assertEqual(collection["avni_uuid"], SLUM_UUID)
        self.assertEqual(collection["total"], 2)
        self.assertEqual(sorted(f["properties"]["s"] for f in collection["features"]), ["1", "35"])
        self.assertEqual(collection["features"][0]["geometry"]["type"], "Polygon")

    def test_houses_digitised_as_house_base_layer_count_as_structures(self):
        # Some slums have no "Structure" components; their footprints are the HouseBaseLayer (as export does).
        Component.objects.filter(metadata=self.structure).delete()
        base_layer = make_metadata("Houses", self.structure.section, code="HouseBaseLayer")
        make_component(self.slum, base_layer, "7", 0.1, 0.1)
        make_component(self.slum, base_layer, "0008", 0.2, 0.2)
        collection = json.loads(self.get_structures().content.decode("utf-8"))
        self.assertEqual(sorted(f["properties"]["s"] for f in collection["features"]), ["0008", "7"])

    def test_boundary_is_the_slum_boundary_component_when_one_is_uploaded(self):
        boundary = make_metadata("Slum boundary", self.structure.section)
        component = make_component(self.slum, boundary, "", 0.9, 0.9)
        collection = json.loads(self.get_structures().content.decode("utf-8"))
        self.assertEqual(collection["boundary"], json.loads(component.shape.geojson))
        self.assertEqual(collection["total"], 2)  # the boundary is not a house

    def test_boundary_falls_back_to_the_master_slum_shape(self):
        collection = json.loads(self.get_structures().content.decode("utf-8"))
        self.assertEqual(collection["boundary"], json.loads(self.slum.shape.geojson))

    def test_filters_carry_the_website_colours_keyed_by_avni_concept_and_answers(self):
        section = self.structure.section
        Metadata.objects.create(  # rhs key that the Avni sync renames from a concept
            name="Has own toilet", section=section, level="H", type="F", display_type="M", visible=True, order=1,
            code="group_oi8ts04/Current_place_of_defecation:Own toilet|,|Shared toilet",
            blob={"polycolor": "#00AA00", "linecolor": "#004400"},
        )
        Metadata.objects.create(  # key written through unchanged: concept name is the key itself
            name="Rented", section=section, level="H", type="F", display_type="M", visible=True, order=2,
            code="Ownership status of the house_1:Rented", blob={"polycolor": "#0000AA"},
        )
        Metadata.objects.create(  # no answers, no colour: nothing to colour with
            name="Broken", section=section, level="H", type="F", display_type="M", visible=True, order=3,
            code="Some question", blob={},
        )
        collection = json.loads(self.get_structures().content.decode("utf-8"))
        self.assertEqual(collection["filters"], [
            {"name": "Has own toilet", "concepts": ["Current place of defecation", "Final current place of defecation"],
             "answers": ["Own toilet", "Shared toilet"], "polycolor": "#00AA00", "linecolor": "#004400"},
            {"name": "Rented", "concepts": ["Ownership status of the house_1"],
             "answers": ["Rented"], "polycolor": "#0000AA", "linecolor": None},
        ])

    def test_map_filters_are_the_active_concepts_chosen_in_admin_in_order(self):
        form = AvniForm.objects.create(uuid="f1", name="Household registration", form_type="IndividualProfile", definition={})
        question = lambda uuid, name: AvniFormQuestion.objects.create(
            form=form, uuid="q-" + uuid, question_name=name, concept_name=name, concept_uuid=uuid, data_type="Coded")
        AvniMapFilter.objects.create(question=question("w", "Water source"), order=2)
        AvniMapFilter.objects.create(question=question("t", "Do you have a toilet at home?"), order=1)
        AvniMapFilter.objects.create(question=question("x", "Hidden"), order=0, is_active=False)
        collection = json.loads(self.get_structures().content.decode("utf-8"))
        self.assertEqual(collection["map_filters"], [
            {"concept_uuid": "t", "concept_name": "Do you have a toilet at home?"},
            {"concept_uuid": "w", "concept_name": "Water source"},
        ])

    def test_map_filters_is_empty_until_configured(self):
        self.assertEqual(json.loads(self.get_structures().content.decode("utf-8"))["map_filters"], [])

    def test_gzips_when_the_client_accepts_it(self):
        response = self.get_structures(HTTP_ACCEPT_ENCODING="gzip")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Encoding"], "gzip")
        collection = json.loads(gzip.decompress(response.content).decode("utf-8"))
        self.assertEqual(collection["total"], 2)

    def test_plain_when_the_client_does_not_accept_gzip(self):
        response = self.get_structures()
        self.assertFalse(response.has_header("Content-Encoding"))

    def test_requires_avni_uuid(self):
        self.assertEqual(self.get_structures(avni_uuid=None).status_code, 400)

    def test_unmapped_uuid_is_404(self):
        response = self.get_structures(avni_uuid="not-a-mapped-uuid")
        self.assertEqual(response.status_code, 404)
        self.assertIn("no slum is mapped", response.json()["error"])

    def test_mapped_uuid_for_a_deleted_slum_is_404(self):
        with mock.patch("component.avni_map.slum_id_for_location_uuid", return_value=self.slum.id + 1000):
            self.assertEqual(self.get_structures(avni_uuid="orphan-uuid").status_code, 404)

    def test_wrong_key_is_401(self):
        self.assertEqual(self.get_structures(key="wrong").status_code, 401)
        self.assertEqual(self.get_structures(key=None).status_code, 401)

    @override_settings(AVNI_GIS_API_KEY="")
    def test_unconfigured_key_is_503_not_open(self):
        self.assertEqual(self.get_structures(key="").status_code, 503)

    def test_post_is_not_allowed(self):
        self.assertEqual(self.client.post(STRUCTURES_URL, HTTP_X_AVNI_GIS_KEY=KEY).status_code, 405)


class MapSubjectToStructureTests(AvniMapTestCase):
    def setUp(self):
        super(MapSubjectToStructureTests, self).setUp()
        self.house_35 = make_component(self.slum, self.structure, "35")

    def test_creates_the_mapping_and_resolves_the_footprint(self):
        response = self.post_mapping({"subject_uuid": "sub-1", "structure_id": "35", "avni_uuid": SLUM_UUID})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "ok", "created": True, "subject_uuid": "sub-1", "structure_id": "35",
            "slum_id": self.slum.id, "component_id": self.house_35.id,
        })
        mapping = SubjectStructureMapping.objects.get()
        self.assertEqual((mapping.slum_id, mapping.structure_id, mapping.component_id), (self.slum.id, "35", self.house_35.id))

    def test_zero_padded_number_from_avni_matches_the_map_number(self):
        response = self.post_mapping({"subject_uuid": "sub-1", "structure_id": "0035", "avni_uuid": SLUM_UUID})
        self.assertEqual(response.json()["component_id"], self.house_35.id)
        self.assertEqual(SubjectStructureMapping.objects.get().structure_id, "35")

    def test_numeric_structure_id_is_accepted(self):
        response = self.post_mapping({"subject_uuid": "sub-1", "structure_id": 35, "avni_uuid": SLUM_UUID})
        self.assertEqual(response.json()["component_id"], self.house_35.id)

    def test_resolves_a_house_base_layer_footprint(self):
        Component.objects.filter(metadata=self.structure).delete()
        base_layer = make_metadata("Houses", self.structure.section, code="HouseBaseLayer")
        house = make_component(self.slum, base_layer, "35")
        self.post_mapping({"subject_uuid": "sub-1", "structure_id": "0035", "avni_uuid": SLUM_UUID})
        self.assertEqual(SubjectStructureMapping.objects.get(subject_uuid="sub-1").component, house)

    def test_unknown_structure_is_recorded_without_a_footprint(self):
        response = self.post_mapping({"subject_uuid": "sub-1", "structure_id": "999", "avni_uuid": SLUM_UUID})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["component_id"])
        self.assertIsNone(SubjectStructureMapping.objects.get().component)

    def test_same_subject_again_updates_instead_of_duplicating(self):
        self.post_mapping({"subject_uuid": "sub-1", "structure_id": "35", "avni_uuid": SLUM_UUID})
        response = self.post_mapping({"subject_uuid": "sub-1", "structure_id": "36", "avni_uuid": SLUM_UUID})
        self.assertFalse(response.json()["created"])
        self.assertEqual(SubjectStructureMapping.objects.count(), 1)
        self.assertEqual(SubjectStructureMapping.objects.get().structure_id, "36")

    def test_two_subjects_may_share_a_structure(self):
        self.post_mapping({"subject_uuid": "sub-1", "structure_id": "35", "avni_uuid": SLUM_UUID})
        self.post_mapping({"subject_uuid": "sub-2", "structure_id": "35", "avni_uuid": SLUM_UUID})
        self.assertEqual(SubjectStructureMapping.objects.filter(structure_id="35").count(), 2)

    def test_missing_fields_are_400(self):
        self.assertEqual(self.post_mapping({"structure_id": "35", "avni_uuid": SLUM_UUID}).status_code, 400)
        self.assertEqual(self.post_mapping({"subject_uuid": "sub-1", "avni_uuid": SLUM_UUID}).status_code, 400)
        self.assertEqual(self.post_mapping({"subject_uuid": "sub-1", "structure_id": "35"}).status_code, 400)

    def test_unmapped_slum_is_404(self):
        response = self.post_mapping({"subject_uuid": "sub-1", "structure_id": "35", "avni_uuid": "nope"})
        self.assertEqual(response.status_code, 404)

    def test_malformed_body_is_400(self):
        self.assertEqual(self.post_mapping(None, raw="not json").status_code, 400)
        self.assertEqual(self.post_mapping(None, raw="[1, 2]").status_code, 400)

    def test_requires_key_and_post(self):
        body = {"subject_uuid": "sub-1", "structure_id": "35", "avni_uuid": SLUM_UUID}
        self.assertEqual(self.post_mapping(body, key=None).status_code, 401)
        self.assertEqual(self.client.get(MAPPING_URL, HTTP_X_AVNI_GIS_KEY=KEY).status_code, 405)
        self.assertEqual(SubjectStructureMapping.objects.count(), 0)


# ---------------------------------------------------------------------------
# KML upload: the HouseNo rule
# ---------------------------------------------------------------------------

def simple_data(attributes):
    return "".join(
        '<SimpleData name="{}">{}</SimpleData>'.format(name, value)
        for name, value in attributes.items()
    )


def placemark_xml(name, attributes, with_extended_data=True):
    """One polygon placemark, optionally carrying ExtendedData/SchemaData."""
    extended = ""
    if with_extended_data:
        extended = (
            "<ExtendedData><SchemaData>{}</SchemaData></ExtendedData>".format(
                simple_data(attributes)
            )
        )
    return (
        "<Placemark><name>{}</name>{}"
        "<Polygon><outerBoundaryIs><LinearRing><coordinates>"
        "73.80,18.50 73.81,18.50 73.81,18.51 73.80,18.51 73.80,18.50"
        "</coordinates></LinearRing></outerBoundaryIs></Polygon>"
        "</Placemark>".format(name, extended)
    )


def kml(folder_name, placemarks):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        "<Folder><name>{}</name>{}</Folder>"
        "</Document></kml>".format(folder_name, "".join(placemarks))
    ).encode("utf-8")


class HouseNoRuleTests(TestCase):
    """HouseNo is required on the house base layer and forbidden elsewhere."""

    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        section = Section.objects.create(name="Housing", order=1)
        self.house_layer = make_metadata("Structure", section, code=HOUSE_BASE_LAYER_CODE)
        self.roads = make_metadata("Roads", section, code="Roads")

    def upload(self, folder_name, placemarks):
        KMLParser(kml(folder_name, placemarks), self.slum, False).other_components()

    def rejection(self, folder_name, placemarks):
        with self.assertRaises(KMLValidationError) as caught:
            self.upload(folder_name, placemarks)
        return caught.exception.errors

    def components_of(self, metadata):
        return Component.objects.filter(
            metadata=metadata,
            content_type=ContentType.objects.get_for_model(self.slum),
            object_id=self.slum.id,
        )

    # --- the house base layer requires it ---

    def test_house_layer_with_houseno_on_every_placemark_is_saved(self):
        self.upload(
            HOUSE_BASE_LAYER_CODE,
            [
                placemark_xml("1", {"HouseNo": "101"}),
                placemark_xml("2", {"HouseNo": "102"}),
            ],
        )

        self.assertEqual(
            sorted(self.components_of(self.house_layer).values_list("housenumber", flat=True)),
            ["101", "102"],
        )

    def test_house_layer_with_only_id_is_rejected(self):
        errors = self.rejection(
            HOUSE_BASE_LAYER_CODE,
            [placemark_xml("1", {"ID": "101"}), placemark_xml("2", {"ID": "102"})],
        )

        self.assertEqual(len(errors), 1)
        self.assertIn('"HousesBaseLayer"', errors[0])
        self.assertIn("2 of 2", errors[0])
        self.assertIn("no HouseNo attribute", errors[0])
        self.assertFalse(self.components_of(self.house_layer).exists())

    def test_count_names_only_the_placemarks_that_are_missing_it(self):
        errors = self.rejection(
            HOUSE_BASE_LAYER_CODE,
            [
                placemark_xml("1", {"HouseNo": "101"}),
                placemark_xml("2", {"ID": "102"}),
                placemark_xml("3", {"ID": "103"}),
            ],
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("2 of 3", errors[0])

    def test_houseno_is_matched_whatever_its_case(self):
        for spelling in ("HouseNo", "houseno", "HOUSENO"):
            with self.subTest(spelling=spelling):
                self.components_of(self.house_layer).delete()
                self.upload(HOUSE_BASE_LAYER_CODE, [placemark_xml("1", {spelling: "101"})])
                self.assertEqual(self.components_of(self.house_layer).count(), 1)

    # --- every other layer forbids it ---

    def test_other_layer_carrying_houseno_is_rejected(self):
        errors = self.rejection(
            "Roads", [placemark_xml("1", {"HouseNo": "101"}), placemark_xml("2", {"ID": "2"})]
        )

        self.assertEqual(len(errors), 1)
        self.assertIn('"Roads"', errors[0])
        self.assertIn("1 of 2", errors[0])
        self.assertIn("only the house base layer may use HouseNo", errors[0])
        self.assertFalse(self.components_of(self.roads).exists())

    def test_other_layer_with_only_id_is_saved(self):
        self.upload("Roads", [placemark_xml("1", {"ID": "1"}), placemark_xml("2", {"ID": "2"})])

        self.assertEqual(
            sorted(self.components_of(self.roads).values_list("housenumber", flat=True)),
            ["1", "2"],
        )

    # --- interaction with the existing per-placemark errors ---

    def test_a_placemark_without_extended_data_is_reported_once(self):
        # component_latlong already fails on it; the rule must not pile a
        # second error on top of the same placemark.
        errors = self.rejection(
            HOUSE_BASE_LAYER_CODE, [placemark_xml("1", {}, with_extended_data=False)]
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("no such child", errors[0])

    def test_an_unrecognised_folder_never_reaches_the_rule(self):
        # No Metadata.code matches, so the folder is skipped as unparsed.
        KMLParser(
            kml("NotAComponent", [placemark_xml("1", {"HouseNo": "101"})]), self.slum, False
        ).other_components()

        self.assertFalse(Component.objects.filter(object_id=self.slum.id).exists())


class HouseNoValueTests(HouseNoRuleTests):
    """A HouseNo also has to carry a value, of at most 5 characters."""

    def test_blank_houseno_is_rejected(self):
        errors = self.rejection(
            HOUSE_BASE_LAYER_CODE,
            [placemark_xml("1", {"HouseNo": "101"}), placemark_xml("2", {"HouseNo": ""})],
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("1 of 2", errors[0])
        self.assertIn("unusable HouseNo", errors[0])
        self.assertFalse(self.components_of(self.house_layer).exists())

    def test_houseno_longer_than_five_characters_is_rejected(self):
        errors = self.rejection(
            HOUSE_BASE_LAYER_CODE, [placemark_xml("1", {"HouseNo": "Church"})]
        )

        self.assertEqual(len(errors), 1)
        self.assertIn('"Church"', errors[0])
        self.assertIn("must be 1 to 5 characters", errors[0])

    def test_exactly_five_characters_is_accepted(self):
        self.upload(HOUSE_BASE_LAYER_CODE, [placemark_xml("1", {"HouseNo": "12345"})])

        self.assertEqual(
            list(self.components_of(self.house_layer).values_list("housenumber", flat=True)),
            ["12345"],
        )

    def test_letter_suffixed_sub_unit_is_accepted(self):
        # 2,383 real house footprints use this convention (7366B, 7369A) for
        # sub-units, so the limit is 5 characters and not 5 digits.
        self.upload(HOUSE_BASE_LAYER_CODE, [placemark_xml("1", {"HouseNo": "7366B"})])

        self.assertEqual(
            list(self.components_of(self.house_layer).values_list("housenumber", flat=True)),
            ["7366B"],
        )

    def test_surrounding_whitespace_does_not_count_towards_the_limit(self):
        self.upload(HOUSE_BASE_LAYER_CODE, [placemark_xml("1", {"HouseNo": "  101  "})])

        self.assertEqual(self.components_of(self.house_layer).count(), 1)

    def test_whitespace_only_houseno_counts_as_blank(self):
        errors = self.rejection(HOUSE_BASE_LAYER_CODE, [placemark_xml("1", {"HouseNo": "   "})])

        self.assertEqual(len(errors), 1)
        self.assertIn("unusable HouseNo", errors[0])

    def test_repeated_bad_value_also_trips_the_duplicate_rule(self):
        # Two placemarks sharing one bad HouseNo is both unusable and a
        # duplicate, and each rule reports it.
        errors = self.rejection(
            HOUSE_BASE_LAYER_CODE,
            [placemark_xml("1", {"HouseNo": "Mandir"}), placemark_xml("2", {"HouseNo": "Mandir"})],
        )

        self.assertTrue(any("duplicate placemark id" in e for e in errors))
        self.assertTrue(any("unusable HouseNo" in e for e in errors))

    def test_more_than_five_distinct_bad_values_are_summarised(self):
        errors = self.rejection(
            HOUSE_BASE_LAYER_CODE,
            [placemark_xml(str(i), {"HouseNo": "Mandir-{}".format(i)}) for i in range(8)],
        )

        self.assertIn("and 3 more", errors[0])

    def test_missing_and_unusable_are_reported_separately(self):
        errors = self.rejection(
            HOUSE_BASE_LAYER_CODE,
            [
                placemark_xml("1", {"ID": "1"}),
                placemark_xml("2", {"HouseNo": ""}),
                placemark_xml("3", {"HouseNo": "103"}),
            ],
        )

        self.assertEqual(len(errors), 2)
        self.assertIn("no HouseNo attribute", errors[0])
        self.assertIn("unusable HouseNo", errors[1])

    def test_other_layers_are_not_length_checked(self):
        # Roads must not carry HouseNo at all; its ID can be any length.
        self.upload("Roads", [placemark_xml("1", {"ID": "Main approach road"})])

        self.assertEqual(self.components_of(self.roads).count(), 1)


class HouseNoHelperTests(SimpleTestCase):
    """The pure helpers behind the HouseNo rule."""

    def test_usable_house_no(self):
        for value in ("1", "101", "12345", "7366B"):
            self.assertTrue(usable_house_no(value), value)
        for value in ("", "123456", "Church", "Mahadev Mandir"):
            self.assertFalse(usable_house_no(value), value)

    def test_quoted_examples_are_distinct_and_ordered(self):
        self.assertEqual(
            quoted_examples(["Church", "Masjid", "Church"]), '"Church", "Masjid"'
        )

    def test_quoted_examples_caps_at_five_distinct(self):
        self.assertEqual(
            quoted_examples(["a", "b", "c", "d", "e", "f", "g"]),
            '"a", "b", "c", "d", "e", and 2 more',
        )

    def test_quoted_examples_of_nothing(self):
        self.assertEqual(quoted_examples([]), "")
