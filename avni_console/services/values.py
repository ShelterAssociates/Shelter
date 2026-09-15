"""Turn a spreadsheet cell into the value AVNI expects for a question."""

import re
from datetime import date, datetime

import dateparser
from django.utils import timezone

NO_CHANGE = object()   # blank cell: leave the observation alone
CLEAR = object()       # the literal __CLEAR__: remove the observation
CLEAR_TOKEN = "__clear__"

TRUE_WORDS = {"yes", "true", "1", "y"}
FALSE_WORDS = {"no", "false", "0", "n"}
DATE_SETTINGS = {"DATE_ORDER": "DMY", "RETURN_AS_TIMEZONE_AWARE": False}
TEXT_TYPES = {"Text", "Notes", "Id"}
ISO_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")


class CellError(ValueError):
    pass


def coerce(cell, question):
    """Value for `question` from `cell`, NO_CHANGE for blanks, CLEAR for the clear token."""
    special = blank_or_clear(cell)
    if special is not None:
        return special
    data_type = question.data_type
    if data_type == "Numeric":
        return number(cell)
    if data_type in TEXT_TYPES:
        return text(cell)
    if data_type == "Coded":
        return coded(cell, question.answers or [], question.is_multi_select)
    if data_type == "Date":
        return iso_date(cell)
    if data_type == "DateTime":
        return iso_datetime(cell)
    raise CellError("{} values cannot be set from a spreadsheet".format(data_type))


def coerce_reserved(field, cell):
    """Top-level fields: Voided, First name, Registration date, Encounter date time, ..."""
    special = blank_or_clear(cell)
    if special is not None:
        return special
    if field == "Voided":
        return boolean(cell)
    if field in ("First name", "Last name"):
        return text(cell)
    if field == "Registration date":
        return iso_date(cell)
    return iso_datetime(cell)


def blank_or_clear(cell):
    if cell is None:
        return NO_CHANGE
    if isinstance(cell, str):
        stripped = cell.strip()
        if not stripped:
            return NO_CHANGE
        if stripped.casefold() == CLEAR_TOKEN:
            return CLEAR
    return None


def number(cell):
    if isinstance(cell, bool):
        raise CellError("'{}' is not a number".format(cell))
    if isinstance(cell, (int, float)):
        return int(cell) if float(cell).is_integer() else cell
    try:
        return int(str(cell).strip())
    except ValueError:
        pass
    try:
        return float(str(cell).strip())
    except ValueError:
        raise CellError("'{}' is not a number".format(cell))


def text(cell):
    return str(cell).strip()


def boolean(cell):
    word = str(cell).strip().casefold()
    if word in TRUE_WORDS:
        return True
    if word in FALSE_WORDS:
        return False
    raise CellError("'{}' is not yes/no".format(cell))


def coded(cell, answers, multi):
    canonical = {answer.casefold(): answer for answer in answers}
    if multi:
        return [match_answer(part, canonical, answers) for part in split_answers(cell, canonical)]
    return match_answer(cell, canonical, answers)


def match_answer(cell, canonical, answers):
    key = str(cell).strip().casefold()
    if key not in canonical:
        raise CellError("'{}' is not one of the allowed answers: {}".format(cell, ", ".join(answers)))
    return canonical[key]


def split_answers(cell, canonical):
    if isinstance(cell, (list, tuple)):
        return [str(part) for part in cell]
    whole = str(cell).strip()
    if whole.casefold() in canonical:
        return [whole]
    separator = ";" if ";" in whole else ","
    return [part for part in (piece.strip() for piece in whole.split(separator)) if part]


def parse_moment(cell):
    if isinstance(cell, datetime):
        return cell
    if isinstance(cell, date):
        return datetime(cell.year, cell.month, cell.day)
    raw = str(cell).strip()
    if ISO_PREFIX.match(raw):
        parsed = dateparser.parse(raw, settings={"DATE_ORDER": "YMD", "RETURN_AS_TIMEZONE_AWARE": False})
    else:
        parsed = dateparser.parse(raw, settings=DATE_SETTINGS)
    if parsed is None:
        raise CellError("'{}' is not a date".format(cell))
    return parsed


def iso_date(cell):
    return parse_moment(cell).strftime("%Y-%m-%d")


def iso_datetime(cell):
    """Naive values are read as local (Asia/Kolkata) time and sent as UTC, AVNI style."""
    moment = parse_moment(cell)
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
