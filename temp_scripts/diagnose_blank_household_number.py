"""
READ-ONLY diagnostic: for the member_ids found in null_cup_used_rows_prod.csv
(all showed blank household_number in the ETL's computed dataframe), check the
RAW MemberData.household_number DB field directly, and whether member_data
(the JSON blob) also contains a conflicting 'household_number' key that could
overwrite it during the ETL's dict merge.

This does NOT write/save anything - read-only, prints + writes a report CSV.

Run on production with:

    python manage.py shell < diagnose_blank_household_number.py

Expects null_cup_used_rows_prod.csv to be in the current directory (the one
you already generated).
"""
import csv

from graphs.models import MemberData

member_ids = []
with open("null_cup_used_rows_prod.csv") as f:
    for row in csv.DictReader(f):
        member_ids.append(int(row["member_id"]))

print(f"Checking {len(member_ids)} member_ids from null_cup_used_rows_prod.csv")

report = []
for m in MemberData.objects.filter(id__in=member_ids):
    json_has_key = isinstance(m.member_data, dict) and "household_number" in m.member_data
    json_value = m.member_data.get("household_number") if json_has_key else None
    report.append(
        {
            "member_id": m.id,
            "raw_db_household_number": repr(m.household_number),
            "member_data_has_household_number_key": json_has_key,
            "member_data_household_number_value": repr(json_value),
        }
    )

blank_in_db = [r for r in report if not str(r["raw_db_household_number"]).strip("'\"") ]
json_collisions = [r for r in report if r["member_data_has_household_number_key"]]

print(f"\nTotal checked: {len(report)}")
print(f"Raw DB household_number is actually blank/empty: {len(blank_in_db)}")
print(f"member_data JSON contains a conflicting 'household_number' key: {len(json_collisions)}")

with open("diagnose_blank_household_number.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(report[0].keys()) if report else [])
    writer.writeheader()
    writer.writerows(report)
print("\nFull detail written to: diagnose_blank_household_number.csv")

if json_collisions:
    print("\nSample JSON-collision rows (these are a code bug - ETL overwrites a good household_number with a blank JSON value):")
    for r in json_collisions[:5]:
        print(" ", r)

if blank_in_db and not json_collisions:
    print("\nNo JSON collisions found - household_number is genuinely blank at the DB level for these members (a data problem, not a code bug).")
