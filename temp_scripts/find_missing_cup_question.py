from django.db.models import Max
from graphs.models import MemberEncounterData, MemberData

QUESTION_KEY = "Did you use cup in the previous menstruation?"

latest_records = (
    MemberEncounterData.objects.values("member_id")
    .annotate(latest_date=Max("submission_date"))
)
latest_pairs = {(r["member_id"], r["latest_date"]) for r in latest_records}

qualified = MemberEncounterData.objects.filter(
    member_id__in=[p[0] for p in latest_pairs],
    submission_date__in=[p[1] for p in latest_pairs],
)

missing = []
for enc in qualified.select_related("member"):
    data = enc.encounter_data
    if not isinstance(data, dict) or QUESTION_KEY not in data or data.get(QUESTION_KEY) is None:
        m = enc.member
        missing.append({
            "member_id": m.id,
            "slum_id": m.slum_id,
            "household_number": m.household_number,
            "member_first_name": m.member_first_name,
            "encounter_data_keys": list(data.keys()) if isinstance(data, dict) else str(type(data)),
        })

print(f"Total members with missing/null '{QUESTION_KEY}' in latest encounter: {len(missing)}")
import json
with open("missing_cup_question_rows.json", "w") as f:
    json.dump(missing, f, indent=2)
print("Written to missing_cup_question_rows.json")

# Print unique household numbers grouped by slum
from collections import defaultdict
by_slum = defaultdict(list)
for row in missing:
    by_slum[row["slum_id"]].append(row["household_number"])

for slum_id, hns in sorted(by_slum.items()):
    print(f"slum {slum_id}: {len(hns)} household numbers -> {hns}")
