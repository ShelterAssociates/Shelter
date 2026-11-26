"""
WRITE script: re-syncs exactly the households and members in query_result.csv
(the 279 member/household pairs pulled directly from AVNI's raw DB), using
AVNI's live API - not a full historical resync of everything.

Two parts:

1. Households - uses the existing, unmodified production sync code
   (avni.sync.by_uuid.sync_by_uuid) to fetch+save each household_uuid. This
   handles the 93 households that don't exist in our DB yet, and refreshes
   the 186 that already do.

2. Members - avni.sync.members.member_household_number() has a real bug: it
   only handles record["Groups"][0] as a dict, but AVNI actually returns
   Groups as a list of bare household-uuid strings, so it always returns None
   for these members (confirmed: member 72386's Groups == ["516a3b75-...-
   f25dfa66371f"], exactly the household_uuid we already have from the raw
   AVNI DB). Rather than monkeypatching or editing that function in the repo,
   this script fetches each member subject fresh from AVNI and writes it with
   the SAME fields save_member_from_record() would write, except
   household_number comes from query_result.csv (the known-correct value)
   instead of the buggy parse. This does not change any file in the repo.

This DOES write to the database (HouseholdData, MemberData) and makes live
calls to the AVNI API. Run it only when you're ready to apply the fix.

Run on production with:

    python manage.py shell < resync_affected_subjects.py

Expects query_result.csv (City, Slum, household_uuid, household_number,
member_uuid, member_first_name, member_last_name, date_of_birth, gender,
household_voided, member_voided) in the current directory.
"""
import csv
import time

from avni.client import AvniError, client
from avni.sync.by_uuid import sync_by_uuid
from avni.sync.households import fetch_subject
from avni.sync.members import write_member, record_day, audit_days, GENDER_CODES
from master.models import Slum

SLEEP_BETWEEN_CALLS = 0.2

with open("query_result.csv") as f:
    rows = list(csv.DictReader(f))

print(f"Loaded {len(rows)} rows from query_result.csv")

# ---- Part 1: households ----
household_uuids = sorted({r["household_uuid"].strip() for r in rows})
print(f"\nSyncing {len(household_uuids)} household subjects...")
household_counts = sync_by_uuid("subject", household_uuids, subject_type="Household")
print(f"Household sync result: {household_counts}")

# ---- Part 2: members, with corrected household_number ----
api = client()
member_results = {"saved": 0, "skipped": 0, "failed": 0}

for i, row in enumerate(rows, 1):
    member_uuid = row["member_uuid"].strip()
    known_household_number = row["household_number"].strip()

    try:
        record = fetch_subject(member_uuid, api)
    except AvniError as e:
        print(f"[{i}/{len(rows)}] member {member_uuid}: FETCH FAILED {e}")
        member_results["failed"] += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    if record.get("Voided"):
        print(f"[{i}/{len(rows)}] member {member_uuid}: voided, skipping")
        member_results["skipped"] += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    slum = Slum.objects.filter(name=(record.get("location") or {}).get("Slum")).first()
    if slum is None:
        print(f"[{i}/{len(rows)}] member {member_uuid}: no matching Slum, skipping")
        member_results["skipped"] += 1
        time.sleep(SLEEP_BETWEEN_CALLS)
        continue

    observations = record.get("observations") or {}
    fields = {
        "member_first_name": (observations.get("First name") or record.get("First name") or "")[:100],
        "member_last_name": (observations.get("Last name") or record.get("Last name") or "")[:100],
        "date_of_birth": record_day(record.get("Date of birth") or observations.get("Date of birth")),
        "gender": GENDER_CODES.get(record.get("Gender") or observations.get("Gender"), "3"),
        "household_number": known_household_number or None,
        "member_data": observations,
    }
    fields.update(audit_days(record))

    write_member(slum, member_uuid, fields)
    member_results["saved"] += 1
    print(f"[{i}/{len(rows)}] member {member_uuid}: saved with household_number={known_household_number!r}")
    time.sleep(SLEEP_BETWEEN_CALLS)

print(f"\nMember resync result: {member_results}")
print("\nDone. Re-run find_null_cup_rows_prod.py to confirm these members no longer show up.")
