"""The Indian financial year (1 April - 31 March), shared by the photo exports and the map filters."""

import datetime


def financial_year_range(start_year):
    """Indian financial year: 1 April <start_year> to 31 March <start_year+1>."""
    start_year = int(start_year)
    return (
        datetime.date(start_year, 4, 1),
        datetime.date(start_year + 1, 3, 31),
    )


def financial_year_label(start_year):
    return "{}-{}".format(start_year, str(int(start_year) + 1)[-2:])


def current_financial_year(today=None):
    """The start year of the financial year we are in."""
    today = today or datetime.date.today()
    # A financial year starts in April, so before April we're still in the previous one.
    return today.year if today.month >= 4 else today.year - 1


def financial_year_choices(back=8):
    """Recent financial years, newest first, for the filter dropdown."""
    current = current_financial_year()
    return [
        (year, financial_year_label(year))
        for year in range(current, current - back, -1)
    ]
