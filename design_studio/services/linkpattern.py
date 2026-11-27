"""QR link patterns: the variables a pattern may use, filling them per row, and the checks before saving."""

import re
from urllib.parse import quote, urlsplit

import qrcode
from django.conf import settings
from qrcode.exceptions import DataOverflowError

VARIABLES = ("house_no", "digipin", "digipin_display", "pluscode", "lat", "long", "slum", "ward", "city")
STARTING_PATTERNS = (
    ("DIGIPIN, India Post page", "https://dac.indiapost.gov.in/mydigipin/home/{digipin}"),
    ("Google Maps from coordinates", "https://www.google.com/maps/place/{lat},{long}"),
    ("Google Maps search by plus code", "https://www.google.com/maps/search/?api=1&query={pluscode}"),
)
DEFAULT_PATTERNS = {"digipin": STARTING_PATTERNS[0][1], "pluscode": STARTING_PATTERNS[1][1]}
# Longest value each variable can hold after the row checks; slum names may be non-ASCII (9 bytes encoded).
WORST_CASE = {
    "house_no": "W" * 5,
    "digipin": "M" * 10,
    "digipin_display": "MMM MMMM MMM",
    "pluscode": "WWWWWWWW+WWWW",
    "lat": "-38.12345678901234",
    "long": "-99.12345678901234",
    "slum": "न" * 80,
    "ward": "न" * 40,
    "city": "न" * 40,
}
PLACEHOLDER = re.compile(r"\{([^{}]*)\}")


def fill(pattern, row):
    """The link for one row; every value URL-encoded, so + becomes %2B."""
    return PLACEHOLDER.sub(lambda match: quote(str(row.get(match.group(1), "") or ""), safe=""), pattern)


MISSING_BY_TYPE = {"digipin": ("pluscode",), "pluscode": ("digipin", "digipin_display")}


def problems(pattern, plate_type=None):
    """Plain-language reasons the pattern cannot be saved; empty when it is fine."""
    pattern = (pattern or "").strip()
    if not pattern.startswith("https://"):
        return ["The QR link must start with https://."]
    found = []
    host = urlsplit(PLACEHOLDER.sub("x", pattern)).hostname or ""
    allowed = getattr(settings, "DESIGN_STUDIO_QR_ALLOWED_HOSTS", [])
    if host not in allowed:
        found.append("The QR link may only point to {} (not {}).".format(", ".join(allowed), host or "an empty host"))
    unknown = [name for name in PLACEHOLDER.findall(pattern) if name not in VARIABLES]
    if unknown:
        found.append("Unknown variable {}. Use only {}.".format(
            ", ".join("{%s}" % name for name in unknown), ", ".join("{%s}" % name for name in VARIABLES)))
    empty = [name for name in PLACEHOLDER.findall(pattern) if name in MISSING_BY_TYPE.get(plate_type, ())]
    if empty:
        found.append("{} plates have no {}, so that part of the link would be empty.".format(
            "DIGIPIN" if plate_type == "digipin" else "Plus Code", ", ".join("{%s}" % name for name in empty)))
    if "{" in PLACEHOLDER.sub("", pattern) or "}" in PLACEHOLDER.sub("", pattern):
        found.append("The QR link has a { or } that is not part of a variable.")
    if not found and worst_case_version(pattern) is None:
        found.append("The longest possible link would not fit in a QR code.")
    return found


def worst_case_version(pattern):
    """QR version (1-40) of the longest link this pattern can make at error correction M, or None."""
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    code.add_data(fill(pattern, WORST_CASE))
    try:
        code.make(fit=True)
    except DataOverflowError:
        return None
    return code.version
