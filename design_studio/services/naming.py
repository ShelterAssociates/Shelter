"""Safe, unique file names for plates inside a zip."""

import re

MAX_LENGTH = 120
UNSAFE = re.compile(r'[/\\:*?"<>|\x00-\x1f\x7f]')


def clean(text, fallback="plate"):
    """Trim, replace unsafe characters with -, collapse -, no '..', never start with - or '.', max 120 chars."""
    name = UNSAFE.sub("-", str(text or "").strip())
    name = re.sub(r"-{2,}", "-", name)
    name = re.sub(r"\.{2,}", ".", name)
    name = name[:MAX_LENGTH].lstrip("-.").rstrip()
    return name or fallback


def design_base_name(code, house_no):
    """4J6M8286K8_1 (DIGIPIN without spaces) or 7J8PMFV5+5RCH_1."""
    return clean("{}_{}".format(code.replace(" ", ""), house_no))


class UniqueNames(object):
    """Hands out names once per zip; repeats get _2, _3."""

    def __init__(self):
        self.taken = set()

    def take(self, base, extension=".png"):
        name = base + extension
        number = 1
        while name.lower() in self.taken:
            number += 1
            name = "{}_{}{}".format(base, number, extension)
        self.taken.add(name.lower())
        return name


def zip_name(slum, plate_type, when):
    """<date>_<time>_<digipin|pluscode>_<slum>.zip, e.g. 2026-11-27_1530_digipin_kasba-peth.zip; lower case, spaces as hyphens."""
    stem = clean(slum, "batch").lower().replace(" ", "-")
    return "{}_{}_{}.zip".format(when.strftime("%Y-%m-%d_%H%M"), plate_type, stem)
