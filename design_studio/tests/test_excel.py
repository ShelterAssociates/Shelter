import io
import os
import shutil
import tempfile
import zipfile

import openpyxl
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from design_studio.services import check, excel, formats, rows
from design_studio.services.render import DesignRenderer
from design_studio.tests.support import HEADERS, RESOURCES, SAMPLE_ROWS, good_rows, preset, sample_workbook, workbook_bytes


def upload(name, content):
    return SimpleUploadedFile(name, content, content_type="application/octet-stream")


class TempFileCase(SimpleTestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)

    def saved(self, content, name="upload.xlsx"):
        path = os.path.join(self.folder, name)
        with open(path, "wb") as handle:
            handle.write(content)
        return path

    def checked(self, content, plate_type="digipin"):
        sheet = excel.read_sheet(self.saved(content))
        return check.check_sheet(sheet, plate_type, DesignRenderer(preset(plate_type), RESOURCES))


class UploadCheckTests(SimpleTestCase):
    def assert_refused(self, name, content, text):
        with self.assertRaises(excel.UploadError) as caught:
            excel.check_upload(upload(name, content))
        self.assertIn(text, str(caught.exception))

    def test_real_xlsx_accepted(self):
        excel.check_upload(upload("plates.xlsx", workbook_bytes(HEADERS["digipin"], good_rows(2))))

    def test_other_types_refused(self):
        content = workbook_bytes(HEADERS["digipin"], good_rows(1))
        self.assert_refused("plates.xls", content, "Only .xlsx files")
        self.assert_refused("plates.xlsm", content, "Only .xlsx files")
        self.assert_refused("plates.csv", b"House No,DIGIPIN\n1,4J6M8286K8\n", "Only .xlsx files")
        self.assert_refused("renamed.xlsx", b"House No,DIGIPIN\n1,4J6M8286K8\n", "Only .xlsx files")

    def test_macros_refused(self):
        buffer = io.BytesIO(workbook_bytes(HEADERS["digipin"], good_rows(1)))
        with zipfile.ZipFile(buffer, "a") as archive:
            archive.writestr("xl/vbaProject.bin", b"macro")
        self.assert_refused("plates.xlsx", buffer.getvalue(), "contains macros")

    def test_zip_bomb_refused(self):
        buffer = io.BytesIO(workbook_bytes(HEADERS["digipin"], good_rows(1)))
        with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/media/padding.bin", b"\0" * (101 * 1024 * 1024))
        self.assert_refused("plates.xlsx", buffer.getvalue(), "too large once unpacked")

    @override_settings(DESIGN_STUDIO_MAX_UPLOAD_MB=0)
    def test_size_limit(self):
        self.assert_refused("plates.xlsx", workbook_bytes(HEADERS["digipin"], good_rows(1)), "larger than 0 MB")


class HeaderTests(TempFileCase):
    def test_missing_required_columns_named_with_expected_headers(self):
        sheet = excel.read_sheet(self.saved(workbook_bytes(["House No", "DIGIPIN", "Ward"], [["1", "4J6M8286K8", "9"]])))
        with self.assertRaises(excel.UploadError) as caught:
            excel.column_positions(sheet.headers, "digipin")
        message = str(caught.exception)
        self.assertIn("missing the columns Latitude, Longitude, Slum Name", message)
        self.assertIn("House No, DIGIPIN, Latitude, Longitude, Slum Name (optional: Ward, City)", message)

    def test_wrong_plate_type_header(self):
        sheet = excel.read_sheet(self.saved(workbook_bytes(HEADERS["pluscode"], good_rows(1, "pluscode"))))
        with self.assertRaises(excel.UploadError):
            excel.column_positions(sheet.headers, "digipin")

    def test_headers_trimmed_case_insensitive_and_first_non_empty_row(self):
        headers = ["  house no ", "digipin", "LATITUDE", "longitude", "slum name"]
        checked = self.checked(workbook_bytes(headers, [["1", "4J6M8286K8", 16.6929355, 74.45952441, "Nimajga Mal"]], leading_blank_rows=2))
        self.assertEqual(len(checked.made), 1)
        self.assertEqual(checked.made[0].number, 4)

    @override_settings(DESIGN_STUDIO_MAX_ROWS=3)
    def test_row_limit(self):
        with self.assertRaises(excel.UploadError) as caught:
            excel.read_sheet(self.saved(workbook_bytes(HEADERS["digipin"], good_rows(4))))
        self.assertIn("This file has 4 rows; the limit is 3. Split it by slum", str(caught.exception))

    def test_sheet_choice(self):
        path = self.saved(workbook_bytes(HEADERS["digipin"], good_rows(1), extra_sheets=["Other"]))
        self.assertEqual(excel.sheet_names(path), ["Plates", "Other"])
        self.assertEqual(excel.read_sheet(path, "Other").headers, ["anything"])


