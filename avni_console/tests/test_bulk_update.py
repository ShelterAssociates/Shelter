"""The bulk-update job end to end against a fake AVNI."""

import csv
import os
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase
from openpyxl import Workbook

from avni import paths
from avni.client import reset_client, use_client
from avni.tests.support import FakeApi, FakeResponse, subject_record
from avni_console.models import BulkUpdate
from avni_console.services import bulk_update
from avni_console.tests.test_headers_values import make_form
from notification.services import reporting


def workbook_bytes(rows):
    book = Workbook()
    for row in rows:
        book.active.append(row)
    handle, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(handle)
    book.save(path)
    with open(path, "rb") as saved:
        data = saved.read()
    os.remove(path)
    return data


class FailingWritesApi(FakeApi):
    def patch(self, path, body, timeout=None):
        self.writes.append(("PATCH", path, body))
        return FakeResponse(400, {"message": "Concept with name=Bogus not found"})


class BulkUpdateTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="data")
        self.form = make_form("IndividualProfile")
        self.api = FakeApi({
            paths.subject("sub-1"): subject_record("sub-1", observations={"Aadhaar number": 1111}),
            paths.subject("sub-2"): subject_record("sub-2", observations={"Aadhaar number": 2222, "Do you have a toilet at home?": "Yes"}),
        })
        use_client(self.api)

    def tearDown(self):
        reset_client()
        for bulk in BulkUpdate.objects.all():
            if bulk.file and os.path.exists(bulk.file.path):
                os.remove(bulk.file.path)

    def make_bulk(self, rows, header_map=None):
        bulk = BulkUpdate(requested_by=self.user, form=self.form, subject_type="Household", level="registration",
                          original_name="fix.xlsx", headers=rows[0], header_map=header_map or {}, row_count=len(rows) - 1)
        bulk.file.save("fix.xlsx", ContentFile(workbook_bytes(rows)))
        return bulk

    def run_bulk(self, bulk, dry_run, workers=1):
        recorder = reporting.start("avni_bulk_update", trigger="manual")
        bulk_update.run(recorder, {"bulk_update_id": bulk.pk, "dry_run": dry_run, "workers": workers})
        run = recorder.finish()
        bulk.refresh_from_db()
        return run, bulk

    def csv_rows(self, bulk):
        with open(bulk.result_file_path) as handle:
            return list(csv.DictReader(handle))


class DryRunTests(BulkUpdateTestCase):
    def test_dry_run_writes_nothing_and_lists_every_change(self):
        rows = [["uuid", "Aadhaar number", "Do you have a toilet at home?"],
                ["sub-1", 9999, "yes"], ["sub-2", 2222, "Yes"], ["ghost", 1, "No"]]
        run, bulk = self.run_bulk(self.make_bulk(rows), dry_run=True)
        self.assertEqual(self.api.writes, [])
        self.assertEqual(bulk.status, "done")
        self.assertTrue(bulk.dry_run)
        lines = self.csv_rows(bulk)
        by_uuid = {}
        for line in lines:
            by_uuid.setdefault(line["uuid"], []).append(line)
        self.assertEqual({l["field"]: (l["old"], l["new"], l["status"]) for l in by_uuid["sub-1"]},
                         {"Aadhaar number": ("1111", "9999", "would_update"),
                          "Do you have a toilet at home?": ("", "Yes", "would_update")})
        self.assertEqual(by_uuid["sub-2"][0]["status"], "unchanged")
        self.assertEqual(by_uuid["ghost"][0]["status"], "failed")
        self.assertIn("404", by_uuid["ghost"][0]["error"])
        step = run.steps.get(name="update")
        self.assertEqual((step.records_ok, step.records_failed), (2, 1))
        self.assertIn("DRY RUN", bulk.summary)


