"""Server errors are logged; the browser gets a plain message, never the exception text."""

import io
from unittest import mock

import openpyxl
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from avni.tests.support import make_city, make_slum
from mastersheet.views import UPLOAD_FAILED

SECRET = "SECRET-INTERNAL-DETAIL"
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
PYTHON_TEXT = ("Traceback", "referenced before assignment", "matching query", "local variable", SECRET)


def workbook(*rows):
    wb = openpyxl.Workbook()
    for row in rows:
        wb.active.append(row)
    data = io.BytesIO()
    wb.save(data)
    return SimpleUploadedFile("households.xlsx", data.getvalue())


class ErrorMessageCase(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("boss", "b@example.org", "x"))
        self.slum = make_slum(make_city())

    def assert_no_internal_text(self, response):
        body = response.content.decode()
        for text in PYTHON_TEXT:
            self.assertNotIn(text, body)


class MastersheetUploadTests(ErrorMessageCase):
    def upload(self, file, slum=None):
        return self.client.post("/mastersheet/files/", {"file": file, "slum_code": slum or self.slum.id}, **AJAX)

    def test_file_without_rhs_columns_is_not_reported_as_an_rhs_error(self):
        response = self.upload(workbook(["Household number", "Note"], ["999999", "dummy"]))
        self.assertEqual(response.json()["total_records"], [1])
        self.assertFalse([key for key in response.json() if "RHS" in key])
        self.assert_no_internal_text(response)

    def test_unknown_slum_gives_a_plain_message(self):
        response = self.upload(workbook(["Household number"], ["101"]), slum=999999)
        self.assertEqual(response.json(), {"Upload error": [UPLOAD_FAILED]})
        self.assert_no_internal_text(response)

    def test_a_failing_row_names_only_the_household(self):
        file = workbook(["Household number", "rhs_update", "HH can connect to Drainage line"], ["101", "1", "Yes"])
        with mock.patch("mastersheet.views.HouseholdData.objects.filter", side_effect=Exception(SECRET)):
            response = self.upload(file)
        self.assertEqual(response.json()["RHS row error (row skipped)"], ["101"])
        self.assert_no_internal_text(response)


class OtherEndpointTests(ErrorMessageCase):
    def test_kobo_sync_error(self):
        with mock.patch("mastersheet.views.avni_rim.sync_slum_rim", side_effect=Exception(SECRET)):
            response = self.client.get("/mastersheet/sync/slum/", {"slumname": self.slum.id}, **AJAX)
        self.assertIn("contact administrator", response.json()["msg"])
        self.assert_no_internal_text(response)

    def test_component_delete_and_metric_errors(self):
        with mock.patch("component.views.Component.objects.filter", side_effect=Exception(SECRET)):
            response = self.client.post("/component/delete_component/", {"object_id": "1", "comp_name": "x", "reason": "r"})
        self.assertEqual(response.status_code, 500)
        self.assert_no_internal_text(response)
        with mock.patch("component.views.Metadata.objects.filter") as metadata, \
                mock.patch("component.views.ComponentMetric.objects.filter", side_effect=Exception(SECRET)):
            metadata.return_value.first.return_value = mock.Mock()
            response = self.client.post("/component/set_component_metric/", {
                "object_id": self.slum.id, "comp_name": "Toilet", "value": "5", "unit": "m", "reason": "r"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["message"], "The metric could not be saved. Please try again.")
        self.assert_no_internal_text(response)

    def test_photo_upload_service_not_configured(self):
        target = "helpers.views.upload_photos_to_slum_drive_folder"
        with mock.patch(target, side_effect=ImproperlyConfigured("PHOTO_UPLOAD_SERVICE_URL " + SECRET)):
            response = self.client.post("/helpers/api/upload-slum-photos-to-drive/", {
                "photos": [SimpleUploadedFile("a.png", _png(), content_type="image/png")], "is_other_upload": "1",
                "custom_folder_name": "Field visit", "slum_id": "", "project_type": "OHOT", "photo_date": "2026-11-01"})
        self.assertEqual(response.status_code, 500)
        self.assert_no_internal_text(response)
        self.assertNotIn("PHOTO_UPLOAD_SERVICE_URL", response.content.decode())


def _png():
    from PIL import Image
    data = io.BytesIO()
    Image.new("RGB", (4, 4), "green").save(data, "PNG")
    return data.getvalue()
