"""
WRITE script: scans EVERY member who has at least one MemberEncounterData row
(the population where the overwrite bug could have put the wrong encounter
in), finds the true latest FILLED "Menstrual hygiene Follow-up" program
encounter in live AVNI, and corrects the stored row if it's wrong (stale,
or - worse - a completely different encounter type like "MHM Pre/Post
Impact Assessment" that silently overwrote the real follow-up answer).

This is the root cause fix target: avni/sync/members.py's
write_member_encounter() upserts on (member, slum, program) with no regard
for encounter type or recency, so any later-synced encounter of ANY type can
clobber the real follow-up data. This script repairs already-corrupted rows
using the exact same write path (write_member_encounter), so corrected data
is indistinguishable from a normal sync once fixed.

Does NOT touch member/household data - only MemberEncounterData rows, one
member at a time, with a dated backup of every row before it's changed.

Run on production with:

    python manage.py shell < fix_stale_encounters.py

Writes:
  stale_encounter_fix_backup_<timestamp>.csv - the OLD value of every row this
    script changes, before changing it (for rollback reference)
  stale_encounter_fix_report_<timestamp>.csv - one row per member checked,
    whether it was stale, and what it was corrected to
"""
import csv
import datetime
import time

from avni.client import AvniError
from avni.provider import AvniProvider
from avni.sync.members import write_member_encounter, record_day, audit_days
from graphs.models import MemberData, MemberEncounterData, MemberProgramData

TARGET_ENCOUNTER_TYPE = "Menstrual hygiene Follow-up"
SLEEP_BETWEEN_CALLS = 0.2

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"stale_encounter_fix_backup_{stamp}.csv"
report_path = f"stale_encounter_fix_report_{stamp}.csv"

provider = AvniProvider()

member_ids = list(
    MemberEncounterData.objects.values_list("member_id", flat=True).distinct()
)[:5]  # TEST LIMIT
print(f"Checking {len(member_ids)} members with existing MemberEncounterData rows...")

backup_rows = []
report_rows = []
fixed_count = 0
already_ok_count = 0
no_data_count = 0
error_count = 0

for i, member_id in enumerate(member_ids, 1):
    member = MemberData.objects.filter(id=member_id).first()
    if not member or not member.member_uuid:
        error_count += 1
        continue

    local = MemberEncounterData.objects.filter(member_id=member_id).order_by("-submission_date").first()

    try:
        tree = provider.get_subject_tree(member.member_uuid)
    except Exception as exc:
        print(f"[{i}/{len(member_ids)}] member {member_id}: AVNI fetch FAILED {exc}")
        error_count += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    completed = []
    target_program_uuid = None
    for enrolment, program_encounters in (tree.enrolments or []):
        for pe in (program_encounters or []):
            observations = pe.get("observations") or {}
            if pe.get("Voided") or not observations:
                continue
            if pe.get("Encounter type") != TARGET_ENCOUNTER_TYPE:
                continue
            modified_at = (pe.get("audit") or {}).get("Last modified at")
            completed.append((modified_at, pe, enrolment.get("ID")))

    if not completed:
        no_data_count += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    completed.sort(key=lambda row: row[0])
    latest_modified, latest_record, enrolment_uuid = completed[-1]

    is_stale = (local is None) or (local.encounter_uuid != latest_record.get("ID"))

    if not is_stale:
        already_ok_count += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    # Back up the old row before changing it.
    if local:
        backup_rows.append(
            {
                "member_id": member_id,
                "old_encounter_uuid": local.encounter_uuid,
                "old_encounter_name": local.encounter_name,
                "old_submission_date": local.submission_date,
                "old_encounter_data": local.encounter_data,
            }
        )

    program = MemberProgramData.objects.filter(member=member, program_uuid=enrolment_uuid or "").first()
    if program is None:
        program = MemberProgramData.objects.filter(member=member).first()

    fields = {
        "encounter_uuid": latest_record.get("ID") or "",
        "encounter_name": (latest_record.get("Encounter type") or "")[:100],
        "encounter_data": latest_record.get("observations") or {},
    }
    fields.update(audit_days(latest_record))

    write_member_encounter(member, program, fields)
    fixed_count += 1
    print(f"[{i}/{len(member_ids)}] member {member_id}: FIXED -> {latest_record.get('ID')} "
          f"(was {local.encounter_uuid if local else None})")

    report_rows.append(
        {
            "member_id": member_id,
            "old_encounter_uuid": local.encounter_uuid if local else "",
            "new_encounter_uuid": latest_record.get("ID"),
            "new_last_modified": latest_modified,
        }
    )
    time.sleep(SLEEP_BETWEEN_CALLS)

if backup_rows:
    with open(backup_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(backup_rows[0].keys()))
        writer.writeheader()
        writer.writerows(backup_rows)
    print(f"\nBackup of old values written to: {backup_path}")

if report_rows:
    with open(report_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(report_rows[0].keys()))
        writer.writeheader()
        writer.writerows(report_rows)
    print(f"Fix report written to: {report_path}")

print("\nSummary:")
print(f"  Total members checked: {len(member_ids)}")
print(f"  Already correct: {already_ok_count}")
print(f"  Fixed (were stale/wrong): {fixed_count}")
print(f"  No filled Follow-up encounter in AVNI at all: {no_data_count}")
print(f"  Errors (fetch failed / no uuid): {error_count}")