class ApplyTests(BulkUpdateTestCase):
    def test_apply_patches_changed_rows_only(self):
        rows = [["uuid", "Aadhaar number", "Voided"], ["sub-1", 9999, ""], ["sub-2", 2222, "yes"]]
        run, bulk = self.run_bulk(self.make_bulk(rows), dry_run=False)
        self.assertEqual(len(self.api.writes), 2)
        method, path, body = self.api.writes[0]
        self.assertEqual((method, path), ("PATCH", "api/subject/sub-1"))
        self.assertEqual(body, {"Subject type": "Household", "observations": {"Aadhaar number": 9999}})
        self.assertEqual(self.api.writes[1][2], {"Subject type": "Household", "Voided": True})
        statuses = [(l["uuid"], l["field"], l["status"]) for l in self.csv_rows(bulk)]
        self.assertIn(("sub-1", "Aadhaar number", "updated"), statuses)
        self.assertIn(("sub-2", "Voided", "updated"), statuses)
        self.assertFalse(bulk.dry_run)
        self.assertEqual(run.status, "success")

    def test_bad_cell_fails_that_row_only(self):
        rows = [["uuid", "Aadhaar number"], ["sub-1", "twelve"], ["sub-2", 5]]
        run, bulk = self.run_bulk(self.make_bulk(rows), dry_run=False)
        self.assertEqual(len(self.api.writes), 1)
        failed = [l for l in self.csv_rows(bulk) if l["status"] == "failed"]
        self.assertEqual(failed[0]["uuid"], "sub-1")
        self.assertIn("not a number", failed[0]["error"])
        self.assertEqual(run.status, "partial")

    def test_server_rejection_is_a_failed_row_with_message(self):
        use_client(FailingWritesApi(self.api.routes))
        rows = [["uuid", "Aadhaar number"], ["sub-1", 9999]]
        run, bulk = self.run_bulk(self.make_bulk(rows), dry_run=False)
        line = self.csv_rows(bulk)[0]
        self.assertEqual(line["status"], "failed")
        self.assertIn("Bogus", line["error"])
        self.assertEqual(run.status, "failed")

    def test_unresolved_headers_stop_before_any_write(self):
        rows = [["uuid", "Aadhar numbr"], ["sub-1", 9999]]
        run, bulk = self.run_bulk(self.make_bulk(rows), dry_run=False)
        self.assertEqual(self.api.writes, [])
        self.assertEqual(run.steps.get(name="resolve").status, "failed")
        self.assertIn("Aadhar numbr", run.steps.get(name="resolve").error)
        self.assertEqual(bulk.status, "failed")

    def test_chosen_header_map_is_used(self):
        rows = [["uuid", "Aadhar numbr"], ["sub-1", 9999]]
        run, bulk = self.run_bulk(self.make_bulk(rows, header_map={"Aadhar numbr": "Aadhaar number"}), dry_run=False)
        self.assertEqual(self.api.writes[0][2]["observations"], {"Aadhaar number": 9999})

    def test_missing_uuid_cell_is_failed_row(self):
        rows = [["uuid", "Aadhaar number"], [None, 9999]]
        run, bulk = self.run_bulk(self.make_bulk(rows), dry_run=False)
        self.assertEqual(self.csv_rows(bulk)[0]["status"], "failed")
        self.assertEqual(self.api.writes, [])

    def test_duplicate_uuid_rows_both_processed_in_order(self):
        rows = [["uuid", "Aadhaar number"], ["sub-1", 1], ["sub-1", 2]]
        run, bulk = self.run_bulk(self.make_bulk(rows), dry_run=False)
        self.assertEqual([w[2]["observations"]["Aadhaar number"] for w in self.api.writes], [1, 2])

    def test_workers_path_gives_same_result(self):
        rows = [["uuid", "Aadhaar number"], ["sub-1", 9999], ["sub-2", 8888], ["ghost", 1]]
        run, bulk = self.run_bulk(self.make_bulk(rows), dry_run=False, workers=3)
        self.assertEqual(len(self.api.writes), 2)
        step = run.steps.get(name="update")
        self.assertEqual((step.records_ok, step.records_failed), (2, 1))
        self.assertEqual(sorted(l["uuid"] for l in self.csv_rows(bulk)), ["ghost", "sub-1", "sub-2"])

    def test_missing_bulk_update_id(self):
        recorder = reporting.start("avni_bulk_update", trigger="manual")
        with self.assertRaises(ValueError):
            bulk_update.run(recorder, {"bulk_update_id": 999999})
        recorder.finish()


class ApplyFileTests(BulkUpdateTestCase):
    def test_apply_file_from_shell_records_everything(self):
        handle, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(handle)
        with open(path, "wb") as out:
            out.write(workbook_bytes([["uuid", "Aadhaar number"], ["sub-1", 9999]]))
        try:
            with mock.patch("notification.services.queue.job_email.send_activity_report") as send:
                bulk = bulk_update.apply_file(path, self.form.uuid, "Household", dry_run=False, workers=1, requested_by=self.user)
        finally:
            os.remove(path)
        self.assertEqual(bulk.status, "done")
        self.assertEqual(bulk.job_request.status, "done")
        self.assertEqual(bulk.job_request.job_run.job_key, "avni_bulk_update")
        self.assertEqual(len(self.api.writes), 1)
        send.assert_called_once()

    def test_apply_file_honours_max_rows(self):
        handle, path = tempfile.mkstemp(suffix=".xlsx")
        os.close(handle)
        with open(path, "wb") as out:
            out.write(workbook_bytes([["uuid"], ["sub-1"], ["sub-2"]]))
        try:
            with self.assertRaises(ValueError):
                bulk_update.apply_file(path, self.form.uuid, "Household", max_rows=1)
        finally:
            os.remove(path)
