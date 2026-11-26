import json
from graphs.models import MemberData
from graphs.member_data_analysis import MemberDataProcess

slums = list(MemberData.objects.all().values_list('slum_id', flat=True).distinct())
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
    null_rows = df[df['cup_used_in_last_followup'].isnull()]
    for _, row in null_rows.iterrows():
        results.append({
            "slum_id": slum_id,
            "member_id": int(row["id"]),
            "household_number": row["household_number"],
            "member_first_name": row.get("member_first_name"),
        })

print(f"Total rows with null cup_used_in_last_followup: {len(results)}")
with open("null_cup_used_rows.json", "w") as f:
    json.dump(results, f, indent=2)
print("Written to null_cup_used_rows.json")

from collections import defaultdict
by_slum = defaultdict(list)
for r in results:
    by_slum[r["slum_id"]].append(r["household_number"])
for slum_id, hns in sorted(by_slum.items()):
    print(f"slum {slum_id}: {len(hns)} rows -> {hns}")

if errors:
    print("Slums that errored during read-only metrics computation:")
    for sid, err in errors.items():
        print(f"  slum {sid}: {err}")
