"""
READ-ONLY: for each member in remaining_null_cup_detail.csv, fetch their
subject record LIVE from AVNI, list every encounter uuid AVNI has attached to
them, fetch each encounter, and show its "Encounter type", whether it has the
target question, and when it was last modified in AVNI - then compare that
timestamp against our last successful sync job run, to show whether this is
simply "not synced yet" (AVNI data is newer than our last run) or "should
have synced already but didn't" (AVNI data predates our last successful run).

Does NOT write/save anything to our DB - only reads, and makes live read-only
GET calls to the AVNI API. Writes a report CSV.

Run on production with:

    python manage.py shell < check_avni_encounter_sync_timing.py

Expects remaining_null_cup_detail.csv (from inspect_remaining_null_cup.py) in
the current directory.
"""
import csv
import time

from avni.client import AvniError, client
from avni import paths
from avni.sync.households import fetch_subject
from notification.models import JobRun

EXPECTED_QUESTION = "Did you use cup in the previous menstruation?"
RELEVANT_JOB_KEYS = ["avni_daily_sync", "household_encounter_sync", "member_sync", "encounter_sync"]
SLEEP_BETWEEN_CALLS = 0.2

with open("remaining_null_cup_detail.csv") as f:
    rows = list(csv.DictReader(f))

print(f"Checking {len(rows)} members against live AVNI...\n")

# Last successful run per relevant job, for comparison.
last_success = {}
for key in RELEVANT_JOB_KEYS:
    run = JobRun.objects.filter(job_key=key, status="success").order_by("-finished_on").first()
    last_success[key] = run.finished_on if run else None
    print(f"Last successful '{key}' run: {last_success[key]}")
print()

api = client()
results = []

for i, row in enumerate(rows, 1):
    member_id = row["member_id"]
    from graphs.models import MemberData
    member = MemberData.objects.filter(id=member_id).only("member_uuid").first()
    if not member or not member.member_uuid:
        print(f"[{i}/{len(rows)}] member {member_id}: no member_uuid locally, skipping")
        continue

    try:
        subject = fetch_subject(member.member_uuid, api)
    except AvniError as e:
        print(f"[{i}/{len(rows)}] member {member_id}: subject fetch FAILED {e}")
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    encounter_uuids = subject.get("encounters") or []
    if not encounter_uuids:
        print(f"[{i}/{len(rows)}] member {member_id}: AVNI subject has NO encounters listed at all")
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    for enc_uuid in encounter_uuids:
        try:
            enc = api.get_json(paths.encounter(enc_uuid))
        except AvniError as e:
            print(f"    encounter {enc_uuid}: fetch FAILED {e}")
            continue
        observations = enc.get("observations") or {}
        has_question = EXPECTED_QUESTION in observations
        value = observations.get(EXPECTED_QUESTION)
        modified_at = (enc.get("audit") or {}).get("Last modified at")
        voided = bool(enc.get("Voided"))

        print(f"[{i}/{len(rows)}] member {member_id} encounter {enc_uuid}: "
              f"type={enc.get('Encounter type')!r} voided={voided} "
              f"has_question={has_question} value={value!r} last_modified={modified_at}")

        results.append(
            {
                "member_id": member_id,
                "member_uuid": member.member_uuid,
                "encounter_uuid": enc_uuid,
                "encounter_type": enc.get("Encounter type"),
                "voided": voided,
                "has_target_question": has_question,
                "target_value": value,
                "avni_last_modified": modified_at,
            }
        )
    time.sleep(SLEEP_BETWEEN_CALLS)

with open("avni_encounter_sync_timing.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else [])
    writer.writeheader()
    writer.writerows(results)
print(f"\nWritten: avni_encounter_sync_timing.csv ({len(results)} encounter rows)")

with_answer = [r for r in results if r["has_target_question"] and r["target_value"]]
print(f"\n{len(with_answer)} encounter(s) found in AVNI WITH an answer to the target question.")
print("For each, compare 'avni_last_modified' to the last successful job run timestamps printed above:")
print("  - if avni_last_modified is AFTER our last successful run -> simply not synced yet (pending, normal)")
print("  - if avni_last_modified is BEFORE our last successful run -> should have synced already, this is a real gap")
for r in with_answer[:20]:
    print(" ", r["member_id"], r["encounter_uuid"], r["avni_last_modified"])
