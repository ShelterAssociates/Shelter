"""The fixed Excel columns, and the checks every row (Excel or single-plate form) must pass."""

from plates.services import codes

CODE_HEADERS = {"digipin": "DIGIPIN", "pluscode": "Plus Code"}
MAX_HOUSE_NO = 5
MAX_SLUM = 80
MAX_OPTIONAL = 40


class RowError(ValueError):
    pass


def columns(plate_type):
    """(key, header, required) in the fixed order of the Excel format."""
    return (
        ("house_no", "House No", True),
        ("code", CODE_HEADERS[plate_type], True),
        ("lat", "Latitude", True),
        ("long", "Longitude", True),
        ("slum", "Slum Name", True),
        ("ward", "Ward", False),
        ("city", "City", False),
    )


def header_list(plate_type, required=None):
    return [header for _, header, is_required in columns(plate_type) if required is None or is_required == required]


def text_value(value):
    """Cell value as trimmed text; 12.0 becomes 12."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def coordinate(value, label):
    text = text_value(value)
    if not text:
        raise RowError("Latitude/Longitude missing")
    try:
        number = float(text)
    except ValueError:
        raise RowError("{} is not a number".format(label))
    if number != number or number in (float("inf"), float("-inf")):
        raise RowError("{} is not a number".format(label))
    return number


def plain_text(value, label, limit, required):
    text = text_value(value)
    if required and not text:
        raise RowError("{} missing".format(label))
    if "<" in text or ">" in text:
        raise RowError("{} contains < or >".format(label))
    if len(text) > limit:
        raise RowError("{} longer than {} characters".format(label, limit))
    return text


def number_text(number):
    return str(int(number)) if number.is_integer() else repr(number)


def code_values(plate_type, raw):
    if plate_type == "digipin":
        if not text_value(raw):
            raise RowError("DIGIPIN missing")
        digipin = codes.clean_digipin(raw)
        return {"digipin": digipin, "digipin_display": codes.display_digipin(digipin), "pluscode": ""}
    if not text_value(raw):
        raise RowError("Plus code missing")
    return {"digipin": "", "digipin_display": "", "pluscode": codes.clean_pluscode(raw)}


def clean_row(values, plate_type, formulas=()):
    """(row variables, warnings) for one row, or RowError with the reason it is skipped.

    values: {key: raw cell value}; formulas: keys whose cell holds a formula.
    """
    for key, header, required in columns(plate_type):
        if key in formulas and required:
            raise RowError("{} contains a formula; type the value instead".format(header))
    house_no = plain_text(values.get("house_no"), "House number", MAX_HOUSE_NO, True)
    try:
        row = code_values(plate_type, values.get("code"))
    except codes.CodeError as exc:
        raise RowError(str(exc))
    lat, long = coordinate(values.get("lat"), "Latitude"), coordinate(values.get("long"), "Longitude")
    if not codes.in_india(lat, long):
        raise RowError("Latitude/Longitude outside India")
    row.update(
        house_no=house_no, lat=number_text(lat), long=number_text(long),
        slum=plain_text(values.get("slum"), "Slum Name", MAX_SLUM, True),
        ward=plain_text(values.get("ward"), "Ward", MAX_OPTIONAL, False),
        city=plain_text(values.get("city"), "City", MAX_OPTIONAL, False),
    )
    return row, row_warnings(plate_type, row, lat, long)


def row_warnings(plate_type, row, lat, long):
    if plate_type != "digipin":
        return []
    computed = codes.encode_digipin(lat, long)
    if computed == row["digipin"]:
        return []
    return ["DIGIPIN does not match Latitude/Longitude (computed: {})".format(codes.display_digipin(computed))]


def code_on_plate(row, plate_type):
    return row["digipin_display"] if plate_type == "digipin" else row["pluscode"]


def plate_code(row, plate_type):
    return row["digipin"] if plate_type == "digipin" else row["pluscode"]
