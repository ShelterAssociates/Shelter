"""Repair HouseholdData rows AVNI no longer agrees with.

HouseholdData is keyed by household number while AVNI is keyed by subject uuid,
so before the sync learnt to reconcile the two (households.retire_stale_rows /
remove_voided_household) every renumber, slum move or void in AVNI left a ghost
row behind. `manage.py reconcile_households` prints the plan; `--apply` runs it.
"""

import logging
from collections import Counter, defaultdict

from avni.client import AvniError, client
from avni.locations import slum_and_city_ids
from avni.sync import households
from graphs.models import HouseholdData

logger = logging.getLogger(__name__)

FF_NUMBER_KEY = "group_vq77l17/Household_number"


def duplicated_subjects():
    """{subject uuid: [rows]} for every uuid stored on more than one HouseholdData row."""
    by_uuid = defaultdict(list)
    rows = HouseholdData.objects.exclude(rhs_data__isnull=True).only("id", "slum_id", "household_number", "rhs_data")
    for row in rows.iterator():
        uuid = (row.rhs_data or {}).get("rhs_uuid")
        if uuid:
            by_uuid[uuid].append(row)
    return {uuid: rows for uuid, rows in by_uuid.items() if len(rows) > 1}


def factsheet_number_mismatches():
    """[(row, number inside the form)] where the factsheet form names another household."""
    out = []
    rows = HouseholdData.objects.exclude(ff_data__isnull=True).only("id", "slum_id", "household_number", "ff_data")
    for row in rows.iterator():
        inner = (row.ff_data or {}).get(FF_NUMBER_KEY)
        if inner is not None and str(inner).strip() != row.household_number:
            out.append((row, inner))
    return out


def run(apply=False, api=None, out=print):
    """Reconcile duplicated subjects against AVNI, then fix factsheet numbers. Returns counts."""
    api = api or client()
    counts = Counter()

    for uuid, rows in sorted(duplicated_subjects().items()):
        try:
            record = households.fetch_subject(uuid, api)
        except AvniError as exc:
            out("SKIP   subject %s not fetched: %s" % (uuid, exc))
            counts["unreachable"] += 1
            continue

        if record.get("Voided"):
            for row in rows:
                out("DELETE slum %s hh %s (subject %s voided in AVNI)" % (row.slum_id, row.household_number, uuid))
            counts["delete"] += len(rows)
            if apply:
                households.remove_voided_household(record)
            continue

        household = households.household_from_record(record)
        try:
            slum_id, city_id = slum_and_city_ids(household.slum)
        except LookupError as exc:
            out("SKIP   subject %s: %s" % (uuid, exc))
            counts["unreachable"] += 1
            continue
        rename, delete = households.plan_stale_rows(uuid, slum_id, household.number)
        if rename is not None:
            out("RENAME slum %s hh %s -> slum %s hh %s (subject %s)" % (rename.slum_id, rename.household_number, slum_id, household.number, uuid))
            counts["rename"] += 1
        for row in delete:
            out("DELETE slum %s hh %s (subject %s is now hh %s in slum %s)" % (row.slum_id, row.household_number, uuid, household.number, slum_id))
        counts["delete"] += len(delete)
        if apply:
            households.save_household_record(record)

    for row, inner in factsheet_number_mismatches():
        out("FF-NUM slum %s hh %s: form says %r -> %r" % (row.slum_id, row.household_number, inner, row.household_number))
        counts["ff_number"] += 1
        if apply:
            row.ff_data[FF_NUMBER_KEY] = row.household_number
            row.save(update_fields=["ff_data"])

    out("%s: %s renamed, %s deleted, %s factsheet numbers fixed, %s skipped" % (
        "Applied" if apply else "Planned (re-run with --apply)",
        counts["rename"], counts["delete"], counts["ff_number"], counts["unreachable"],
    ))
    return counts
