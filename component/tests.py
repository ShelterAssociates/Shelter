"""component.avni_map: the endpoints the Avni mobile app's map picker calls."""

import gzip
import json
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Polygon
from django.test import TestCase, override_settings

from avni import locations
from avni.tests.support import make_city, make_slum
from component.models import Component, Metadata, Section, SubjectStructureMapping

SLUM_UUID = "e275c12b-149e-485a-a9db-93f02a10547c"
KEY = "test-gis-key"
STRUCTURES_URL = "/component/get_structures_for_avni/"
MAPPING_URL = "/component/map_subject_to_structure/"


def footprint(x, y):
    return Polygon(((x, y), (x, y + 0.001), (x + 0.001, y + 0.001), (x + 0.001, y), (x, y)))


def make_metadata(name, section):
    return Metadata.objects.create(
        name=name, section=section, level="S", type="C", display_type="M", visible=True, order=1, blob={},
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
        self.uuid_map = {str(self.slum.id): SLUM_UUID}
        locations.slum_location_uuids.cache_clear()
        locations.slum_ids_by_location_uuid.cache_clear()
        patcher = mock.patch.object(locations, "slum_location_uuids", return_value=self.uuid_map)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(locations.slum_location_uuids.cache_clear)
        self.addCleanup(locations.slum_ids_by_location_uuid.cache_clear)

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
        self.uuid_map[str(self.slum.id + 1000)] = "orphan-uuid"
        locations.slum_ids_by_location_uuid.cache_clear()
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
