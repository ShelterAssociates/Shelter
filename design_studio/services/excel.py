"""Reading the fixed-format Excel upload and writing plates.xlsx. Formulas are read as text, never evaluated."""

import zipfile

import openpyxl
from django.conf import settings
from django.core.exceptions import ValidationError
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill

from design_studio.services import rows as row_rules
from utils.uploads import SPREADSHEET_MAX_UNZIPPED_BYTES, file_extension, validate_spreadsheet

WRONG_TYPE = "Only .xlsx files can be uploaded. Save the file as an Excel Workbook (.xlsx) and try again."
UNSAFE_START = ("=", "+", "-", "@", "\t", "\r")
ADDED_HEADERS = ("Image file name", "Status", "Reason", "Code on plate", "QR link")
HEADER_FILL = PatternFill("solid", fgColor="2A2468")
HEADER_FONT = Font(bold=True, color="FFFFFF")


class UploadError(ValueError):
    pass


class Sheet(object):
    """Header row and data rows of one worksheet. Each row: (excel row number, [(value, is_formula), ...])."""

    def __init__(self, title, header_number, headers, data):
        self.title = title
        self.header_number = header_number
        self.headers = headers
        self.data = data


def max_rows():
    return int(getattr(settings, "DESIGN_STUDIO_MAX_ROWS", 15000))


def check_upload(upload):
    """Refuse anything but a real, macro-free .xlsx within the size limits. Raises UploadError."""
    if file_extension(getattr(upload, "name", "")) != "xlsx":
        raise UploadError(WRONG_TYPE)
    limit_mb = int(getattr(settings, "DESIGN_STUDIO_MAX_UPLOAD_MB", 10))
    if upload.size > limit_mb * 1024 * 1024:
        raise UploadError("This file is larger than {0} MB; the limit is {0} MB. Split it by slum and upload each part.".format(limit_mb))
    upload.seek(0)
    try:
        if not zipfile.is_zipfile(upload):
            raise UploadError(WRONG_TYPE)
        upload.seek(0)
        with zipfile.ZipFile(upload) as archive:
            names = archive.namelist()
            if "[Content_Types].xml" not in names:
                raise UploadError(WRONG_TYPE)
            if any(name.lower().endswith("vbaproject.bin") for name in names):
                raise UploadError("This workbook contains macros. Save it as an Excel Workbook (.xlsx) without macros and try again.")
            if sum(item.file_size for item in archive.infolist()) > SPREADSHEET_MAX_UNZIPPED_BYTES:
                raise UploadError("The workbook is too large once unpacked. Split it by slum and upload each part.")
        validate_spreadsheet(upload)
    except ValidationError as exc:
        raise UploadError(" ".join(exc.messages))
    finally:
        upload.seek(0)


def open_workbook(path):
    return openpyxl.load_workbook(path, read_only=True, data_only=False)


def sheet_names(path):
    workbook = open_workbook(path)
    try:
        return list(workbook.sheetnames)
    finally:
        workbook.close()


def cell_pairs(cells):
    return [(cell.value, getattr(cell, "data_type", "") == "f") for cell in cells]


def is_empty(pairs):
    return all(value is None or (isinstance(value, str) and not value.strip()) for value, _ in pairs)


def read_sheet(path, sheet_name=""):
    """The sheet's header row (first non-empty row) and its non-empty data rows. Raises UploadError."""
    workbook = open_workbook(path)
    try:
        if sheet_name and sheet_name not in workbook.sheetnames:
            raise UploadError('The workbook has no sheet named "{}".'.format(sheet_name))
        worksheet = workbook[sheet_name] if sheet_name else workbook.worksheets[0]
        header_number, headers, data, count = None, None, [], 0
        for number, cells in enumerate(worksheet.iter_rows(), start=1):
            pairs = cell_pairs(cells)
            if is_empty(pairs):
                continue
            if headers is None:
                header_number, headers = number, [row_rules.text_value(value) for value, _ in pairs]
                continue
            count += 1
            if count <= max_rows():
                data.append((number, pairs))
        if headers is None:
            raise UploadError("The sheet is empty. Fill in the Excel format and upload it again.")
        if count > max_rows():
            raise UploadError("This file has {:,} rows; the limit is {:,}. Split it by slum and upload each part.".format(count, max_rows()))
        return Sheet(worksheet.title, header_number, headers, data)
    finally:
        workbook.close()


def column_positions(headers, plate_type):
    """{key: column index} for the fixed format, or UploadError naming the missing columns."""
    found = {}
    for index, header in enumerate(headers):
        found.setdefault((header or "").strip().lower(), index)
    positions, missing = {}, []
    for key, header, required in row_rules.columns(plate_type):
        if header.lower() in found:
            positions[key] = found[header.lower()]
        elif required:
            missing.append(header)
    if missing:
        raise UploadError("The file is missing the column{} {}. The first row must have these headers: {} (optional: {}).".format(
            "s" if len(missing) > 1 else "", ", ".join(missing),
            ", ".join(row_rules.header_list(plate_type, True)), ", ".join(row_rules.header_list(plate_type, False))))
    return positions


def row_values(pairs, positions):
    """({key: value}, formula keys) for one data row. Formulas in optional columns are left blank."""
    values, formulas = {}, set()
    required = {key for key, _, is_required in row_rules.columns("digipin") if is_required}
    for key, index in positions.items():
        value, is_formula = pairs[index] if index < len(pairs) else (None, False)
        if is_formula:
            formulas.add(key)
            value = value if key in required else None
        values[key] = value
    return values, formulas


def safe(value):
    """Text that Excel could read as a formula gets a leading apostrophe."""
    if isinstance(value, str) and value.startswith(UNSAFE_START):
        return "'" + value
    return value


def header_cells(sheet, titles):
    cells = []
    for title in titles:
        cell = WriteOnlyCell(sheet, value=safe(title))
        cell.fill, cell.font, cell.alignment = HEADER_FILL, HEADER_FONT, Alignment(horizontal="center")
        cells.append(cell)
    return cells


def write_report(target, sheet, results, batch_facts):
    """plates.xlsx: every uploaded column, then file name, status, reason, code and QR link; and a Batch sheet."""
    workbook = openpyxl.Workbook(write_only=True)
    plates = workbook.create_sheet("Plates")
    plates.freeze_panes = "A2"
    plates.append(header_cells(plates, list(sheet.headers) + list(ADDED_HEADERS)))
    width = len(sheet.headers)
    for (number, pairs), result in zip(sheet.data, results):
        values = [safe(value) for value, _ in pairs][:width]
        values += [None] * (width - len(values))
        plates.append(values + [safe(item) for item in result.report_cells()])
    facts = workbook.create_sheet("Batch")
    facts.append(header_cells(facts, ["Item", "Value"]))
    for label, value in batch_facts:
        facts.append([label, safe(value)])
    workbook.save(target)


def write_problem_list(target, checked):
    """Every skipped row, warning, duplicate code and renamed file of a check, for the "rows to check" download."""
    workbook = openpyxl.Workbook(write_only=True)
    sheet = workbook.create_sheet("Rows to check")
    sheet.append(header_cells(sheet, ["Row", "Status", "Reason"]))
    for result in checked.results:
        if not result.made:
            sheet.append([result.number, "skipped", safe(result.reason)])
            continue
        notes = result.warnings + result.notes + (["File name " + result.file_name] if result.renamed else [])
        if notes:
            sheet.append([result.number, "made", safe("; ".join(notes))])
    workbook.save(target)
