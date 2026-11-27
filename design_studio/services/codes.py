"""DIGIPIN and plus code checks, and the DIGIPIN encoder (same grid as static/js/digipin.js)."""

import re

DIGIPIN_GRID = (
    ("F", "C", "9", "8"),
    ("J", "3", "2", "7"),
    ("K", "4", "5", "6"),
    ("L", "M", "P", "T"),
)
DIGIPIN_CHARS = frozenset("".join("".join(row) for row in DIGIPIN_GRID))
MIN_LAT, MAX_LAT, MIN_LONG, MAX_LONG = 2.5, 38.5, 63.5, 99.5
PLUSCODE_CHARS = "23456789CFGHJMPQRVWX"
PLUSCODE_PATTERN = re.compile(r"^[{0}]{{8}}\+[{0}]{{2,4}}$".format(PLUSCODE_CHARS))


class CodeError(ValueError):
    pass


def clean_digipin(value):
    """10-character DIGIPIN without spaces or hyphens, upper case."""
    code = re.sub(r"[\s\-]", "", str(value or "")).upper()
    if len(code) != 10 or not set(code) <= DIGIPIN_CHARS:
        raise CodeError('Invalid DIGIPIN "{}"'.format(str(value or "").strip()[:30]))
    return code


def display_digipin(code):
    return "{} {} {}".format(code[:3], code[3:7], code[7:])


def clean_pluscode(value):
    """Full plus code: 8 characters, '+', 2 to 4 characters. Localities and short codes are refused."""
    code = str(value or "").strip().upper()
    if not PLUSCODE_PATTERN.match(code):
        raise CodeError('Invalid plus code "{}"'.format(str(value or "").strip()[:30]))
    return code


def in_india(lat, long):
    return MIN_LAT <= lat <= MAX_LAT and MIN_LONG <= long <= MAX_LONG


def encode_digipin(lat, long):
    """The DIGIPIN of a point inside the India bounding box."""
    if not in_india(lat, long):
        raise CodeError("Latitude/Longitude outside India")
    min_lat, max_lat, min_long, max_long = MIN_LAT, MAX_LAT, MIN_LONG, MAX_LONG
    code = ""
    for level in range(10):
        lat_div = (max_lat - min_lat) / 4
        long_div = (max_long - min_long) / 4
        row = min(max(3 - int((lat - min_lat) // lat_div), 0), 3)
        col = min(max(int((long - min_long) // long_div), 0), 3)
        code += DIGIPIN_GRID[row][col]
        max_lat = min_lat + lat_div * (4 - row)
        min_lat = min_lat + lat_div * (3 - row)
        min_long = min_long + long_div * col
        max_long = min_long + long_div
    return code


def decode_digipin(code):
    """Centre (lat, long) of a DIGIPIN cell."""
    code = clean_digipin(code)
    min_lat, max_lat, min_long, max_long = MIN_LAT, MAX_LAT, MIN_LONG, MAX_LONG
    for char in code:
        row = next(index for index, cells in enumerate(DIGIPIN_GRID) if char in cells)
        col = DIGIPIN_GRID[row].index(char)
        lat_div = (max_lat - min_lat) / 4
        long_div = (max_long - min_long) / 4
        max_lat = min_lat + lat_div * (4 - row)
        min_lat = min_lat + lat_div * (3 - row)
        min_long = min_long + long_div * col
        max_long = min_long + long_div
    return (min_lat + max_lat) / 2, (min_long + max_long) / 2
