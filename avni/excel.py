"""Reading spreadsheets uploaded by the team.

openpyxl rather than pandas+xlrd: the pinned xlrd 0.9.3 fails on blank string
cells, which hand-edited files always contain.
"""

from openpyxl import load_workbook


def read_rows(file_path):
    """(headers, rows) of the first sheet; rows are dicts keyed by header, blanks kept as None."""
    sheet = load_workbook(file_path, read_only=True, data_only=True).active
    lines = sheet.iter_rows(values_only=True)
    try:
        first = next(lines)
    except StopIteration:
        return [], []
    headers = [clean_header(value) for value in first]
    rows = []
    for line in lines:
        values = list(line) + [None] * (len(headers) - len(line))
        row = {header: clean_cell(values[index]) for index, header in enumerate(headers) if header}
        if any(value is not None for value in row.values()):
            rows.append(row)
    return [header for header in headers if header], rows


def read_column(file_path, column):
    """Non-blank values of one column, as strings."""
    headers, rows = read_rows(file_path)
    if column not in headers:
        raise KeyError("Column '{}' not found; headers are {}".format(column, ", ".join(headers)))
    return [str(row[column]) for row in rows if row.get(column) is not None]


def clean_header(value):
    return str(value).strip() if value is not None else ""


def clean_cell(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value
