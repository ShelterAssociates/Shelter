"""
READ-ONLY report: for each member_id/member_uuid in null_cup_used_rows_prod.csv
(members whose household_number came back blank locally), hit the live AVNI
API directly to find:
  - the member's own subject record in AVNI, and whether it is voided
  - the household number AVNI has for that member (via Groups/observations)
  - the household's own AVNI subject uuid (preferring our local HouseholdData
    cache first, falling back to AVNI's slow subject scan) and whether THAT
    household subject is voided in AVNI

This makes live calls to the AVNI API (read-only GETs) - no writes to AVNI and
no writes to our own DB, only local CSV/JSON output. It can be slow (up to
~2 API calls per member) and is throttled with a small delay between calls.

Run on production with:

    python manage.py shell < fetch_household_from_avni.py

Expects null_cup_used_rows_prod.csv in the current directory.
"""
import csv
import json
import time

from avni.client import AvniError
from avni.sync.households import fetch_subject as fetch_household_subject
from avni.sync.members import member_household_number
from avni.media import find_subject_uuid
from graphs.models import HouseholdData
from photos.utils import normalize_household_number, household_number_variants

SLEEP_BETWEEN_CALLS = 0.2  # be polite to the AVNI API

with open("null_cup_used_rows_prod.csv") as f:
    rows = list(csv.DictReader(f))

print(f"Looking up {len(rows)} members against live AVNI...")

def local_household_uuid(slum_id, household_number):
    if not household_number:
        return None
    variants = household_number_variants(normalize_household_number(household_number))
    hh = HouseholdData.objects.filter(slum_id=slum_id, household_number__in=variants).first()
    if not hh:
        return None
    return (hh.rhs_data or {}).get("rhs_uuid") or (hh.ff_data or {}).get("ff_uuid")


results = []
for i, row in enumerate(rows, 1):
    member_id = row["member_id"]
    member_uuid = row["member_uuid"]
    out = {
        "member_id": member_id,
        "member_uuid": member_uuid,
        "city_name": row["city_name"],
        "slum_name": row["slum_name"],
        "member_voided": None,
        "household_number_from_avni": None,
        "household_uuid": None,
        "household_uuid_source": None,
        "household_voided": None,
        "error": None,
    }

    try:
        member_record = fetch_household_subject(member_uuid)
    except AvniError as e:
        out["error"] = f"member fetch failed: {e}"
        results.append(out)
        print(f"[{i}/{len(rows)}] member {member_id}: ERROR {e}")
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    out["member_voided"] = bool(member_record.get("Voided"))
    household_number = member_household_number(member_record)
    out["household_number_from_avni"] = household_number

    slum_id = None
    # slum_id isn't in the csv; look it up locally from MemberData so we can
    # use the existing household-number resolution helpers.
    from graphs.models import MemberData
    m = MemberData.objects.filter(id=member_id).only("slum_id").first()
    slum_id = m.slum_id if m else None

    household_uuid = None
    if household_number and slum_id:
        household_uuid = local_household_uuid(slum_id, household_number)
        if household_uuid:
            out["household_uuid_source"] = "local HouseholdData cache"
        else:
            household_uuid = find_subject_uuid(slum_id, household_number)
            if household_uuid:
                out["household_uuid_source"] = "AVNI subject scan (fallback)"

    out["household_uuid"] = household_uuid

    if household_uuid:
        try:
            household_record = fetch_household_subject(household_uuid)
            out["household_voided"] = bool(household_record.get("Voided"))
        except AvniError as e:
            out["error"] = f"household fetch failed: {e}"

    results.append(out)
    status = "voided" if out["household_voided"] else ("not voided" if out["household_voided"] is not None else "unknown")
    print(f"[{i}/{len(rows)}] member {member_id}: household_number={household_number!r} household_uuid={household_uuid} ({status})")
    time.sleep(SLEEP_BETWEEN_CALLS)

with open("household_avni_lookup.json", "w") as f:
    json.dump(results, f, indent=2)

csv_path = "household_avni_lookup.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else [])
    writer.writeheader()
    writer.writerows(results)

print(f"\nWritten: {csv_path} and household_avni_lookup.json")

voided_count = sum(1 for r in results if r["household_voided"] is True)
not_voided_count = sum(1 for r in results if r["household_voided"] is False)
unknown_count = sum(1 for r in results if r["household_voided"] is None)
member_voided_count = sum(1 for r in results if r["member_voided"] is True)
no_household_number = sum(1 for r in results if not r["household_number_from_avni"])
errors = sum(1 for r in results if r["error"])

print("\nSummary:")
print(f"  Total members checked: {len(results)}")
print(f"  Member subject itself voided in AVNI: {member_voided_count}")
print(f"  AVNI has no household number for this member (Groups/observations empty): {no_household_number}")
print(f"  Household resolved and VOIDED in AVNI: {voided_count}")
print(f"  Household resolved and NOT voided: {not_voided_count}")
print(f"  Household UUID could not be resolved at all: {unknown_count}")
print(f"  Errors during lookup: {errors}")
