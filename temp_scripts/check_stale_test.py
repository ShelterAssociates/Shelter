"""
READ-ONLY check: for each member, fetch their real AVNI program-encounter
history (via AvniProvider.get_subject_tree - the same read path the real sync
uses) and find the chronologically latest COMPLETED (non-empty, non-voided)
program encounter. Compare its uuid/answer against what we currently have
stored in MemberEncounterData.

This detects the "stale encounter" bug: our write_member_encounter() upsert
has no "only overwrite if newer" guard, so whichever encounter happened to
sync last can be an OLDER one than what AVNI actually has as most recent,
silently keeping stale data (e.g. "Follow-up 1" instead of "Follow-up 3").

Does NOT write/save anything - read-only, makes live GET calls to AVNI.
Writes a report CSV.

Run on production with:

    python manage.py shell < check_stale_encounter_prod.py

Expects a CSV with a `member_id` column in the current directory - edit
INPUT_CSV below to point at whichever list you want to check (e.g.
null_cup_used_rows_prod.csv or remaining_null_cup_detail.csv).
"""
import csv
import time
from datetime import datetime

from avni.provider import AvniProvider
from graphs.models import MemberData, MemberEncounterData

INPUT_CSV = "remaining_null_cup_detail_test3.csv"
EXPECTED_QUESTION = "Did you use cup in the previous menstruation?"
SLEEP_BETWEEN_CALLS = 0.2


def parse_dt(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")


with open(INPUT_CSV) as f:
    rows = list(csv.DictReader(f))

member_ids = sorted({r["member_id"] for r in rows})
print(f"Checking {len(member_ids)} members from {INPUT_CSV} for stale stored encounters...\n")

provider = AvniProvider()
results = []

for i, member_id in enumerate(member_ids, 1):
    member = MemberData.objects.filter(id=member_id).first()
    if not member or not member.member_uuid:
        print(f"[{i}/{len(member_ids)}] member {member_id}: no member_uuid locally, skipping")
        continue

    try:
        tree = provider.get_subject_tree(member.member_uuid)
    except Exception as exc:
        print(f"[{i}/{len(member_ids)}] member {member_id}: AVNI fetch FAILED {exc}")
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    # Collect every real (non-voided, non-empty) program encounter across all enrolments.
    completed = []
    for enrolment, program_encounters in (tree.enrolments or []):
        for pe in (program_encounters or []):
            if pe.get("Voided"):
                continue
            observations = pe.get("observations") or {}
            if not observations:
                continue  # the "scheduled" empty placeholder - correctly not a real completed visit
            modified_at = (pe.get("audit") or {}).get("Last modified at")
            completed.append((parse_dt(modified_at), pe.get("ID"), observations, modified_at))

    if not completed:
        print(f"[{i}/{len(member_ids)}] member {member_id}: AVNI has no completed program encounters at all")
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    completed.sort(key=lambda x: x[0])
    latest_dt, latest_uuid, latest_obs, latest_raw_ts = completed[-1]

    local = MemberEncounterData.objects.filter(member_id=member_id).order_by("-submission_date").first()
    local_uuid = local.encounter_uuid if local else None
    is_stale = local_uuid != latest_uuid

    print(f"[{i}/{len(member_ids)}] member {member_id}: "
          f"{'STALE' if is_stale else 'OK'} - stored={local_uuid} latest_in_avni={latest_uuid} "
          f"({len(completed)} completed encounters in AVNI)")

    results.append(
        {
            "member_id": member_id,
            "member_uuid": member.member_uuid,
            "completed_encounters_in_avni": len(completed),
            "stored_encounter_uuid": local_uuid or "",
            "latest_avni_encounter_uuid": latest_uuid,
            "latest_avni_last_modified": latest_raw_ts,
            "is_stale": is_stale,
            "latest_avni_target_value": latest_obs.get(EXPECTED_QUESTION, ""),
            "stored_target_value": (local.encounter_data or {}).get(EXPECTED_QUESTION, "") if local else "",
        }
    )
    time.sleep(SLEEP_BETWEEN_CALLS)

with open("stale_encounter_check.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else [])
    writer.writeheader()
    writer.writerows(results)
print("\nWritten: stale_encounter_check.csv")

stale = [r for r in results if r["is_stale"]]
print(f"\nSummary: {len(stale)} / {len(results)} members have a STALE stored encounter "
      f"(an older completed follow-up is kept instead of the true latest one).")
