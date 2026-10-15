"""
READ-ONLY, fast: checks just 5 hardcoded members against live AVNI - no CSV,
no loop over hundreds of rows. Run directly:

    python manage.py shell < check_5_stale.py
"""
from datetime import datetime

from avni.provider import AvniProvider
from graphs.models import MemberData, MemberEncounterData

MEMBER_IDS = [121009, 151177, 72386, 18246, 31826]
EXPECTED_QUESTION = "Did you use cup in the previous menstruation?"


def parse_dt(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ") if value else None


provider = AvniProvider()

for member_id in MEMBER_IDS:
    member = MemberData.objects.filter(id=member_id).first()
    print("=" * 80)
    if not member or not member.member_uuid:
        print(f"member {member_id}: not found / no uuid")
        continue

    local = MemberEncounterData.objects.filter(member_id=member_id).order_by("-submission_date").first()
    print(f"member_id={member_id}")
    print(f"  IN DB: encounter_uuid={local.encounter_uuid if local else None} "
          f"submission_date={local.submission_date if local else None} "
          f"target_value={(local.encounter_data or {}).get(EXPECTED_QUESTION) if local else None}")

    try:
        tree = provider.get_subject_tree(member.member_uuid)
    except Exception as exc:
        print(f"  AVNI fetch failed: {exc}")
        continue

    completed = []
    for _, program_encounters in (tree.enrolments or []):
        for pe in (program_encounters or []):
            observations = pe.get("observations") or {}
            if pe.get("Voided") or not observations or pe.get("Encounter type") != "Menstrual hygiene Follow-up":
                continue
            modified_at = (pe.get("audit") or {}).get("Last modified at")
            completed.append((parse_dt(modified_at), pe.get("ID"), observations, modified_at))

    if not completed:
        print("  AVNI: no completed program encounters")
        continue

    completed.sort(key=lambda x: x[0])
    latest_dt, latest_uuid, latest_obs, latest_raw = completed[-1]
    stale = local is None or local.encounter_uuid != latest_uuid
    print(f"  LATEST IN AVNI: encounter_uuid={latest_uuid} last_modified={latest_raw} "
          f"target_value={latest_obs.get(EXPECTED_QUESTION)}")
    print(f"  {len(completed)} completed encounter(s) in AVNI total -> {'STALE' if stale else 'OK (matches)'}")
