"""Console changes for the survey core: switch-driven visibility, the all-encounters
job card, and the subject explorer."""

import json

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from avni import paths
from avni.client import reset_client, use_client
from avni.tests.support import FakeApi, encounter_record, make_city, make_slum, subject_record
from avni_console import catalog
from avni_console.tests.test_bulk_update import workbook_bytes
from notification.models import JobRequest
from survey import connector
from survey.models import Record, SyncSwitch
from survey.store import SyncContext

SYNC_GROUP = "Data Team"


@override_settings(AVNI_SYNC_GROUPS=[SYNC_GROUP], AVNI_SUBJECT_PREVIEW_MAX_IDS=3)
class SurveyConsoleTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.sync_user = User.objects.create_user("sync", password="x")
        self.sync_user.groups.add(Group.objects.create(name=SYNC_GROUP))
        self.api = FakeApi()
        use_client(self.api)
        connector.reset_provider()
        self.addCleanup(reset_client)
        self.addCleanup(connector.reset_provider)

    def switch(self, subject_type="Household", kind="subject", program="", encounter_type="", enabled=True):
        return SyncSwitch.objects.create(
            provider="avni", subject_type=subject_type, kind=kind, program=program,
            encounter_type=encounter_type, is_enabled=enabled,
        )

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")


