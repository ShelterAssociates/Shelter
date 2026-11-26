"""
READ-ONLY check: AVNI's own database (per query_result.csv, pulled via direct
SQL against AVNI) shows all 279 households for our problem members DO exist,
have a real household_uuid/household_number, and are NOT voided.

This script checks whether those same households actually exist in OUR app's
HouseholdData table - if not, that's the real root cause: these households
were simply never synced into our DB, so MemberData.household_number was
never populated for their members.

Does NOT write/save anything - read-only, prints + writes a report CSV.

Memory note: this version only ever queries the ~279 relevant rows (scoped by
slum_id and household_number), never the full HouseholdData/MemberData
tables, since those are large enough on production to get OOM-killed by a
full-table scan.

Run on production with:

    python manage.py shell < check_households_exist_in_db.py

Expects query_result.csv (the AVNI raw-DB export: City, Slum, household_uuid,
household_number, member_uuid, member_first_name, member_last_name,
date_of_birth, gender, household_voided, member_voided) in the current
directory.
"""
import csv

from graphs.models import HouseholdData, MemberData
from photos.utils import normalize_household_number, household_number_variants

with open("query_result.csv") as f:
    avni_rows = list(csv.DictReader(f))

print(f"Checking {len(avni_rows)} AVNI household/member pairs against our DB...")

# Resolve slum_id for each distinct (Slum, City) pair via MemberData, scoped
# small since there are only ~16 distinct slums here.
slum_city_pairs = {(r["Slum"].strip(), r["City"].strip()) for r in avni_rows}
slum_id_by_name = {}
for slum_name, city_name in slum_city_pairs:
    qs = MemberData.objects.filter(slum_id__name=slum_name)
    if city_name:
        qs = qs.filter(
            slum_id__electoral_ward__administrative_ward__city__name__city_name=city_name
        )
    slum_id = qs.values_list("slum_id", flat=True).first()
    if slum_id:
        slum_id_by_name[(slum_name, city_name)] = slum_id

print(f"Resolved {len(slum_id_by_name)} / {len(slum_city_pairs)} slum(s).")

all_slum_ids = set(slum_id_by_name.values())

# Narrow household_number candidates to just the ones in our CSV (with
# zero-padding variants), scoped to the relevant slums only - not a full scan.
needed_variants = set()
for r in avni_rows:
    needed_variants |= household_number_variants(normalize_household_number(r["household_number"]))

households_by_slum_number = {}
for hh in HouseholdData.objects.filter(
    slum_id__in=all_slum_ids, household_number__in=needed_variants
).only("id", "slum_id", "household_number", "rhs_data", "ff_data"):
    rhs_uuid = (hh.rhs_data or {}).get("rhs_uuid") if isinstance(hh.rhs_data, dict) else None
    ff_uuid = (hh.ff_data or {}).get("ff_uuid") if isinstance(hh.ff_data, dict) else None
    households_by_slum_number.setdefault((hh.slum_id, hh.household_number), []).append(
        {"id": hh.id, "household_number": hh.household_number, "rhs_uuid": rhs_uuid, "ff_uuid": ff_uuid}
    )

# Member lookups scoped to just the 279 uuids in the CSV.
member_uuids = [r["member_uuid"].strip() for r in avni_rows]
member_map = {
    m.member_uuid: m
    for m in MemberData.objects.filter(member_uuid__in=member_uuids).only(
        "id", "member_uuid", "household_number", "slum_id"
    )
}

results = []
for row in avni_rows:
    household_uuid = row["household_uuid"].strip()
    member_uuid = row["member_uuid"].strip()
    slum_key = (row["Slum"].strip(), row["City"].strip())
    slum_id = slum_id_by_name.get(slum_key)

    local_household = None
    if slum_id:
        for variant in household_number_variants(normalize_household_number(row["household_number"])):
            candidates = households_by_slum_number.get((slum_id, variant), [])
            match = None
            for c in candidates:
                if c["rhs_uuid"] == household_uuid or c["ff_uuid"] == household_uuid:
                    match = c
                    break
            if match:
                local_household = match
                break

    member = member_map.get(member_uuid)

    results.append(
        {
            "City": row["City"],
            "Slum": row["Slum"],
            "avni_household_uuid": household_uuid,
            "avni_household_number": row["household_number"],
            "member_uuid": member_uuid,
            "member_id_in_our_db": member.id if member else "",
            "household_exists_in_our_db": bool(local_household),
            "our_db_household_number_for_this_household": local_household["household_number"] if local_household else "",
            "our_db_member_household_number_field": (member.household_number if member else "") or "",
        }
    )

with open("household_existence_check.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else [])
    writer.writeheader()
    writer.writerows(results)
print("Written: household_existence_check.csv")

missing_household = [r for r in results if not r["household_exists_in_our_db"]]
present_household = [r for r in results if r["household_exists_in_our_db"]]
member_not_found = [r for r in results if not r["member_id_in_our_db"]]
blank_member_hn = [r for r in results if r["household_exists_in_our_db"] and not r["our_db_member_household_number_field"]]

print("\nSummary:")
print(f"  Total checked: {len(results)}")
print(f"  Household EXISTS in our HouseholdData table: {len(present_household)}")
print(f"  Household MISSING from our HouseholdData table entirely: {len(missing_household)}")
print(f"  Member not found in our MemberData table at all: {len(member_not_found)}")
print(f"  Household exists locally BUT member's household_number field is still blank: {len(blank_member_hn)}")

if missing_household:
    print("\nSample of households missing from our DB:")
    for r in missing_household[:5]:
        print(" ", r["Slum"], r["avni_household_uuid"], r["avni_household_number"])

if blank_member_hn:
    print("\nSample where household exists locally but member.household_number is still blank (a sync/write bug, not a missing-data issue):")
    for r in blank_member_hn[:5]:
        print(" ", r["member_uuid"], "-> household", r["avni_household_uuid"])