class RowTests(TempFileCase):
    def test_sample_input_every_row_as_expected(self):
        checked = self.checked(sample_workbook())
        self.assertEqual(len(checked.results), len(SAMPLE_ROWS))
        for result, (values, (status, detail)) in zip(checked.results, SAMPLE_ROWS):
            if status == "made":
                self.assertTrue(result.made, (values, result.reason))
                self.assertEqual(result.file_name, detail)
            else:
                self.assertFalse(result.made, values)
                self.assertEqual(result.reason, detail)
        self.assertEqual(checked.duplicate_codes, {"4J6M8286K8": [2, 6, 7]})
        self.assertEqual([result.number for result in checked.renamed], [7])

    def test_digipin_lat_long_mismatch_is_a_warning_not_a_skip(self):
        checked = self.checked(workbook_bytes(HEADERS["digipin"], [["2", "3728F37K28", 16.69301, 74.45961, "Nimajga Mal"]]))
        self.assertTrue(checked.made[0].made)
        self.assertEqual(checked.made[0].warnings, ["DIGIPIN does not match Latitude/Longitude (computed: 4J6 M828 634)"])

    def test_house_number_rules(self):
        values = {"house_no": 12.0, "code": "4J6M8286K8", "lat": 16.6929355, "long": 74.45952441, "slum": "Nimajga Mal"}
        self.assertEqual(rows.clean_row(values, "digipin")[0]["house_no"], "12")
        with self.assertRaises(rows.RowError) as caught:
            rows.clean_row(dict(values, house_no="123456"), "digipin")
        self.assertEqual(str(caught.exception), "House number longer than 5 characters")

    def test_latitude_longitude_ranges_and_numbers(self):
        values = {"house_no": "1", "code": "4J6M8286K8", "slum": "Nimajga Mal"}
        for lat, long, reason in ((2.4, 74.0, "outside India"), (16.0, 99.6, "outside India"), ("north", 74.0, "Latitude is not a number")):
            with self.assertRaises(rows.RowError) as caught:
                rows.clean_row(dict(values, lat=lat, long=long), "digipin")
            self.assertIn(reason, str(caught.exception))
        self.assertEqual(rows.clean_row(dict(values, lat=38.5, long=63.5, code=rows.codes.encode_digipin(38.5, 63.5)), "digipin")[0]["lat"], "38.5")

    def test_empty_rows_ignored(self):
        checked = self.checked(workbook_bytes(HEADERS["digipin"], [good_rows(1)[0], [None] * 7, ["", " ", None], good_rows(2)[1]]))
        self.assertEqual(checked.total, 2)

    def test_plus_code_rows(self):
        data = [["1", "7J8PMFV5+5RCH", 16.69, 74.45, "Nimajga Mal"], ["2", "PMFV5+5R Ichalkaranji", 16.69, 74.45, "Nimajga Mal"]]
        checked = self.checked(workbook_bytes(HEADERS["pluscode"][:5], data), "pluscode")
        self.assertEqual(checked.made[0].file_name, "7J8PMFV5+5RCH_1.png")
        self.assertEqual(checked.made[0].link, "https://www.google.com/maps/place/16.69,74.45")
        self.assertIn("Invalid plus code", checked.skipped[0].reason)

    def test_text_too_long_is_skipped_with_reason(self):
        checked = self.checked(workbook_bytes(HEADERS["digipin"], [["1", "4J6M8286K8", 16.69, 74.45, "Ambedkar " * 8]]))
        self.assertEqual(checked.skipped[0].reason, "Text too long for slum")

    def test_demo_rows_first_widest_longest(self):
        checked = self.checked(sample_workbook())
        demos = checked.demos(DesignRenderer(preset("digipin"), RESOURCES))
        self.assertEqual([result.number for result in demos], [2, 4])


class ReportTests(TempFileCase):
    def test_plates_xlsx_columns_injection_and_extra_columns(self):
        checked = self.checked(sample_workbook())
        buffer = io.BytesIO()
        excel.write_report(buffer, checked.sheet, checked.results, [("Batch", "x"), ("Note", "=cmd")])
        workbook = openpyxl.load_workbook(io.BytesIO(buffer.getvalue()))
        sheet = workbook["Plates"]
        header = [cell.value for cell in sheet[1]]
        self.assertEqual(header[:8], HEADERS["digipin"] + ["Expected (testing only)"])
        self.assertEqual(header[8:], list(excel.ADDED_HEADERS))
        first = [cell.value for cell in sheet[2]]
        self.assertEqual(first[8:], ["images/4J6M8286K8_1.png", "made", "Same DIGIPIN as row 6, 7", "4J6 M828 6K8", "https://dac.indiapost.gov.in/mydigipin/home/4J6M8286K8"])
        formula_row = [cell.value for cell in sheet[8]]
        self.assertEqual(formula_row[4], "'=HYPERLINK(\"http://example.com\",\"x\")")
        self.assertEqual(formula_row[9:11], ["skipped", "Slum Name contains a formula; type the value instead"])
        self.assertTrue(all(cell.data_type != "f" for row in sheet.iter_rows() for cell in row))
        self.assertEqual([cell.value for cell in workbook["Batch"][3]], ["Note", "'=cmd"])

    def test_safe_prefixes(self):
        for value in ("=1+1", "+1", "-1", "@x", "\tx", "\rx"):
            self.assertEqual(excel.safe(value), "'" + value)
        self.assertEqual(excel.safe("7J8PMFV5+5RCH"), "7J8PMFV5+5RCH")
        self.assertEqual(excel.safe(-1.5), -1.5)


class FormatTests(SimpleTestCase):
    def test_format_files_match_the_hand_off_layout(self):
        for plate_type in ("digipin", "pluscode"):
            workbook = openpyxl.load_workbook(io.BytesIO(formats.workbook_bytes(plate_type)))
            self.assertEqual(workbook.sheetnames, ["Plates", "Instructions"])
            sheet = workbook["Plates"]
            self.assertEqual([cell.value for cell in sheet[1]], HEADERS[plate_type])
            self.assertEqual(sheet["A1"].fill.fgColor.rgb, "002A2468")
            self.assertEqual(sheet["F1"].fill.fgColor.rgb, "00CDC8F0")
            self.assertEqual((sheet["A4"].number_format, sheet["C4"].number_format), ("@", "0.0000000"))
            self.assertEqual(sheet.freeze_panes, "A2")
            self.assertEqual(len(sheet.data_validations.dataValidation), 3)
            self.assertEqual(workbook["Instructions"]["A1"].value, formats.TITLES[plate_type])
