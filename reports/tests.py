from collections import OrderedDict
from unittest import mock

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from graphs.models import SlumData
from master.models import Rapid_Slum_Appraisal
from reports.services.rim_compare import compare
from reports.services import rim_factsheet
from reports.services.rim_factsheet import map_rim_data
from reports.views import previous_version
from survey import versioning
from survey.tests.support import make_city, make_slum


def section(fields, meta=None):
    return {"fields": OrderedDict(fields), "meta": meta or {}}


def context(sections):
    return {"sections": OrderedDict(sections)}


# The map slot is always the section's first field, so every fixture starts
# with one, the way map_rim_data builds it.
def general(**fields):
    base = [("Map", "map.png")]
    base.extend(fields.items())
    return section(base)


class CompareTests(SimpleTestCase):
    """The comparison keeps the whole factsheet and marks what moved."""

    def test_identical_versions_produce_no_comparison(self):
        ctx = context([("General", general(Households="412"))])
        self.assertIsNone(compare(ctx, ctx))

    def test_a_changed_field_carries_both_values_and_is_marked(self):
        old = context([("General", general(Households="412"))])
        new = context([("General", general(Households="486"))])

        result = compare(old, new)

        self.assertEqual(
            result["sections"]["General"]["fields"]["Households"],
            {"old": "412", "new": "486", "changed": True},
        )

    def test_an_unchanged_field_is_kept_and_marked_unchanged(self):
        old = context([("General", general(Households="412", Area="38274"))])
        new = context([("General", general(Households="486", Area="38274"))])

        result = compare(old, new)

        self.assertEqual(
            result["sections"]["General"]["fields"]["Area"],
            {"old": "38274", "new": "38274", "changed": False},
        )

    def test_a_section_with_no_change_is_still_shown(self):
        """The PDF reads like the factsheet, so every section keeps its page."""
        old = context([
            ("General", general(Households="412")),
            ("Water", general(Taps="12")),
        ])
        new = context([
            ("General", general(Households="486")),
            ("Water", general(Taps="12")),
        ])

        result = compare(old, new)

        self.assertEqual(list(result["sections"]), ["General", "Water"])
        self.assertFalse(result["sections"]["Water"]["fields"]["Taps"]["changed"])

    def test_a_section_records_how_many_of_its_fields_moved(self):
        old = context([
            ("General", general(Households="412", Area="38274")),
            ("Water", general(Taps="12")),
        ])
        new = context([
            ("General", general(Households="486", Area="40000")),
            ("Water", general(Taps="12")),
        ])

        result = compare(old, new)

        self.assertEqual(result["sections"]["General"]["changed"], 2)
        self.assertEqual(result["sections"]["Water"]["changed"], 0)

    def test_image_slots_are_never_compared(self):
        """Signed image URLs differ on every fetch, so they are not real changes."""
        old = context([("General", section([
            ("Map", "old-map.png"), ("Photo1", "a.jpg"), ("Photo2", "b.jpg"),
        ]))])
        new = context([("General", section([
            ("Map", "new-map.png"), ("Photo1", "c.jpg"), ("Photo2", "d.jpg"),
        ]))])

        self.assertIsNone(compare(old, new))

    def test_a_field_the_older_version_never_had_counts_as_new(self):
        old = context([("General", general(Households="412"))])
        new = context([("General", general(Households="412", Toilets="3"))])

        result = compare(old, new)

        self.assertEqual(
            result["sections"]["General"]["fields"]["Toilets"],
            {"old": "NA", "new": "3", "changed": True},
        )

    def test_a_field_dropped_in_the_newer_version_counts_as_a_change(self):
        old = context([("General", general(Households="412", Toilets="3"))])
        new = context([("General", general(Households="412"))])

        result = compare(old, new)

        self.assertEqual(
            result["sections"]["General"]["fields"]["Toilets"],
            {"old": "3", "new": "NA", "changed": True},
        )

    def test_the_total_counts_only_what_changed(self):
        old = context([
            ("General", general(Households="412", Area="38274")),
            ("Water", general(Taps="12")),
        ])
        new = context([
            ("General", general(Households="486", Area="40000")),
            ("Water", general(Taps="20")),
        ])

        result = compare(old, new)

        self.assertEqual(result["count"], 3)

    def test_the_section_meta_is_carried_through_for_the_page_layout(self):
        old = context([("General", section([("Map", "m.png"), ("Households", "412")], meta={"map_ok": True}))])
        new = context([("General", section([("Map", "m.png"), ("Households", "486")], meta={"map_ok": True}))])

        result = compare(old, new)

        self.assertTrue(result["sections"]["General"]["meta"]["map_ok"])

    def test_a_missing_context_produces_no_comparison(self):
        ctx = context([("General", general(Households="412"))])
        self.assertIsNone(compare(None, ctx))
        self.assertIsNone(compare(ctx, None))


