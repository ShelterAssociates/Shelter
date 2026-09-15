"""Console views: access matrix, queueing, dry run, bulk upload flow."""

import json
import os

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from avni import paths
from avni.client import reset_client, use_client
from avni.tests.support import FakeApi, make_city, make_slum, page
from avni_console.models import BulkUpdate
from avni_console.tests.test_bulk_update import workbook_bytes
from avni_console.tests.test_headers_values import make_form
from notification.models import JobRequest

SYNC_GROUP, WRITE_GROUP = "Data Team", "AVNI Writers"


@override_settings(AVNI_SYNC_GROUPS=[SYNC_GROUP], AVNI_WRITE_GROUPS=[WRITE_GROUP], AVNI_BULK_MAX_ROWS=3)
class ConsoleTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.sync_user = User.objects.create_user("sync", password="x")
        self.sync_user.groups.add(Group.objects.create(name=SYNC_GROUP))
        self.writer = User.objects.create_user("writer", password="x")
        self.writer.groups.add(Group.objects.create(name=WRITE_GROUP))
        self.outsider = User.objects.create_user("outsider", password="x")
        self.api = FakeApi()
        use_client(self.api)

    def tearDown(self):
        reset_client()
        for bulk in BulkUpdate.objects.all():
            if bulk.file and os.path.exists(bulk.file.path):
                os.remove(bulk.file.path)

    def post_json(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")


class AccessTests(ConsoleTestCase):
    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("avni_console:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_outsider_forbidden_everywhere(self):
        self.client.force_login(self.outsider)
        for name in ("index", "runs", "bulk_new"):
            self.assertEqual(self.client.get(reverse("avni_console:" + name)).status_code, 403, name)

    def test_sync_user_sees_console_but_not_bulk(self):
        self.client.force_login(self.sync_user)
        self.assertEqual(self.client.get(reverse("avni_console:index")).status_code, 200)
        self.assertEqual(self.client.get(reverse("avni_console:runs")).status_code, 200)
        self.assertEqual(self.client.get(reverse("avni_console:bulk_new")).status_code, 403)

    def test_writer_sees_bulk(self):
        self.client.force_login(self.writer)
        self.assertEqual(self.client.get(reverse("avni_console:bulk_new")).status_code, 200)


class QueueViewTests(ConsoleTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.sync_user)

    def test_queue_rhs_sync(self):
        response = self.post_json(reverse("avni_console:queue", args=["rhs_sync"]),
                                  {"from_date": "2026-01-01", "subject_types": ["Household"]})
        self.assertEqual(response.status_code, 200, response.content)
        request = JobRequest.objects.get()
        self.assertEqual(request.params, {"from_date": "2026-01-01", "subject_types": ["Household"]})
        self.assertEqual(request.requested_by, self.sync_user)
        self.assertIn("queued", response.json()["message"].lower())

    def test_duplicate_pending_request_is_409(self):
        data = {"from_date": "2026-01-01", "subject_types": ["Household"]}
        self.post_json(reverse("avni_console:queue", args=["rhs_sync"]), data)
        response = self.post_json(reverse("avni_console:queue", args=["rhs_sync"]), data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(JobRequest.objects.count(), 1)

    def test_bad_params_400(self):
        response = self.post_json(reverse("avni_console:queue", args=["rhs_sync"]), {"from_date": "01-01-2026", "subject_types": ["Household"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("YYYY-MM-DD", response.json()["error"])

    def test_unknown_job_404(self):
        self.assertEqual(self.post_json(reverse("avni_console:queue", args=["nope"]), {}).status_code, 404)

    def test_bulk_update_cannot_be_queued_here(self):
        self.assertEqual(self.post_json(reverse("avni_console:queue", args=["avni_bulk_update"]), {}).status_code, 404)

    def test_dashboard_is_scheduled_for_night_slot_and_merges(self):
        url = reverse("avni_console:queue", args=["dashboard_update"])
        first = self.post_json(url, {"city_ids": [self.city.id]})
        self.assertEqual(first.status_code, 200)
        self.assertIn("01:00", first.json()["message"])
        other = make_city("Pune")
        second = self.post_json(url, {"city_ids": [other.id]})
        self.assertEqual(second.status_code, 200)
        request = JobRequest.objects.get()
        self.assertEqual(sorted(request.params["city_ids"]), sorted([self.city.id, other.id]))
        self.assertGreater(request.scheduled_for, request.created_on)

    def test_mobilization_all_dates_drops_from_date(self):
        self.post_json(reverse("avni_console:queue", args=["mobilization_sync"]), {"from_date": "2026-01-01", "all_dates": True})
        self.assertEqual(JobRequest.objects.get().params, {"all_dates": True})

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("avni_console:queue", args=["rhs_sync"])).status_code, 405)


class DryRunViewTests(ConsoleTestCase):
    def test_counts_returned(self):
        self.client.force_login(self.sync_user)
        self.api.routes[paths.subjects("Household", "2026-01-01T00:00:00.000Z")] = page(["x"] * 7)
        response = self.post_json(reverse("avni_console:dry_run_rhs"), {"from_date": "2026-01-01", "subject_types": ["Household"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["counts"]["Household"]["total"], 7)
        self.assertEqual(JobRequest.objects.count(), 0)

    def test_requires_from_date(self):
        self.client.force_login(self.sync_user)
        response = self.post_json(reverse("avni_console:dry_run_rhs"), {"subject_types": ["Household"]})
        self.assertEqual(response.status_code, 400)


class RunsViewTests(ConsoleTestCase):
    def test_user_sees_own_requests_only_superuser_all(self):
        JobRequest.objects.create(job_key="rhs_sync", requested_by=self.sync_user, params={})
        JobRequest.objects.create(job_key="rhs_sync", requested_by=self.writer, params={})
        self.client.force_login(self.sync_user)
        self.assertEqual(len(self.client.get(reverse("avni_console:runs")).context["requests"]), 1)
        admin = User.objects.create_superuser("root", "r@x.org", "x")
        self.client.force_login(admin)
        self.assertEqual(len(self.client.get(reverse("avni_console:runs")).context["requests"]), 2)

    def test_run_detail_of_someone_else_is_404(self):
        other = JobRequest.objects.create(job_key="rhs_sync", requested_by=self.writer, params={})
        self.client.force_login(self.sync_user)
        self.assertEqual(self.client.get(reverse("avni_console:run_detail", args=[other.pk])).status_code, 404)


class BulkFlowTests(ConsoleTestCase):
    def setUp(self):
        super().setUp()
        self.form = make_form("IndividualProfile")
        from avni.models import AvniFormMapping

        AvniFormMapping.objects.create(uuid="m1", form=self.form, subject_type="Household")
        self.client.force_login(self.writer)

    def upload(self, rows, **extra):
        data = {"subject_type": "Household", "level": "registration",
                "file": SimpleUploadedFile("fix.xlsx", workbook_bytes(rows))}
        data.update(extra)
        return self.client.post(reverse("avni_console:bulk_new"), data)

    def test_levels_and_questions_json(self):
        response = self.client.get(reverse("avni_console:levels_json") + "?subject_type=Household")
        self.assertEqual(response.json()["registration"]["form_id"], self.form.pk)
        response = self.client.get(reverse("avni_console:questions_json", args=[self.form.pk]))
        names = [q["concept_name"] for q in response.json()["questions"]]
        self.assertIn("Aadhaar number", names)
        self.assertIn("Voided", response.json()["reserved"])

    def test_template_download(self):
        response = self.client.get(reverse("avni_console:template_xlsx", args=[self.form.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])

    def test_upload_creates_draft_and_redirects_to_preview(self):
        response = self.upload([["uuid", "Aadhar numbr"], ["sub-1", 1]])
        bulk = BulkUpdate.objects.get()
        self.assertRedirects(response, reverse("avni_console:bulk_preview", args=[bulk.pk]), fetch_redirect_response=False)
        self.assertEqual((bulk.status, bulk.row_count, bulk.requested_by), ("draft", 1, self.writer))

    def test_upload_over_row_cap_is_refused(self):
        response = self.upload([["uuid"], ["a"], ["b"], ["c"], ["d"]])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ask the developer")
        self.assertEqual(BulkUpdate.objects.count(), 0)

    def test_upload_without_uuid_column_is_refused(self):
        response = self.upload([["Aadhaar number"], [1]])
        self.assertContains(response, "uuid")
        self.assertEqual(BulkUpdate.objects.count(), 0)

    def test_upload_for_unknown_level_is_refused(self):
        response = self.upload([["uuid"], ["a"]], level="encounter", encounter_type="Nope")
        self.assertContains(response, "No form")

    def test_preview_blocks_apply_until_headers_resolve_then_queues(self):
        self.upload([["uuid", "Aadhar numbr"], ["sub-1", 1]])
        bulk = BulkUpdate.objects.get()
        preview = reverse("avni_console:bulk_preview", args=[bulk.pk])
        response = self.client.get(preview)
        self.assertContains(response, "Did you mean")
        self.assertFalse(response.context["can_run"])

        blocked = self.client.post(preview, {"action": "apply"})
        self.assertEqual(blocked.status_code, 200)
        self.assertEqual(JobRequest.objects.count(), 0)

        fixed = self.client.post(preview, {"action": "dry_run", "map__Aadhar numbr": "Aadhaar number"})
        bulk.refresh_from_db()
        self.assertRedirects(fixed, reverse("avni_console:bulk_detail", args=[bulk.pk]), fetch_redirect_response=False)
        self.assertEqual(bulk.header_map, {"Aadhar numbr": "Aadhaar number"})
        request = JobRequest.objects.get()
        self.assertEqual(request.params, {"bulk_update_id": bulk.pk, "dry_run": True})
        self.assertEqual(bulk.status, "queued")

    def test_apply_queues_real_run_and_blocks_second_queue_while_pending(self):
        self.upload([["uuid", "Aadhaar number"], ["sub-1", 1]])
        bulk = BulkUpdate.objects.get()
        preview = reverse("avni_console:bulk_preview", args=[bulk.pk])
        self.client.post(preview, {"action": "apply"})
        self.assertEqual(JobRequest.objects.get().params["dry_run"], False)
        again = self.client.post(preview, {"action": "apply"})
        self.assertEqual(JobRequest.objects.count(), 1)
        self.assertEqual(again.status_code, 200)

    def test_sync_user_cannot_open_someone_elses_bulk(self):
        self.upload([["uuid", "Aadhaar number"], ["sub-1", 1]])
        bulk = BulkUpdate.objects.get()
        self.client.force_login(self.sync_user)
        self.assertEqual(self.client.get(reverse("avni_console:bulk_detail", args=[bulk.pk])).status_code, 403)
