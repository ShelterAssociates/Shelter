"""Small shared helpers for the photos app."""

import datetime


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


def financial_year_range(start_year):
    """Indian financial year: 1 April <start_year> to 31 March <start_year+1>."""
    start_year = int(start_year)
    return (
        datetime.date(start_year, 4, 1),
        datetime.date(start_year + 1, 3, 31),
    )


def financial_year_label(start_year):
    return "{}-{}".format(start_year, str(int(start_year) + 1)[-2:])


def financial_year_choices(back=8):
    """Recent financial years, newest first, for the filter dropdown."""
    today = datetime.date.today()
    # A financial year starts in April, so before April we're still in the
    # previous one.
    current = today.year if today.month >= 4 else today.year - 1
    return [
        (year, financial_year_label(year))
        for year in range(current, current - back, -1)
    ]
