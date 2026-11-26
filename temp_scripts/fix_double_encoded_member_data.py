"""
One-off data fix for MemberData.member_data rows that were saved double-encoded
(the DB column holds a JSON string whose contents are themselves JSON, instead
of a JSON object). Run via:

    python manage.py shell < fix_double_encoded_member_data.py

Steps:
  1. Find every MemberData row where member_data is not a dict.
  2. Back up id, slum_id, and the raw (double-encoded) value to a local JSON
     file before changing anything.
  3. Decode each value one extra time and re-save it as a proper dict.
  4. Print a summary, including any rows that still can't be decoded.

Set DRY_RUN = True to only inspect/back up without writing changes.
"""
import json
import datetime

from graphs.models import MemberData

DRY_RUN = False  # flip to False to actually write the fix

backup_path = f"member_data_double_encoded_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"

affected = []
for row in MemberData.objects.all().only("id", "slum_id", "member_data"):
    if not isinstance(row.member_data, dict):
        affected.append(row)

print(f"Found {len(affected)} rows where member_data is not a dict.")

backup = []
fixed = 0
still_broken = []

for row in affected:
    raw_value = row.member_data
    backup.append(
        {
            "id": row.id,
            "slum_id": row.slum_id,
            "raw_value": str(raw_value),
        }
    )
    try:
        decoded = json.loads(str(raw_value))
    except (ValueError, TypeError) as e:
        still_broken.append({"id": row.id, "slum_id": row.slum_id, "error": str(e)})
        continue

    if not isinstance(decoded, dict):
        still_broken.append(
            {"id": row.id, "slum_id": row.slum_id, "error": f"decoded to {type(decoded).__name__}, not dict"}
        )
        continue

    if not DRY_RUN:
        row.member_data = decoded
        row.save(update_fields=["member_data"])
    fixed += 1

with open(backup_path, "w") as f:
    json.dump(backup, f, indent=2)

print(f"Backup written to: {backup_path}")
print(f"{'[DRY RUN] Would fix' if DRY_RUN else 'Fixed'}: {fixed} rows")
if still_broken:
    print(f"Still broken / needs manual review: {len(still_broken)} rows")
    for item in still_broken:
        print("  ", item)
else:
    print("No rows left unresolved.")
