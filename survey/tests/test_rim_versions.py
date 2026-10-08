"""An older RIM stays readable after a re-survey: the backup accessors, the
availability API, and the factsheet reading a frozen version.
"""

import json

from django.test import TestCase
from django.utils import timezone

from graphs.models import HouseholdData, SlumData
from master.models import Rapid_Slum_Appraisal
from survey import versioning
from survey.models import SlumVersionBackup
from survey.tests.support import make_city, make_slum

V1_RIM = {
    "General": {"survey_sector_number": "Thirty", "landmark": "Old landmark"},
    "Water": {"water_source": "Tanker"},
    "Toilet": [{"toilet_comment": "first survey"}],
}
V2_RIM = {
    "General": {"survey_sector_number": "Thirty-one", "landmark": "New landmark"},
    "Water": {"water_source": "Tap"},
    "Toilet": [{"toilet_comment": "second survey"}],
}


class RimBackupAccessorTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        SlumData.objects.create(
            slum=self.slum, city=self.city, submission_date=timezone.now(),
            rim_data=V1_RIM, modified_on=timezone.now(),
        )
        Rapid_Slum_Appraisal.objects.create(slum_name=self.slum, approximate_population="1250")

    def test_live_rim_is_read_when_no_version_is_asked_for(self):
        rim_data, appraisal = versioning.rim_at(self.slum.id)
        self.assertEqual(rim_data["General"]["landmark"], "Old landmark")
        self.assertEqual(appraisal["approximate_population"], "1250")

    def test_a_frozen_version_is_read_back_from_the_backup(self):
        versioning.start_new_version(self.slum.id)
        # the re-survey replaces the live RIM
        SlumData.objects.filter(slum=self.slum).update(rim_data=V2_RIM)

        live, _ = versioning.rim_at(self.slum.id)
        frozen, frozen_appraisal = versioning.rim_at(self.slum.id, 1)
        self.assertEqual(live["General"]["landmark"], "New landmark")
        self.assertEqual(frozen["General"]["landmark"], "Old landmark")
        self.assertEqual(frozen["Toilet"][0]["toilet_comment"], "first survey")
        self.assertEqual(frozen_appraisal["approximate_population"], "1250")

    def test_a_json_string_in_the_backup_is_parsed_back(self):
        """jsonfield dumps a JSONField as a string, so it has to be decoded."""
        versioning.start_new_version(self.slum.id)
        row = SlumVersionBackup.objects.get(slum=self.slum, source_model=versioning.SLUM_DATA_LABEL)
        self.assertIsInstance(row.data["fields"]["rim_data"], str)

        fields = versioning.backup_fields(self.slum.id, 1, versioning.SLUM_DATA_LABEL)
        self.assertIsInstance(fields["rim_data"], dict)
        self.assertEqual(fields["rim_data"], json.loads(row.data["fields"]["rim_data"]))

    def test_an_unknown_version_reads_as_nothing(self):
        self.assertEqual(versioning.rim_at(self.slum.id, 9), (None, None))
        self.assertIsNone(versioning.backup_fields(self.slum.id, 9, versioning.SLUM_DATA_LABEL))

    def test_the_picker_offers_the_live_one_then_the_archived_ones(self):
        self.assertEqual(
            versioning.rim_choices_for(self.slum.id),
            [{"version": None, "label": "Current", "live": True}],
        )
        versioning.start_new_version(self.slum.id)
        self.assertEqual(
            versioning.rim_choices_for(self.slum.id),
            [
                {"version": None, "label": "Current", "live": True},
                {"version": 1, "label": "Version 1", "live": False},
            ],
        )

    def test_a_cleared_rim_still_offers_the_archived_one(self):
        versioning.start_new_version(self.slum.id, rim_choice=versioning.RIM_CLEAR)
        self.assertFalse(SlumData.objects.filter(slum=self.slum).exists())
        self.assertEqual(
            versioning.rim_choices_for(self.slum.id),
            [{"version": 1, "label": "Version 1", "live": False}],
        )


class FactsheetAvailabilityTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.url = "/admin/api/rim_factsheet_available/{}/".format(self.slum.id)

    def rim(self):
        SlumData.objects.create(
            slum=self.slum, city=self.city, submission_date=timezone.now(), rim_data=V1_RIM,
        )
        Rapid_Slum_Appraisal.objects.create(slum_name=self.slum, approximate_population="1250")

    def test_a_slum_with_no_rim_has_no_factsheet(self):
        body = self.client.get(self.url).json()
        self.assertFalse(body["available"])
        self.assertEqual(body["versions"], [])

    def test_a_slum_with_live_rim_offers_one_version(self):
        self.rim()
        body = self.client.get(self.url).json()
        self.assertTrue(body["available"])
        self.assertEqual(body["versions"], [{"version": None, "label": "Current"}])

    def test_after_a_re_survey_both_versions_are_offered(self):
        self.rim()
        versioning.start_new_version(self.slum.id)
        body = self.client.get(self.url).json()
        self.assertTrue(body["available"])
        self.assertEqual(
            body["versions"],
            [{"version": None, "label": "Current"}, {"version": 1, "label": "Version 1"}],
        )

    def test_a_cleared_rim_keeps_the_factsheet_available_from_the_backup(self):
        """Clearing RIM must not make the factsheet button vanish."""
        self.rim()
        versioning.start_new_version(self.slum.id, rim_choice=versioning.RIM_CLEAR)
        body = self.client.get(self.url).json()
        self.assertTrue(body["available"])
        self.assertEqual(body["versions"], [{"version": 1, "label": "Version 1"}])


class FactsheetReadsTheChosenVersionTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        SlumData.objects.create(
            slum=self.slum, city=self.city, submission_date=timezone.now(),
            rim_data=V1_RIM, modified_on=timezone.now(),
        )
        Rapid_Slum_Appraisal.objects.create(slum_name=self.slum, approximate_population="1250")
        versioning.start_new_version(self.slum.id)
        SlumData.objects.filter(slum=self.slum).update(rim_data=V2_RIM)

    def detail(self, version=None):
        from reports.services.rim_factsheet import get_rim_factsheet_detail

        return get_rim_factsheet_detail(self.slum.id, version)

    def test_the_live_factsheet_shows_the_new_survey(self):
        self.assertEqual(self.detail().get("landmark"), "New landmark")

    def test_the_old_factsheet_is_still_readable(self):
        self.assertEqual(self.detail(1).get("landmark"), "Old landmark")

    def test_a_version_with_no_rim_reports_no_data(self):
        self.assertEqual(self.detail(9).get("data"), "NA")

    def test_the_old_factsheet_keeps_the_real_slum_name(self):
        """The backup stores the appraisal's FK as `slum_name`, which would
        otherwise shadow the slum's display name in the merged context."""
        from reports.services.rim_factsheet import rim_factsheet_view

        for version in (None, 1):
            context = rim_factsheet_view(self.slum.id, version=version)
            self.assertEqual(
                context.get("meta_data", {}).get("slum_name"), self.slum.name,
                "version {} lost the slum name".format(version),
            )

    def test_both_versions_render_with_their_own_data(self):
        from reports.services.rim_factsheet import rim_factsheet_view

        live = rim_factsheet_view(self.slum.id)
        old = rim_factsheet_view(self.slum.id, version=1)
        self.assertNotEqual(live.get("data"), "NA")
        self.assertNotEqual(old.get("data"), "NA")
        self.assertEqual(len(old.get("version_choices") or []), 2)

    def test_the_version_is_part_of_the_pdf_report_id(self):
        from reports.views import rim_report_id

        self.assertEqual(rim_report_id(self.slum.id, None), str(self.slum.id))
        self.assertEqual(rim_report_id(self.slum.id, 1), "{}-v1".format(self.slum.id))


class AutoLockTests(TestCase):
    """A hand-made mapping must survive the nightly AVNI location refresh."""

    def setUp(self):
        from django.contrib.auth.models import User

        self.city = make_city()
        self.slum = make_slum(self.city)
        User.objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.login(username="boss", password="pw")

    def post(self, path, data):
        return self.client.post("/slum-versions/{}/{}".format(self.slum.id, path), data, follow=True)

    def test_mapping_a_location_locks_the_slum(self):
        from survey import slum_sync

        self.assertFalse(slum_sync.is_alias_locked(self.slum.id))
        self.post("locations/add/", {"external_id": "loc-1", "external_name": "Title"})
        self.assertTrue(slum_sync.is_alias_locked(self.slum.id))

    def test_changing_the_rim_source_locks_the_slum(self):
        from survey import slum_sync
        from survey.models import SlumAlias

        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="a", is_primary=True)
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="b", is_primary=False)
        slum_sync.update(self.slum.id, alias_locked=False)

        self.post("locations/primary/", {"external_id": "b"})
        self.assertTrue(slum_sync.is_alias_locked(self.slum.id))


class SlumSearchIndexTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_the_index_carries_the_path_and_version_state(self):
        from survey import views

        rows = {row["id"]: row for row in views.slum_search_index()}
        row = rows[self.slum.id]
        self.assertEqual(row["name"], self.slum.name)
        self.assertIn(self.city.name.city_name, row["path"])
        self.assertEqual((row["version"], row["waiting"], row["locations"]), (1, False, 0))

    def test_a_versioned_slum_shows_as_waiting(self):
        from survey import views
        from survey.models import SlumAlias

        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id="loc-1")
        HouseholdData.objects.create(
            slum=self.slum, city=self.city, household_number="1",
            submission_date=timezone.now(), rhs_data={},
        )
        versioning.start_new_version(self.slum.id)

        row = {r["id"]: r for r in views.slum_search_index()}[self.slum.id]
        self.assertEqual((row["version"], row["waiting"], row["locations"]), (2, True, 1))
        self.assertEqual(
            [r["id"] for r in views.recently_versioned()], [self.slum.id],
        )
