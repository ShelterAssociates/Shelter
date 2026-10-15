"""
READ-ONLY report: finds every MemberData row whose computed
`cup_used_in_last_followup` would come back null, which is what crashes the
Member ETL with a not-null constraint violation and aborts that slum's batch.

Does NOT write/save anything to the DB - only reads, and writes a local CSV
(+ JSON) report.

Run on production with:

    python manage.py shell < find_null_cup_rows_prod.py

Output: null_cup_used_rows_prod.csv with columns:
    city_name, slum_name, household_number, household_uuid, member_id, member_uuid

Note: there is no dedicated household_uuid column anywhere in this codebase.
The household's AVNI subject uuid lives inside HouseholdData.rhs_data['rhs_uuid']
(falling back to HouseholdData.ff_data['ff_uuid'] if rhs_uuid isn't present),
keyed by (slum_id, household_number). Household numbers are stored with
inconsistent zero-padding ('22', '022', '0022' all occur), so the lookup uses
the same normalize_household_number / household_number_variants helpers the
photos app uses, rather than an exact string match.
"""
import csv
import json
from collections import defaultdict

from graphs.models import MemberData, HouseholdData
from graphs.member_data_analysis import MemberDataProcess
from photos.utils import normalize_household_number, household_number_variants

slums = list(MemberData.objects.all().values_list("slum_id", flat=True).distinct())
print(f"Checking {len(slums)} slums...")

results = []
errors = {}

for slum_id in slums:
    try:
        proc = MemberDataProcess(slum_id)
        df = proc.create_member_metrics()
        df = proc.create_member_program_metrics(df)
    except Exception as e:
        errors[slum_id] = str(e)
        continue

    null_rows = df[df["cup_used_in_last_followup"].isnull()]
    for _, row in null_rows.iterrows():
        results.append(
            {
                "slum_id": slum_id,
                "member_id": int(row["id"]),
                "household_number": row["household_number"],
                "member_first_name": row.get("member_first_name"),
                "city_name": row.get("city_name"),
                "slum_name": row.get("slum_name"),
            }
        )

print(f"\nTotal rows with null cup_used_in_last_followup: {len(results)}")

# Pull member_uuid separately since it's not part of the ETL's working dataframe
member_ids = [r["member_id"] for r in results]
uuid_map = dict(
    MemberData.objects.filter(id__in=member_ids).values_list("id", "member_uuid")
)
for r in results:
    r["member_uuid"] = uuid_map.get(r["member_id"], "")

# Household uuid lives inside HouseholdData.rhs_data['rhs_uuid'] (fallback ff_data['ff_uuid']),
# keyed by (slum_id, household_number) - matched via zero-padding variants since
# HouseholdData stores household_number inconsistently ('22'/'022'/'0022' all occur).
household_keys = {(r["slum_id"], r["household_number"]) for r in results}
all_variants = set()
for _, hn in household_keys:
    all_variants |= household_number_variants(normalize_household_number(hn))

households_by_slum_and_number = defaultdict(dict)
for hh in HouseholdData.objects.filter(
    slum_id__in={k[0] for k in household_keys},
    household_number__in=all_variants,
):
    rhs_uuid = (hh.rhs_data or {}).get("rhs_uuid")
    ff_uuid = (hh.ff_data or {}).get("ff_uuid")
    households_by_slum_and_number[hh.slum_id][hh.household_number] = rhs_uuid or ff_uuid or ""

household_uuid_map = {}
for slum_id, hn in household_keys:
    candidates = households_by_slum_and_number.get(slum_id, {})
    for variant in household_number_variants(normalize_household_number(hn)):
        if variant in candidates and candidates[variant]:
            household_uuid_map[(slum_id, hn)] = candidates[variant]
            break
    else:
        household_uuid_map[(slum_id, hn)] = ""

for r in results:
    r["household_uuid"] = household_uuid_map.get((r["slum_id"], r["household_number"]), "")

with open("null_cup_used_rows_prod.json", "w") as f:
    json.dump(results, f, indent=2)
print("Full detail (JSON) written to: null_cup_used_rows_prod.json")

csv_path = "null_cup_used_rows_prod.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "city_name",
            "slum_name",
            "household_number",
            "household_uuid",
            "member_id",
            "member_uuid",
            "member_first_name",
        ],
    )
    writer.writeheader()
    for r in results:
        writer.writerow(
            {
                "city_name": r["city_name"],
                "slum_name": r["slum_name"],
                "household_number": r["household_number"],
                "household_uuid": r["household_uuid"],
                "member_id": r["member_id"],
                "member_uuid": r["member_uuid"],
                "member_first_name": r["member_first_name"],
            }
        )
print(f"CSV report written to: {csv_path}")

by_slum = defaultdict(list)
for r in results:
    by_slum[r["slum_id"]].append(r["household_number"])

print("\nHousehold numbers by slum:")
for slum_id, hns in sorted(by_slum.items()):
    print(f"  slum {slum_id}: {len(hns)} rows -> {hns}")

if errors:
    print(f"\n{len(errors)} slum(s) errored while computing metrics (e.g. the JSONString double-encoding issue):")
    for sid, err in errors.items():
        print(f"  slum {sid}: {err}")
