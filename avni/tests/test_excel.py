"""Spreadsheet reading edge cases."""

import os
import tempfile

from django.test import SimpleTestCase
from openpyxl import Workbook

from avni import excel


def workbook(rows):
    book = Workbook()
    for row in rows:
        book.active.append(row)
    handle, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(handle)
    book.save(path)
    return path


class ExcelTests(SimpleTestCase):
    def read(self, rows):
        path = workbook(rows)
        try:
            return excel.read_rows(path)
        finally:
            os.remove(path)

    def test_headers_are_stripped_and_blank_rows_dropped(self):
        headers, rows = self.read([[" uuid ", "Voided", None], ["a", "yes", None], [None, None, None], ["b", "", None]])
        self.assertEqual(headers, ["uuid", "Voided"])
        self.assertEqual(rows, [{"uuid": "a", "Voided": "yes"}, {"uuid": "b", "Voided": None}])

    def test_numbers_and_dates_keep_their_types(self):
        from datetime import datetime

        headers, rows = self.read([["uuid", "n", "d"], ["a", 42, datetime(2026, 1, 2)]])
        self.assertEqual(rows[0]["n"], 42)
        self.assertEqual(rows[0]["d"], datetime(2026, 1, 2))

    def test_empty_sheet(self):
        self.assertEqual(self.read([]), ([], []))

    def test_read_column_missing(self):
        path = workbook([["uuid"], ["a"]])
        try:
            self.assertEqual(excel.read_column(path, "uuid"), ["a"])
            with self.assertRaises(KeyError):
                excel.read_column(path, "nope")
        finally:
            os.remove(path)