class VisibilityTests(SurveyConsoleTestCase):
    def test_every_card_shows_when_nothing_is_switched_off(self):
        self.client.force_login(self.sync_user)
        response = self.client.get(reverse("avni_console:index"))
        keys = [job.key for job in response.context["jobs"]]
        self.assertIn("household_encounter_sync", keys)
        self.assertIn("daily_reporting_sync", keys)
        self.assertNotIn("subject_sync", keys, "hidden jobs have no card")
        self.assertNotIn("member_sync", keys, "members wait for their switch")

    def test_a_switched_off_job_has_no_card_and_cannot_be_queued(self):
        self.switch("Household", "program_encounter", "Sanitation program", "Daily Reporting", enabled=False)
        self.client.force_login(self.sync_user)
        response = self.client.get(reverse("avni_console:index"))
        self.assertNotIn("daily_reporting_sync", [job.key for job in response.context["jobs"]])
        response = self.post_json(reverse("avni_console:queue", args=["daily_reporting_sync"]), {"from_date": "2026-01-01"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("switched off", response.json()["error"])
        self.assertFalse(JobRequest.objects.exists())

    def test_the_member_card_appears_once_its_switch_is_on(self):
        self.switch("Family Member")
        self.client.force_login(self.sync_user)
        response = self.client.get(reverse("avni_console:index"))
        self.assertIn("member_sync", [job.key for job in response.context["jobs"]])

    def test_subject_and_encounter_type_lists_follow_the_switches(self):
        self.switch("Structure", enabled=False)
        self.switch("Household", "encounter", "", "Waste", enabled=False)
        self.switch("Household", "encounter", "", "Water")
        self.switch("Detailed Socio Economic Survey", "encounter", "", "Water INP")
        self.client.force_login(self.sync_user)
        response = self.client.get(reverse("avni_console:index"))
        self.assertEqual(response.context["subject_types"], ["Household", "Detailed Socio Economic Survey"])
        self.assertNotIn("Waste", response.context["encounter_types"])
        self.assertIn("Water", response.context["encounter_types"])
        self.assertEqual([value for value, label in response.context["household_encounter_types"]], ["Water", "Water INP"])
        self.assertContains(response, 'name="household_encounter_types" value="Water INP"')

    def test_queue_household_encounter_sync_with_ticked_forms(self):
        self.switch("Household", "encounter", "", "Water")
        self.client.force_login(self.sync_user)
        response = self.post_json(reverse("avni_console:queue", args=["household_encounter_sync"]),
                                  {"from_date": "2026-05-01", "household_encounter_types": ["Water"]})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(JobRequest.objects.get().params, {"from_date": "2026-05-01", "encounter_types": ["Water"]})

    def test_a_switched_off_form_is_refused(self):
        self.switch("Household", "encounter", "", "Water", enabled=False)
        self.client.force_login(self.sync_user)
        response = self.post_json(reverse("avni_console:queue", args=["household_encounter_sync"]),
                                  {"household_encounter_types": ["Water"]})
        self.assertEqual(response.status_code, 400)

    def test_rhs_sync_offers_dses_and_refuses_switched_off_types(self):
        self.switch("Structure", enabled=False)
        self.client.force_login(self.sync_user)
        ok = self.post_json(reverse("avni_console:queue", args=["rhs_sync"]),
                            {"subject_types": ["Detailed Socio Economic Survey"], "from_date": "2026-01-01"})
        self.assertEqual(ok.status_code, 200, ok.content)
        refused = self.post_json(reverse("avni_console:queue", args=["rhs_sync"]),
                                 {"subject_types": ["Structure"], "from_date": "2026-01-01"})
        self.assertEqual(refused.status_code, 400)

    def test_describe_mentions_subject_counts(self):
        self.assertEqual(catalog.describe("subject_sync", {"subject_ids": ["a", "b"]}), "2 subject(s)")


class ExplorerTests(SurveyConsoleTestCase):
    def setUp(self):
        super(ExplorerTests, self).setUp()
        subject = subject_record()
        subject["encounters"] = ["enc-1", "enc-2"]
        scheduled = encounter_record("enc-2", "Water", observations={})
        scheduled["Encounter date time"] = None
        self.api.routes[paths.subject("sub-1")] = subject
        self.api.routes[paths.encounter("enc-1")] = encounter_record("enc-1", "Sanitation")
        self.api.routes[paths.encounter("enc-2")] = scheduled
        self.url = reverse("avni_console:subjects")
        self.preview_url = reverse("avni_console:subject_preview")
        self.sync_url = reverse("avni_console:subject_sync_queue")

    def test_access(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(User.objects.create_user("outsider", password="x"))
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.sync_user)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_empty_page_lists_nothing(self):
        self.client.force_login(self.sync_user)
        response = self.client.get(self.url)
        self.assertEqual(response.context["subjects"], [])
        self.assertEqual(response.context["preview_max"], 3)

    def test_pasted_uuids_render_identity_and_forms_with_badges(self):
        self.client.force_login(self.sync_user)
        response = self.client.post(self.preview_url, {"uuids": "sub-1\nsub-1, ghost"})
        self.assertEqual(response.status_code, 200)
        subjects = response.context["subjects"]
        self.assertEqual([s["subject_id"] for s in subjects], ["sub-1", "ghost"], "duplicates collapse, order kept")
        described = subjects[0]
        self.assertEqual((described["subject_type"], described["slum"], described["household_number"]), ("Household", "Lokmanya Nagar", "42"))
        self.assertEqual([f["status"] for f in described["forms"]], ["done", "done", "scheduled"])
        self.assertEqual((described["done"], described["scheduled"], described["pending"]), (2, 1, 2))
        self.assertIn("error", subjects[1])
        self.assertContains(response, "scheduled")
        self.assertContains(response, "not found")
        self.assertEqual(response.context["subject_ids"], ["sub-1", "ghost"])
        self.assertEqual(Record.objects.count(), 0, "preview writes nothing")

    def test_a_get_with_uuids_previews_too(self):
        self.client.force_login(self.sync_user)
        response = self.client.get(self.url, {"uuids": "sub-1"})
        self.assertEqual(len(response.context["subjects"]), 1)

    def test_excel_upload_gives_the_same_ids_as_pasting(self):
        self.client.force_login(self.sync_user)
        upload = SimpleUploadedFile("ids.xlsx", workbook_bytes([["uuid", "note"], ["sub-1", "x"], [None, None], ["sub-1", ""]]))
        response = self.client.post(self.preview_url, {"file": upload})
        self.assertEqual(response.context["subject_ids"], ["sub-1"])

    def test_excel_without_uuid_column_is_refused(self):
        self.client.force_login(self.sync_user)
        upload = SimpleUploadedFile("ids.xlsx", workbook_bytes([["id"], ["sub-1"]]))
        response = self.client.post(self.preview_url, {"file": upload})
        self.assertIn("uuid", response.context["error"])
        self.assertEqual(response.context["subjects"], [])

    def test_nothing_given_is_an_inline_error(self):
        self.client.force_login(self.sync_user)
        response = self.client.post(self.preview_url, {"uuids": ""})
        self.assertIn("at least one", response.context["error"])

    def test_only_the_first_few_are_previewed_but_all_are_synced(self):
        self.client.force_login(self.sync_user)
        response = self.client.post(self.preview_url, {"uuids": "sub-1,b,c,d,e"})
        self.assertEqual([s["subject_id"] for s in response.context["subjects"]], ["sub-1", "b", "c"])
        self.assertEqual(response.context["not_previewed"], ["d", "e"])
        self.assertEqual(response.context["subject_ids"], ["sub-1", "b", "c", "d", "e"])
        self.assertContains(response, "2 more subject(s) not previewed")
        response = self.post_json(self.sync_url, {"subject_ids": ["a", "b", "c", "d", "e"]})
        self.assertEqual(response.status_code, 200, "the background sync has no cap")
        self.assertEqual(len(JobRequest.objects.get().params["subject_ids"]), 5)

    def test_synced_forms_are_marked_after_a_sync(self):
        connector.sync_record("subject", subject_record(), SyncContext(connector.provider()))
        self.client.force_login(self.sync_user)
        response = self.client.post(self.preview_url, {"uuids": "sub-1"})
        forms = response.context["subjects"][0]["forms"]
        self.assertTrue(forms[0]["synced"])
        self.assertFalse(forms[1]["synced"])

    def test_sync_button_queues_a_subject_sync_request(self):
        self.client.force_login(self.sync_user)
        response = self.post_json(self.sync_url, {"subject_ids": ["sub-1", "sub-1", "other"]})
        self.assertEqual(response.status_code, 200, response.content)
        request = JobRequest.objects.get()
        self.assertEqual(request.job_key, "subject_sync")
        self.assertEqual(request.params, {"subject_ids": ["sub-1", "other"]})
        self.assertEqual(request.requested_by, self.sync_user)
        self.assertIn("2 subject(s)", response.json()["message"])

    def test_the_same_list_cannot_be_queued_twice(self):
        self.client.force_login(self.sync_user)
        self.post_json(self.sync_url, {"subject_ids": ["sub-1"]})
        self.assertEqual(self.post_json(self.sync_url, {"subject_ids": ["sub-1"]}).status_code, 409)

    def test_an_empty_sync_is_refused(self):
        self.client.force_login(self.sync_user)
        self.assertEqual(self.post_json(self.sync_url, {"subject_ids": []}).status_code, 400)

    def test_the_console_links_to_the_explorer(self):
        self.client.force_login(self.sync_user)
        self.assertContains(self.client.get(reverse("avni_console:index")), self.url)


class CatalogBuilderTests(SurveyConsoleTestCase):
    def test_household_subject_type_builders(self):
        self.switch("Structure", enabled=False)
        self.assertEqual(catalog.build_params("household_encounter_sync", {"household_subject_types": "Household"}),
                         {"subject_types": ["Household"]})
        with self.assertRaises(catalog.ParamError):
            catalog.build_params("household_encounter_sync", {"household_subject_types": ["Structure"]})
        with self.assertRaises(catalog.ParamError):
            catalog.build_params("household_encounter_sync", {"household_encounter_types": ["Nope"]})
        self.assertEqual(catalog.build_params("household_encounter_sync", {}), {})

    def test_subject_ids_builder_and_encounter_type_switch(self):
        self.assertEqual(catalog.build_params("subject_sync", {"subject_ids": "a, b"}), {"subject_ids": ["a", "b"]})
        with self.assertRaises(catalog.ParamError):
            catalog.build_params("subject_sync", {"subject_ids": ""})
        self.switch("Household", "encounter", "", "Water", enabled=False)
        with self.assertRaises(catalog.ParamError):
            catalog.build_params("encounter_sync", {"encounter_types": ["Water"]})

    def test_describe_resume_and_choice_labels(self):
        self.assertEqual(catalog.describe("rhs_sync", {"resume_run": 7}), "resumes run #7")
        self.switch("Household", "enrolment", "Sanitation program", "")
        self.switch("Household", "program_encounter", "Sanitation program", "Survey")
        choices = dict(catalog.household_encounter_choices())
        self.assertEqual(choices, {"Survey": "Survey (Household, program encounter)"},
                         "enrolments cannot be listed, so they are not offered")


class ExplorerEdgeTests(SurveyConsoleTestCase):
    def test_a_bad_upload_and_a_non_xlsx_upload_are_refused(self):
        self.client.force_login(self.sync_user)
        url = reverse("avni_console:subject_preview")
        response = self.client.post(url, {"file": SimpleUploadedFile("ids.csv", b"uuid\nx")})
        self.assertIn(".xlsx", response.context["error"])
        response = self.client.post(url, {"file": SimpleUploadedFile("ids.xlsx", b"not a workbook")})
        self.assertIn("could not be read", response.context["error"])

    def test_an_avni_error_is_shown_inline(self):
        from avni.client import AvniError

        self.api.routes[paths.subject("down")] = AvniError(503, "x", "busy")
        self.client.force_login(self.sync_user)
        with mock_no_pause():
            response = self.client.get(reverse("avni_console:subjects"), {"uuids": "down"})
        self.assertIn("AVNI", response.context["subjects"][0]["error"])


class mock_no_pause(object):
    def __enter__(self):
        from avni import provider

        self.original = provider.sleep
        provider.sleep = lambda seconds: None

    def __exit__(self, *args):
        from avni import provider

        provider.sleep = self.original


class ExplorerGenericErrorTests(SurveyConsoleTestCase):
    def test_any_other_error_is_shown_inline(self):
        from unittest import mock

        self.client.force_login(self.sync_user)
        with mock.patch("avni_console.views.connector.describe_subject", side_effect=RuntimeError("odd")):
            response = self.client.get(reverse("avni_console:subjects"), {"uuids": "x"})
        self.assertEqual(response.context["subjects"][0]["error"], "odd")
