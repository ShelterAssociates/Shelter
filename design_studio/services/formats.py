"""The blank "Excel format" workbooks offered for download (same layout as the hand-off files)."""

import io

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from design_studio.services import rows

FORMAT_ROWS = 15000
WIDTHS = {"A": 12, "B": 18, "C": 14, "D": 14, "E": 34, "F": 10, "G": 16}
TITLES = {"digipin": "DIGIPIN plates: Excel format", "pluscode": "Plus Code plates: Excel format"}
EXAMPLES = {
    "digipin": [["1", "4J6M8286K8", 16.6929355, 74.45952441, "Nimajga Mal", "9", "Ichalkaranji"],
                ["2", "4J6M8286K9", 16.69301, 74.45961, "Nimajga Mal", "9", "Ichalkaranji"]],
    "pluscode": [["1", "7J8PMFV5+5RCH", 16.6929355, 74.45952441, "Nimajga Mal", "9", "Ichalkaranji"],
                 ["2", "7J8PMFV5+6RCH", 16.69301, 74.45961, "Nimajga Mal", "9", "Ichalkaranji"]],
}
CODE_HELP = {
    "digipin": "DIGIPIN (required): 10 characters, e.g. 4J6M8286K8. Spaces and hyphens are removed, so 372-8F3-7K28 is fine.",
    "pluscode": "Plus Code (required): full code: 8 characters, '+', then 2 to 4 characters, e.g. 7J8PMFV5+5RCH. "
                "Short codes with a place name are not accepted.",
}
COORDINATE_FORMAT = "0.0000000"


def instructions(plate_type):
    """(row number, text, is title) for the Instructions sheet."""
    return [
        (1, TITLES[plate_type], True),
        (3, "Fill in the 'Plates' sheet, one row per plate. Keep the header row exactly as it is.", False),
        (4, "Dark purple columns are required. Light purple columns are optional. You may add your own extra columns "
            "at the end; they are copied into the result unchanged.", False),
        (6, "House No (required): text, up to {} characters, e.g. 1, 12A, 0045. Used in the image file name.".format(rows.MAX_HOUSE_NO), False),
        (7, CODE_HELP[plate_type], False),
        (8, "Latitude, Longitude (required): decimal degrees inside India, e.g. 16.6929355 and 74.45952441. Used for the QR link.", False),
        (9, "Slum Name (required): printed on the plate under the code, up to 80 characters, no < or >.", False),
        (10, "Ward, City (optional): kept in the result file; City is used in the download name.", False),
        (12, "Up to 15,000 rows per file. Save as Excel Workbook (.xlsx). No formulas or macros.", False),
        (13, "Rows with a problem are skipped and listed with the reason; all other rows still become plates.", False),
    ]


def header_style(cell, required):
    cell.font = Font(bold=True, color="FFFFFF") if required else Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="2A2468" if required else "CDC8F0")
    cell.alignment = Alignment(horizontal="center")


def validations(sheet):
    last = FORMAT_ROWS + 1
    rules = (
        ("decimal", "between", "2.5", "38.5", "C2:C{}".format(last), "Latitude must be between 2.5 and 38.5 (India).", "Latitude"),
        ("decimal", "between", "63.5", "99.5", "D2:D{}".format(last), "Longitude must be between 63.5 and 99.5 (India).", "Longitude"),
        ("textLength", "lessThanOrEqual", "80", None, "E2:E{}".format(last), "Slum name can be at most 80 characters.", "Slum Name"),
    )
    for kind, operator, first, second, cells, message, title in rules:
        rule = DataValidation(type=kind, operator=operator, formula1=first, formula2=second, error=message, errorTitle=title,
                              showErrorMessage=False, allow_blank=False)
        rule.add(cells)
        sheet.add_data_validation(rule)


def plates_sheet(sheet, plate_type):
    sheet.title = "Plates"
    for column, (_, header, required) in enumerate(rows.columns(plate_type), start=1):
        header_style(sheet.cell(row=1, column=column, value=header), required)
    for number in range(2, FORMAT_ROWS + 2):
        for column in range(1, 8):
            sheet.cell(row=number, column=column).number_format = COORDINATE_FORMAT if column in (3, 4) else "@"
    for number, values in enumerate(EXAMPLES[plate_type], start=2):
        for column, value in enumerate(values, start=1):
            sheet.cell(row=number, column=column, value=value)
    for letter, width in WIDTHS.items():
        sheet.column_dimensions[letter].width = width
    sheet.freeze_panes = "A2"
    validations(sheet)


def workbook_bytes(plate_type):
    workbook = openpyxl.Workbook()
    plates_sheet(workbook.active, plate_type)
    guide = workbook.create_sheet("Instructions")
    guide.column_dimensions["A"].width = 120
    for number, text, is_title in instructions(plate_type):
        guide.cell(row=number, column=1, value=text).font = Font(bold=True, size=13) if is_title else Font(size=11)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def file_name(plate_type):
    return "excel_format_{}.xlsx".format(plate_type)
