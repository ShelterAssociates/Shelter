"""
READ-ONLY: for each member in null_cup_used_rows_prod.csv (the ones still
coming back with null cup_used_in_last_followup AFTER the resync), show every
question/answer we actually have for them - member_data (registration survey)
and every MemberEncounterData row (follow-up surveys), newest first - so you
can see exactly what's present vs missing question-by-question.

Does NOT write/save anything. Prints a formatted report, and also writes
remaining_null_cup_detail.csv (one row per member, flattened) for a wider
look in a spreadsheet.

Run on production with:

    python manage.py shell < inspect_remaining_null_cup.py

Expects null_cup_used_rows_prod.csv (the regenerated one, from re-running
find_null_cup_rows_prod.py after the resync) in the current directory.
"""
import csv

from graphs.models import MemberData, MemberEncounterData

EXPECTED_ENCOUNTER_QUESTION = "Did you use cup in the previous menstruation?"

with open("null_cup_used_rows_prod.csv") as f:
    rows = list(csv.DictReader(f))

member_ids = [int(r["member_id"]) for r in rows]
print(f"Inspecting {len(member_ids)} remaining members...\n")

flat_rows = []

for member_id in member_ids:
    member = MemberData.objects.filter(id=member_id).first()
    print("=" * 80)
    if not member:
        print(f"member_id {member_id}: NOT FOUND in MemberData")
        continue

    print(f"member_id={member_id}  name={member.member_first_name!r} "
          f"household_number={member.household_number!r}  slum_id={member.slum_id}")
    print("-- member_data (registration survey) --")
    data = member.member_data or {}
    if isinstance(data, dict) and data:
        for q, a in data.items():
            print(f"  {q!r}: {a!r}")
    else:
        print(f"  (empty or not a dict: {data!r})")

    encounters = MemberEncounterData.objects.filter(member_id=member_id).order_by("-submission_date")
    print(f"-- {encounters.count()} MemberEncounterData row(s), newest first --")

    latest_has_question = None
    latest_value = None
    if encounters.exists():
        for enc in encounters:
            edata = enc.encounter_data or {}
            has_q = isinstance(edata, dict) and EXPECTED_ENCOUNTER_QUESTION in edata
            print(f"  encounter_id={enc.id} submission_date={enc.submission_date} "
                  f"has_target_question={has_q}")
            if isinstance(edata, dict):
                for q, a in edata.items():
                    marker = " <-- TARGET" if q == EXPECTED_ENCOUNTER_QUESTION else ""
                    print(f"      {q!r}: {a!r}{marker}")
            else:
                print(f"      (encounter_data not a dict: {edata!r})")
        latest = encounters.first()
        ledata = latest.encounter_data or {}
        latest_has_question = isinstance(ledata, dict) and EXPECTED_ENCOUNTER_QUESTION in ledata
        latest_value = ledata.get(EXPECTED_ENCOUNTER_QUESTION) if isinstance(ledata, dict) else None
    else:
        print("  (no encounters at all for this member)")

    flat_rows.append(
        {
            "member_id": member_id,
            "household_number": member.household_number,
            "slum_id": member.slum_id,
            "member_data_keys": ", ".join((member.member_data or {}).keys()) if isinstance(member.member_data, dict) else "",
            "encounter_count": encounters.count(),
            "latest_encounter_has_target_question": latest_has_question,
            "latest_encounter_target_value": latest_value,
        }
    )
    print()

with open("remaining_null_cup_detail.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(flat_rows[0].keys()) if flat_rows else [])
    writer.writeheader()
    writer.writerows(flat_rows)
print("\nWritten: remaining_null_cup_detail.csv")

no_encounters = sum(1 for r in flat_rows if r["encounter_count"] == 0)
has_encounters_no_question = sum(
    1 for r in flat_rows if r["encounter_count"] > 0 and not r["latest_encounter_has_target_question"]
)
has_question_but_still_null = sum(
    1 for r in flat_rows if r["latest_encounter_has_target_question"] and not r["latest_encounter_target_value"]
)

print("\nSummary:")
print(f"  Members with NO MemberEncounterData at all: {no_encounters}")
print(f"  Members with encounters, but latest one lacks the target question: {has_encounters_no_question}")
print(f"  Members whose latest encounter HAS the question but value is blank/falsy: {has_question_but_still_null}")
