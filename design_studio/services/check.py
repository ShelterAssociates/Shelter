"""The check step: every row validated, fitted, named and linked exactly as the batch run will make it."""

from collections import OrderedDict

from design_studio.services import excel, naming, rows
from design_studio.services.textfit import TextDoesNotFit

MAX_DEMOS = 3


class RowResult(object):
    def __init__(self, number):
        self.number = number
        self.row = None
        self.reason = ""
        self.warnings = []
        self.notes = []
        self.file_name = ""
        self.renamed = False
        self.link = ""
        self.code_text = ""

    @property
    def made(self):
        return self.row is not None

    def report_cells(self):
        """Image file name | Status | Reason | Code on plate | QR link, for plates.xlsx."""
        if not self.made:
            return ["", "skipped", self.reason, "", ""]
        return ["images/" + self.file_name, "made", "; ".join(self.warnings + self.notes), self.code_text, self.link]


class CheckResult(object):
    def __init__(self, sheet, plate_type, results):
        self.sheet = sheet
        self.plate_type = plate_type
        self.results = results
        self.made = [result for result in results if result.made]
        self.skipped = [result for result in results if not result.made]
        self.warned = [result for result in self.made if result.warnings]
        self.duplicate_codes = duplicate_codes(self.made, plate_type)
        self.renamed = [result for result in self.made if result.renamed]

    @property
    def total(self):
        return len(self.results)

    def first_value(self, key):
        return next((result.row[key] for result in self.made if result.row.get(key)), "")

    def demos(self, renderer):
        """First valid row, widest code, longest slum name; at most 3, no repeats."""
        if not self.made:
            return []
        picks = [self.made[0], max(self.made, key=lambda result: renderer.code_width(result.row)),
                 max(self.made, key=lambda result: len(result.row["slum"]))]
        unique = OrderedDict((result.number, result) for result in picks)
        return list(unique.values())[:MAX_DEMOS]


def duplicate_codes(made, plate_type):
    """{code: [row numbers]} for codes on more than one row; each row also gets a note."""
    seen = OrderedDict()
    for result in made:
        seen.setdefault(rows.plate_code(result.row, plate_type), []).append(result)
    found = OrderedDict()
    label = rows.CODE_HEADERS[plate_type]
    for code, results in seen.items():
        if len(results) > 1:
            found[code] = [result.number for result in results]
            for result in results:
                others = ", ".join(str(other.number) for other in results if other is not result)
                result.notes.append("Same {} as row {}".format(label, others))
    return found


def check_row(number, pairs, positions, plate_type, renderer, names):
    result = RowResult(number)
    values, formulas = excel.row_values(pairs, positions)
    try:
        row, warnings = rows.clean_row(values, plate_type, formulas)
        renderer.check(row)
    except (rows.RowError, TextDoesNotFit) as exc:
        result.reason = str(exc)
        return result
    base = naming.design_base_name(rows.plate_code(row, plate_type), row["house_no"])
    result.row, result.warnings = row, warnings
    result.file_name = names.take(base)
    result.renamed = result.file_name.lower() != (base + ".png").lower()
    result.link = renderer.link(row)
    result.code_text = rows.code_on_plate(row, plate_type)
    return result


def check_sheet(sheet, plate_type, renderer):
    """CheckResult for a sheet; UploadError when required columns are missing (before any row is read)."""
    positions = excel.column_positions(sheet.headers, plate_type)
    names = naming.UniqueNames()
    results = [check_row(number, pairs, positions, plate_type, renderer, names) for number, pairs in sheet.data]
    return CheckResult(sheet, plate_type, results)
