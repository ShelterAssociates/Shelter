"""Small shared helpers for the photos app."""

# Re-exported: the financial year is shared with the map filters.
from helpers.financial_year import (  # noqa: F401
    financial_year_choices,
    financial_year_label,
    financial_year_range,
)


def normalize_household_number(value):
    """Match mastersheet.views.normalize_household_number so lookups here agree
    with how household numbers are keyed everywhere else.

    Household numbers can be alphanumeric ('0749A'), so strip leading zeros
    string-safely rather than casting to int.
    """
    if value is None:
        return None
    stripped = str(value).strip().lstrip("0")
    return stripped if stripped else "0"


def household_number_variants(lookup_number, max_width=6):
    """Every zero-padded spelling of a household number.

    HouseholdData stores these inconsistently ('22', '022', '0022' all occur),
    so matching needs all the variants rather than a Python-side scan.
    """
    if not lookup_number:
        return set()
    variants = {lookup_number}
    for width in range(len(lookup_number) + 1, max_width + 1):
        variants.add(lookup_number.rjust(width, "0"))
    return variants
