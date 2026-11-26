"""Mastersheet Excel upload: real .xls/.xlsx only, no DTDs, size-capped, CSRF-protected."""

import io
import re
import zipfile
from unittest import mock

import openpyxl
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase

from utils.uploads import validate_spreadsheet

URL = "/mastersheet/files/"
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def workbook():
    wb = openpyxl.Workbook()
    wb.active.append(["Household number", "Name"])
    wb.active.append(["101", "MARKER"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def with_doctype(data, doctype, encoding="utf-8"):
    src, out = zipfile.ZipFile(io.BytesIO(data)), io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for item in src.infolist():
            body = src.read(item.filename)
            if b"MARKER" in body:
                text = re.sub(r"^<\?xml[^>]*\?>", "", body.decode("utf-8"))
                body = ('<?xml version="1.0"?>' + doctype + text).encode(encoding)
            archive.writestr(item, body)
    return out.getvalue()


def upload(name, data):
    return SimpleUploadedFile(name, data)


class SpreadsheetRuleTests(SimpleTestCase):
    def refused(self, name, data, text):
        with self.assertRaisesMessage(ValidationError, text):
            validate_spreadsheet(upload(name, data))

    def test_real_xlsx_is_accepted_and_still_readable_by_pandas(self):
        import pandas
        file = upload("households.xlsx", workbook())
        validate_spreadsheet(file)
        self.assertEqual(pandas.read_excel(file).iloc[0, 1], "MARKER")

    def test_real_xls_header_is_accepted(self):
        validate_spreadsheet(upload("old.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 600))

    def test_external_entity_and_entity_expansion_are_refused(self):
        self.refused("x.xlsx", with_doctype(workbook(), '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'), "DOCTYPE")
        self.refused("x.xlsx", with_doctype(workbook(), '<!DOCTYPE x [<!ENTITY a "AAAA">]>'), "DOCTYPE")

    def test_utf16_doctype_is_refused_too(self):
        self.refused("x.xlsx", with_doctype(workbook(), '<!DOCTYPE x [<!ENTITY a "A">]>', "utf-16"), "DOCTYPE")

    def test_wrong_types_and_disguised_files_are_refused(self):
        self.refused("data.csv", b"a,b\n1,2\n", "Only .xls and .xlsx")
        self.refused("page.html", b"<html></html>", "Only .xls and .xlsx")
        self.refused("fake.xlsx", b"<html></html>", "not a real .xlsx")
        self.refused("fake.xls", b"<html></html>", "not a real .xls")
        self.refused("none.xlsx", b"", "not a real .xlsx")

    def test_zip_bomb_is_refused(self):
        with mock.patch("utils.uploads.SPREADSHEET_MAX_UNZIPPED_BYTES", 100):
            self.refused("big.xlsx", workbook(), "too large once unpacked")

    def test_missing_file_is_refused(self):
        with self.assertRaisesMessage(ValidationError, "Choose"):
            validate_spreadsheet(None)


class FileOpsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("boss", "b@example.org", "x")
        self.client.force_login(self.user)

    def test_hostile_workbook_never_reaches_the_parser(self):
        bad = with_doctype(workbook(), '<!DOCTYPE x [<!ENTITY a "AAAA">]>')
        with mock.patch("mastersheet.views.handle_uploaded_file") as parser:
            response = self.client.post(URL, {"file": upload("x.xlsx", bad), "slum_code": "1"}, **AJAX)
        parser.assert_not_called()
        self.assertIn("DOCTYPE", response.json()["Upload error"][0])

    def test_real_workbook_is_processed(self):
        with mock.patch("mastersheet.views.handle_uploaded_file", return_value=[["total_records", 1]]) as parser:
            response = self.client.post(URL, {"file": upload("ok.xlsx", workbook()), "slum_code": "1"}, **AJAX)
        parser.assert_called_once()
        self.assertEqual(response.json(), [["total_records", 1]])

    def test_upload_needs_the_csrf_token(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(URL, {"file": upload("ok.xlsx", workbook())}, **AJAX).status_code, 403)
