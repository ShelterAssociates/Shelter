"""Shared test data: the seeded presets, sample rows and the bundled fonts and logos."""

import copy
import json
import os

from django.conf import settings

from design_studio.services.codes import display_digipin
from design_studio.services.resources import Resources

PRESET_DIR = os.path.join(settings.BASE_DIR, "design_studio", "fixtures", "presets")
RESOURCES = Resources.bundled()
SLUM_60 = "Ambedkar Nagar Wasti Phase Two Extension Near Railway Line 2"


def preset(plate_type, **changes):
    with open(os.path.join(PRESET_DIR, "{}_plate.json".format(plate_type))) as handle:
        spec = json.load(handle)
    spec.update(copy.deepcopy(changes))
    return spec


def row(plate_type="digipin", **changes):
    values = {"house_no": "1", "slum": "Nimajga Mal", "ward": "9", "city": "Ichalkaranji", "lat": "16.6929355", "long": "74.45952441"}
    if plate_type == "digipin":
        values.update(digipin="4J6M8286K8", digipin_display=display_digipin("4J6M8286K8"))
    else:
        values.update(pluscode="7J8PMFV5+5RCH")
    values.update(changes)
    return values


def worst_row(plate_type, **changes):
    if plate_type == "digipin":
        values = row("digipin", digipin="MMMMMMMMMM", digipin_display="MMM MMMM MMM", slum=SLUM_60, house_no="W" * 5)
    else:
        values = row("pluscode", pluscode="WWWWWWWW+WWWW", slum=SLUM_60, house_no="W" * 5)
    values.update(changes)
    return values


HEADERS = {
    "digipin": ["House No", "DIGIPIN", "Latitude", "Longitude", "Slum Name", "Ward", "City"],
    "pluscode": ["House No", "Plus Code", "Latitude", "Longitude", "Slum Name", "Ward", "City"],
}
# samples/sample_input_digipin.xlsx from the hand-off pack: (row values, expected outcome).
SAMPLE_ROWS = [
    (["1", "4J6M8286K8", 16.6929355, 74.45952441, "Nimajga Mal", "9", "Ichalkaranji"], ("made", "4J6M8286K8_1.png")),
    (["2", "372-8F3-7K28", 16.69301, 74.45961, "Nimajga Mal", "9", "Ichalkaranji"], ("made", "3728F37K28_2.png")),
    (["3", "MMMMMMMMMM", 16.6931, 74.4597, "Ambedkar Nagar Wasti Phase Two Extension Near Railway Line", "9", None], ("made", "MMMMMMMMMM_3.png")),
    (["4", "BAD-123", 16.6932, 74.4598, "Nimajga Mal", "9", None], ("skipped", 'Invalid DIGIPIN "BAD-123"')),
    ([12, "4j6 m828 6k8", 16.6933, 74.4599, "Nimajga Mal", "9", None], ("made", "4J6M8286K8_12.png")),
    (["1", "4J6M8286K8", 16.6929355, 74.45952441, "Nimajga Mal", "9", None], ("made", "4J6M8286K8_1_2.png")),
    (["7", "4J6M8286K9", 16.6934, 74.46, '=HYPERLINK("http://example.com","x")', "9", None],
     ("skipped", "Slum Name contains a formula; type the value instead")),
    (["8", "4J6M8286KC", 16.6935, 74.4601, "Nimajga <b>Mal</b>", "9", None], ("skipped", "Slum Name contains < or >")),
    ([None, "4J6M8286KF", 16.6936, 74.4602, "Nimajga Mal", "9", None], ("skipped", "House number missing")),
    (["10", "4J6M8286KJ", None, None, "Nimajga Mal", "9", None], ("skipped", "Latitude/Longitude missing")),
    (["11", "4J6M8286KL", 51.5, 0.12, "Nimajga Mal", "9", None], ("skipped", "Latitude/Longitude outside India")),
    (["12", "4J6M8286KM", 16.6937, 74.4603, None, "9", None], ("skipped", "Slum Name missing")),
]


def workbook_bytes(headers, data, sheet_title="Plates", leading_blank_rows=0, extra_sheets=()):
    import io

    import openpyxl

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = sheet_title
    for _ in range(leading_blank_rows):
        sheet.append([None])
    sheet.append(headers)
    for values in data:
        sheet.append(values)
    for title in extra_sheets:
        workbook.create_sheet(title).append(["anything"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def sample_workbook():
    headers = HEADERS["digipin"] + ["Expected (testing only)"]
    return workbook_bytes(headers, [values + ["{}: {}".format(*expected)] for values, expected in SAMPLE_ROWS])


def good_rows(count, plate_type="digipin"):
    rows = []
    for number in range(1, count + 1):
        code = "4J6M8286K8" if plate_type == "digipin" else "7J8PMFV5+5RCH"
        rows.append([str(number), code, 16.6929355, 74.45952441, "Nimajga Mal", "9", "Ichalkaranji"])
    return rows
