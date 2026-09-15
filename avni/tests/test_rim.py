"""Slum RIM registration and community toilet blocks."""

from unittest import mock

from django.test import TestCase

from avni import paths, watermark
from avni.sync import rim
from avni.tests.support import FakeApi, make_city, make_slum, page, subject_record
from graphs.models import SlumData
from master.models import Rapid_Slum_Appraisal


def rim_record(uuid="rim-1", voided=False, **observations):
    general = rim.rim_questions()["General"]
    first_shelter_key, first_concept = next(iter(general.items()))
    data = {first_concept: "answer", "Comment if any ?": "note", "Slum Land owner": ["ULB", "Private"]}
    data.update(observations)
    return subject_record(uuid, voided=voided, number="", observations=data), first_shelter_key


class RimMappingTests(TestCase):
    def test_multiselect_joined(self):
        mapped = rim.map_section({"Slum Land owner": ["ULB", "Private"], "Other": "x"}, {"owner": "Slum Land owner", "other": "Other"})
        self.assertEqual(mapped, {"owner": "ULB, Private", "other": "x"})

    def test_images_only_present_ones(self):
        images = rim.rim_images({"Toilet Image 1": "url1", "Unrelated": 1})
        self.assertEqual(images, {"toilet_image_bottomdown1": "url1"})

    def test_question_file_has_all_sections(self):
        for section in rim.RIM_SECTIONS + [rim.TOILET_SECTION]:
            self.assertIn(section, rim.rim_questions())


class RimSaveTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_creates_slum_data_with_sections(self):
        record, key = rim_record()
        self.assertFalse(rim.save_rim_record(record, self.slum.id))
        row = SlumData.objects.get(slum=self.slum)
        self.assertEqual(row.rim_data["General"][key], "answer")
        self.assertEqual(row.rim_data["Toilet"], [{"toilet_comment": "note"}])
        self.assertEqual(row.city, self.city)

    def test_updates_existing_and_images_when_appraisal_exists(self):
        SlumData.objects.create(slum=self.slum, city=self.city, submission_date="2020-01-01T00:00:00Z", rim_data={"old": 1})
        Rapid_Slum_Appraisal.objects.create(slum_name=self.slum)
        record, key = rim_record(**{"Toilet Image 1": "https://s3/toilet.jpg"})
        self.assertTrue(rim.save_rim_record(record, self.slum.id))
        row = SlumData.objects.get(slum=self.slum)
        self.assertNotIn("old", row.rim_data, "RIM registration replaces the blob")
        self.assertEqual(Rapid_Slum_Appraisal.objects.get(slum_name=self.slum).toilet_image_bottomdown1, "https://s3/toilet.jpg")

    def test_toilet_added_then_replaced_by_name(self):
        SlumData.objects.create(slum=self.slum, city=self.city, submission_date="2020-01-01T00:00:00Z", rim_data={"Toilet": []})
        name_concept = rim.rim_questions()["Toilet"]["ctb name"]
        toilet = subject_record("t1", number="", observations={name_concept: "CTB A", "Comment if any ?": "v1"})
        self.assertTrue(rim.save_toilet_record(toilet))
        toilet["observations"]["Comment if any ?"] = "v2"
        self.assertTrue(rim.save_toilet_record(toilet))
        toilets = SlumData.objects.get(slum=self.slum).rim_data["Toilet"]
        self.assertEqual(len(toilets), 1)
        self.assertEqual(toilets[0]["ctb name"], "CTB A")

    def test_toilet_without_slum_data_is_skipped(self):
        name_concept = rim.rim_questions()["Toilet"]["ctb name"]
        self.assertFalse(rim.save_toilet_record(subject_record("t1", number="", observations={name_concept: "CTB A"})))


class RimSyncTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_unmapped_slum(self):
        with mock.patch("avni.sync.rim.slum_location_uuid", return_value=None):
            self.assertEqual(rim.sync_slum_rim(self.slum.id), (False, 0, False))
            self.assertEqual(rim.sync_slum_toilets(self.slum.id), 0)

    def test_mapped_slum_syncs_and_counts(self):
        record, _ = rim_record()
        name_concept = rim.rim_questions()["Toilet"]["ctb name"]
        toilets = [subject_record("t{}".format(i), number="", observations={name_concept: "CTB {}".format(i)}) for i in range(3)]
        toilets.append(subject_record("tv", voided=True, number="", observations={name_concept: "void"}))
        api = FakeApi({
            paths.subjects(rim.RIM_SUBJECT_TYPE, watermark.EPOCH, "loc-1"): page([record]),
            paths.subjects(rim.TOILET_SUBJECT_TYPE, watermark.EPOCH, "loc-1"): [page(toilets[:2], 2), page(toilets[2:], 2)],
        })
        with mock.patch("avni.sync.rim.slum_location_uuid", return_value="loc-1"):
            self.assertEqual(rim.sync_slum_rim(self.slum.id, api=api), (True, 1, False))
            self.assertEqual(rim.sync_slum_toilets(self.slum.id, api=api), 3)
        toilets = SlumData.objects.get(slum=self.slum).rim_data["Toilet"]
        self.assertEqual(toilets[0], {"toilet_comment": "note"}, "RIM registration keeps the slum comment first")
        self.assertEqual([t["ctb name"] for t in toilets[1:]], ["CTB 0", "CTB 1", "CTB 2"])
