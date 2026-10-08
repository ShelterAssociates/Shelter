"""Read one encounter by uuid, for checking what AVNI actually holds.

    from developer_scripts import encounters
    encounters.fetch("f3cdff50-...")
    encounters.observations("f3cdff50-...")
"""

from avni import paths
from avni.client import AvniError, client


def fetch(encounter_uuid, api=None):
    """The raw encounter record, or None when AVNI will not give it."""
    try:
        return (api or client()).get_json(paths.encounter(str(encounter_uuid)))
    except AvniError as exc:
        print("[ENCOUNTER] {} not fetched: {}".format(encounter_uuid, exc))
        return None


def observations(encounter_uuid, api=None):
    return (fetch(encounter_uuid, api) or {}).get("observations") or {}


def summary(encounter_uuid, api=None):
    record = fetch(encounter_uuid, api)
    if record is None:
        return None
    return {
        "uuid": encounter_uuid,
        "encounter_type": record.get("Encounter type"),
        "subject_id": record.get("Subject ID"),
        "voided": bool(record.get("Voided")),
        "audit": record.get("audit") or {},
        "observations": record.get("observations") or {},
    }
