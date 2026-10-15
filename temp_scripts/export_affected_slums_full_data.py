"""
READ-ONLY export: for every slum that showed up in null_cup_used_rows_prod.csv
(the slums with members missing cup_used_in_last_followup / blank household
number), pull EVERY household and EVERY member in those slums - not just the
problem rows - so they can be reviewed/cross-checked as a whole.

Does NOT write/save anything to the DB - only reads, and writes two local CSVs.

Run on production with:

    python manage.py shell < export_affected_slums_full_data.py

Expects null_cup_used_rows_prod.csv in the current directory.

Output:
  households_in_affected_slums.csv - every HouseholdData row in those slums
  members_in_affected_slums.csv    - every MemberData row in those slums
"""
import csv

from graphs.models import HouseholdData, MemberData

with open("null_cup_used_rows_prod.csv") as f:
    rows = list(csv.DictReader(f))

slum_city_pairs = {(r["slum_name"], r["city_name"]) for r in rows}
print(f"Distinct (slum_name, city_name) pairs from null_cup_used_rows_prod.csv: {len(slum_city_pairs)}")
for slum_name, city_name in sorted(slum_city_pairs):
    print(f"  {slum_name} / {city_name}")

slum_ids = set()
unresolved = []
for slum_name, city_name in slum_city_pairs:
    ids = list(
        MemberData.objects.filter(
            slum_id__name=slum_name,
            slum_id__electoral_ward__administrative_ward__city__name__city_name=city_name,
        )
        .values_list("slum_id", flat=True)
        .distinct()
    )
    if ids:
        slum_ids.update(ids)
    else:
        unresolved.append((slum_name, city_name))

print(f"\nResolved {len(slum_ids)} slum_id(s): {sorted(slum_ids)}")
if unresolved:
    print(f"Could NOT resolve slum_id for {len(unresolved)} pairs: {unresolved}")

# ---- Households ----
household_fields = [
    "id",
    "household_number",
    "slum_id",
    "city_id",
    "submission_date",
    "created_date",
    "kobo_id",
    "ff_kobo_id",
]
household_rows = []
for hh in HouseholdData.objects.filter(slum_id__in=slum_ids).only(
    "id", "household_number", "slum_id", "city_id", "submission_date", "created_date", "kobo_id", "ff_kobo_id", "rhs_data", "ff_data"
):
    rhs_uuid = (hh.rhs_data or {}).get("rhs_uuid") if isinstance(hh.rhs_data, dict) else None
    ff_uuid = (hh.ff_data or {}).get("ff_uuid") if isinstance(hh.ff_data, dict) else None
    household_rows.append(
        {
            "id": hh.id,
            "household_number": hh.household_number,
            "slum_id": hh.slum_id,
            "city_id": hh.city_id,
            "submission_date": hh.submission_date,
            "created_date": hh.created_date,
            "household_uuid": rhs_uuid or ff_uuid or "",
            "has_rhs_data": isinstance(hh.rhs_data, dict),
            "has_ff_data": isinstance(hh.ff_data, dict),
        }
    )

with open("households_in_affected_slums.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(household_rows[0].keys()) if household_rows else [])
    writer.writeheader()
    writer.writerows(household_rows)
print(f"\nWritten households_in_affected_slums.csv: {len(household_rows)} rows")

# ---- Members ----
member_rows = []
for m in MemberData.objects.filter(slum_id__in=slum_ids).only(
    "id", "slum_id", "household_number", "member_uuid", "member_first_name", "member_last_name",
    "date_of_birth", "gender", "created_date", "submission_date",
):
    member_rows.append(
        {
            "id": m.id,
            "slum_id": m.slum_id,
            "household_number": m.household_number,
            "member_uuid": m.member_uuid,
            "member_first_name": m.member_first_name,
            "member_last_name": m.member_last_name,
            "date_of_birth": m.date_of_birth,
            "gender": m.gender_display,
            "created_date": m.created_date,
            "submission_date": m.submission_date,
        }
    )

with open("members_in_affected_slums.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(member_rows[0].keys()) if member_rows else [])
    writer.writeheader()
    writer.writerows(member_rows)
print(f"Written members_in_affected_slums.csv: {len(member_rows)} rows")

blank_hn_members = sum(1 for r in member_rows if not str(r["household_number"] or "").strip())
print(f"\nOf those members, {blank_hn_members} have a blank household_number.")
