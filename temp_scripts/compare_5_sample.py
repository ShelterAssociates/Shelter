"""
READ-ONLY: for 5 sample members from remaining_null_cup_detail.csv, fetch
their FULL AVNI tree (subject + enrolments + program encounters, via the same
AvniProvider.get_subject_tree() the real sync code uses) and show it next to
what we have locally, so the two can be compared directly.

Does NOT write/save anything to our DB. Makes live read-only GET calls to
AVNI.

Run on production with:

    python manage.py shell < compare_5_sample.py

Expects remaining_null_cup_detail.csv in the current directory.
"""
import csv

from avni.provider import AvniProvider
from graphs.models import MemberData, MemberEncounterData

EXPECTED_QUESTION = "Did you use cup in the previous menstruation?"

with open("remaining_null_cup_detail.csv") as f:
    rows = list(csv.DictReader(f))[:5]

provider = AvniProvider()

for row in rows:
    member_id = row["member_id"]
    member = MemberData.objects.filter(id=member_id).first()
    print("=" * 90)
    print(f"member_id={member_id}  member_uuid={member.member_uuid if member else 'N/A'}")

    print("\n--- OUR DB ---")
    if member:
        print(f"household_number={member.household_number!r}  slum_id={member.slum_id}")
        print(f"member_data: {member.member_data}")
        encs = MemberEncounterData.objects.filter(member_id=member_id).order_by("-submission_date")
        print(f"{encs.count()} MemberEncounterData row(s):")
        for e in encs:
            print(f"  encounter_uuid={e.encounter_uuid} encounter_name={e.encounter_name!r} "
                  f"submission_date={e.submission_date} encounter_data={e.encounter_data}")
    else:
        print("NOT FOUND locally")

    print("\n--- LIVE AVNI ---")
    if not member or not member.member_uuid:
        print("(no member_uuid to look up)")
        continue

    try:
        tree = provider.get_subject_tree(member.member_uuid)
    except Exception as exc:
        print(f"get_subject_tree FAILED: {exc}")
        continue

    subject = tree.subject
    print(f"subject ID={subject.get('ID')} Voided={subject.get('Voided')} "
          f"location={subject.get('location')}")
    print(f"subject observations: {subject.get('observations')}")

    print(f"{len(tree.enrolments or [])} enrolment(s):")
    for enrolment, program_encounters in (tree.enrolments or []):
        print(f"  enrolment ID={enrolment.get('ID')} Program={enrolment.get('Program')} "
              f"Voided={enrolment.get('Voided')}")
        print(f"  {len(program_encounters or [])} program encounter(s):")
        for pe in (program_encounters or []):
            observations = pe.get("observations") or {}
            has_q = EXPECTED_QUESTION in observations
            modified_at = (pe.get("audit") or {}).get("Last modified at")
            print(f"    - ID={pe.get('ID')} Encounter type={pe.get('Encounter type')!r} "
                  f"Voided={pe.get('Voided')} last_modified={modified_at} "
                  f"has_target_question={has_q} target_value={observations.get(EXPECTED_QUESTION)!r}")
            print(f"      full observations: {observations}")

    print(f"{len(tree.encounters or [])} subject-level encounter(s):")
    for enc in (tree.encounters or []):
        observations = enc.get("observations") or {}
        print(f"    - ID={enc.get('ID')} Encounter type={enc.get('Encounter type')!r} "
              f"observations={observations}")
    print()
