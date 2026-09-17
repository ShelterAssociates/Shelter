"""How a household number is spelled, whatever tool collected it."""

import re

LEADING_ZEROS = re.compile(r"^0*(\d+)([A-Za-z].*)$")


def household_number_from(value):
    """'0042' -> '42', '0022A' -> '22A', 42.0 -> '42'. Blank stays blank."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if text.isdigit():
        return str(int(text))
    match = LEADING_ZEROS.match(text)
    return match.group(1) + match.group(2) if match else text
