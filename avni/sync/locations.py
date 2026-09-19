"""Map AVNI slum locations onto master.Slum by name + city, as survey.SlumAlias rows.

`manage.py match_avni_locations` prints the plan; `--apply` writes. Only an
exact (slum name, city name) match creates an alias; everything else is
listed for a human: unmatched on either side, ambiguous names, and slums
already aliased to another uuid.
"""

import logging
from collections import Counter, defaultdict

from avni import paths
from avni.client import client
from avni.locations import PROVIDER
from master.models import Slum
from survey.models import SlumAlias

logger = logging.getLogger(__name__)

SLUM_TYPE = "Slum"
CITY_TYPE = "City"
LOCATIONS_SINCE = "1900-01-01T00:00:00.000Z"


def key(name, city):
    return ((name or "").strip().casefold(), (city or "").strip().casefold())


def city_of(location):
    """Title of the City ancestor, walking the nested Parent chain."""
    parent = location.get("Parent")
    while parent:
        if parent.get("Type") == CITY_TYPE:
            return parent.get("Title")
        parent = parent.get("Parent")
    return None


def fetch_slums(api):
    """[(uuid, title, city title)] for every live Slum location in AVNI."""
    slums = []
    for page in api.iter_pages(paths.locations(LOCATIONS_SINCE)):
        for location in page:
            if location.get("Type") == SLUM_TYPE and not location.get("Voided"):
                slums.append((location["ID"], location.get("Title") or "", city_of(location)))
    return slums


def db_slums():
    """{(name, city) key: [(slum id, name, city)]} for every Slum, keyed like AVNI titles."""
    rows = Slum.objects.values_list("id", "name", "electoral_ward__administrative_ward__city__name__city_name")
    by_key = defaultdict(list)
    for slum_id, name, city in rows:
        by_key[key(name, city)].append((slum_id, name, city))
    return by_key


def plan(api):
    """(creates, report) — creates = [(slum id, uuid, title)], report = {kind: [lines]}."""
    aliases = dict(SlumAlias.objects.filter(provider=PROVIDER).values_list("slum_id", "external_id"))
    slum_by_uuid = {uuid: slum_id for slum_id, uuid in aliases.items()}
    by_key = db_slums()
    cities_by_name = defaultdict(set)
    for (name, _), rows in by_key.items():
        cities_by_name[name].update(city for _, _, city in rows)

    creates, report = [], defaultdict(list)
    matched_ids = set()
    for uuid, title, city in fetch_slums(api):
        if uuid in slum_by_uuid:
            matched_ids.add(slum_by_uuid[uuid])
            continue
        rows = by_key.get(key(title, city), [])
        if len(rows) > 1:
            report["ambiguous"].append("%s (%s) matches slums %s" % (title, city, [r[0] for r in rows]))
        elif rows:
            slum_id = rows[0][0]
            matched_ids.add(slum_id)
            if slum_id in aliases:
                report["conflict"].append("%s (%s) is slum %s, already aliased to %s" % (title, city, slum_id, aliases[slum_id]))
            else:
                creates.append((slum_id, uuid, title))
        else:
            cities = sorted(c or "?" for c in cities_by_name.get(key(title, None)[0], ()))
            hint = " (same name in DB under %s)" % ", ".join(cities) if cities else ""
            report["unmatched_avni"].append("%s (%s) %s%s" % (title, city, uuid, hint))
    for rows in by_key.values():
        for slum_id, name, city in rows:
            if slum_id not in matched_ids and slum_id not in aliases:
                report["unmatched_db"].append("slum %s %s (%s)" % (slum_id, name, city))
    report["unmatched_db"].sort()
    return creates, report


def run(apply=False, api=None, out=print):
    """Print the plan (and with apply=True write the aliases). Returns counts."""
    creates, report = plan(api or client())
    for slum_id, uuid, title in creates:
        out("CREATE slum %s <- %s (%s)" % (slum_id, uuid, title))
    for kind in ("conflict", "ambiguous", "unmatched_avni", "unmatched_db"):
        for line in report[kind]:
            out("%-14s %s" % (kind.upper(), line))
    if apply:
        SlumAlias.objects.bulk_create([
            SlumAlias(slum_id=slum_id, provider=PROVIDER, external_id=uuid, external_name=title)
            for slum_id, uuid, title in creates
        ])
    counts = Counter({kind: len(lines) for kind, lines in report.items()})
    counts["created" if apply else "to_create"] = len(creates)
    out(", ".join("%s %s" % (n, kind) for kind, n in sorted(counts.items())))
    return counts