class CompareImagesTests(SimpleTestCase):
    """Pictures are compared on the stored path, never the displayed URL."""

    def ctx(self, map_url, photo):
        return context([("General", section([
            ("general_info_map", map_url),
            ("general_image_1_bottom1", photo),
            ("Households", "412"),
        ], meta={"map_ok": True, "img1_ok": True}))])

    def test_a_new_signed_url_for_the_same_picture_is_not_a_change(self):
        """AVNI signs a fresh URL on every fetch, so the URL alone proves nothing."""
        old = self.ctx("https://avni/signed?a=1", "https://avni/p?a=1")
        new = self.ctx("https://avni/signed?a=2", "https://avni/p?a=2")

        result = compare(
            old, new,
            old_raw={"general_info_left_image": "slum/map.png"},
            new_raw={"general_info_left_image": "slum/map.png"},
        )

        self.assertIsNone(result)

    def test_a_different_stored_picture_is_a_change(self):
        old = self.ctx("https://avni/signed?a=1", "https://avni/p?a=1")
        new = self.ctx("https://avni/signed?a=2", "https://avni/p?a=2")

        result = compare(
            old, new,
            old_raw={"general_info_left_image": "slum/map-2021.png"},
            new_raw={"general_info_left_image": "slum/map-2026.png"},
        )

        self.assertTrue(result["sections"]["General"]["images"]["map"]["changed"])
        self.assertEqual(result["count"], 1)

    def test_the_displayed_urls_are_carried_for_both_sides(self):
        old = self.ctx("https://avni/old-map", "https://avni/old-photo")
        new = self.ctx("https://avni/new-map", "https://avni/new-photo")

        result = compare(
            old, new,
            old_raw={"general_info_left_image": "a.png"},
            new_raw={"general_info_left_image": "b.png"},
        )
        images = result["sections"]["General"]["images"]

        self.assertEqual(images["map"]["old"], "https://avni/old-map")
        self.assertEqual(images["map"]["new"], "https://avni/new-map")
        self.assertEqual(images["photo1"]["old"], "https://avni/old-photo")

    def test_without_the_stored_paths_no_picture_is_claimed_to_have_changed(self):
        old = self.ctx("https://avni/signed?a=1", "https://avni/p?a=1")
        new = self.ctx("https://avni/signed?a=2", "https://avni/p?a=2")

        self.assertIsNone(compare(old, new))


class PreviousVersionTests(TestCase):
    """Which earlier version the page compares the chosen one against."""

    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        SlumData.objects.create(
            slum=self.slum, city=self.city, submission_date=timezone.now(), rim_data={"a": 1},
        )
        Rapid_Slum_Appraisal.objects.create(slum_name=self.slum, approximate_population="1250")

    def test_a_slum_never_re_surveyed_has_nothing_to_compare(self):
        self.assertIsNone(previous_version(self.slum.id, None))

    def test_the_current_version_compares_against_the_newest_archived_one(self):
        versioning.start_new_version(self.slum.id)
        self.assertEqual(previous_version(self.slum.id, None), 1)

    def test_an_archived_version_compares_against_the_one_before_it(self):
        versioning.start_new_version(self.slum.id)
        SlumData.objects.create(
            slum=self.slum, city=self.city, submission_date=timezone.now(), rim_data={"a": 2},
        )
        versioning.start_new_version(self.slum.id)
        self.assertEqual(previous_version(self.slum.id, 2), 1)

    def test_the_oldest_version_has_nothing_before_it(self):
        versioning.start_new_version(self.slum.id)
        self.assertIsNone(previous_version(self.slum.id, 1))


class ReportPageTests(TestCase):
    """The reports home page: slum search index and the comparison fragment."""

    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.user = User.objects.create_user(
            "reporter", "r@example.com", "pw", is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.user)

    def test_the_page_carries_a_slum_search_index(self):
        response = self.client.get("/reports/")
        self.assertEqual(response.status_code, 200)
        names = [row["name"] for row in response.context["slum_search_index"]]
        self.assertIn(self.slum.name, names)

    def test_a_slum_with_one_version_has_no_comparison(self):
        response = self.client.get("/reports/rim-comparison/{}/".format(self.slum.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.strip(), b"")


class CompareOverRealFactsheetMappingTests(SimpleTestCase):
    """compare() against contexts map_rim_data actually produces."""

    def mapped(self, **raw):
        return map_rim_data(raw)

    def test_a_changed_answer_shows_up_under_its_display_name(self):
        old = self.mapped(year_established_according_to="1970")
        new = self.mapped(year_established_according_to="1975")

        result = compare(old, new)

        self.assertEqual(
            result["sections"]["General"]["fields"]["Year Established"],
            {"old": "1970", "new": "1975", "changed": True},
        )

    def test_the_same_answers_produce_no_comparison(self):
        old = self.mapped(year_established_according_to="1970", legal_status="Notified")
        new = self.mapped(year_established_according_to="1970", legal_status="Notified")

        self.assertIsNone(compare(old, new))

    def test_an_answer_given_for_the_first_time_is_a_change(self):
        old = self.mapped()
        new = self.mapped(legal_status="Notified")

        result = compare(old, new)

        self.assertEqual(
            result["sections"]["General"]["fields"]["Legal Status of Slum"],
            {"old": "NA", "new": "Notified", "changed": True},
        )


class ImageReachabilityTests(SimpleTestCase):
    """AVNI presigns its media for GET only, so HEAD is refused."""

    def test_a_presigned_url_that_refuses_head_is_still_reachable(self):
        class Response(object):
            def __init__(self, status, ctype):
                self.status_code = status
                self.headers = {"Content-Type": ctype}

            def close(self):
                pass

        def head(url, **kwargs):
            return Response(403, "application/xml")

        def get(url, **kwargs):
            return Response(206, "image/jpeg")

        with mock.patch.object(rim_factsheet.requests, "head", head), \
                mock.patch.object(rim_factsheet.requests, "get", get):
            self.assertTrue(rim_factsheet.is_image_reachable("https://s3/presigned"))

    def test_a_missing_image_is_not_reachable(self):
        class Response(object):
            def __init__(self):
                self.status_code = 404
                self.headers = {"Content-Type": "application/xml"}

            def close(self):
                pass

        with mock.patch.object(rim_factsheet.requests, "get", lambda url, **kw: Response()):
            self.assertFalse(rim_factsheet.is_image_reachable("https://s3/gone"))
