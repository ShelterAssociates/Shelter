"""Fixes written for one specific data problem each, kept for reference.

Both have been run already. They are here because the next odd fix is usually a
variation on one of them, not because they are meant to be run again as they
are. Both read a sqlite run file (see tracker) and write to live AVNI.
"""

from avni import paths
from avni.client import AvniError, client
from developer_scripts import tracker
from developer_scripts.payload import subject_put_body

# Members had been stored under concept uuids instead of names in this group.
MEMBER_COUNT_KEYS = {
    "088fa808-7013-4f4b-8e1b-80c2fc77add0": "Number of Children/Girls",
    "399d35e0-d496-49b1-a13c-65510cee632d": "Number of Male members",
    "9f35ecab-41af-4abc-b97c-08817ebacdba": "Number of Female members",
}
MEMBER_COUNT_GROUP = "Total Number of Members"
ACTIVITY_CONCEPT = "Activity conducted for project ?"


def fill_missing_locations(db_path, table="missing_location"):
    """Subjects registered without coordinates: set them, and name the member-count keys.

    Needs `latitude` and `longitude` columns in the run file.
    """
    api = client()
    connection = tracker.connect(db_path)
    rows = tracker.pending(connection, table)
    print("{} row(s) to process".format(len(rows)))

    for row in rows:
        uuid = str(row.get("uuid") or "").strip()
        try:
            fetched = api.get_json(paths.subject(uuid))
        except AvniError as exc:
            print("[{}] not fetched: {}".format(uuid, exc))
            tracker.set_status(connection, table, uuid, tracker.FETCH_FAILED)
            connection.commit()
            continue

        body = subject_put_body(fetched)
        body["Registration location"] = {"x": row["latitude"], "y": row["longitude"]}
        body["observations"] = named_member_counts(body["observations"])
        tracker.set_status(connection, table, uuid, write(api, uuid, body))
        connection.commit()
    connection.close()


def named_member_counts(observations):
    """Move the member counts off their concept uuids and onto their names."""
    group = dict(observations.get(MEMBER_COUNT_GROUP) or {})
    if not group:
        return observations
    for uuid, name in MEMBER_COUNT_KEYS.items():
        if uuid in group:
            group[name] = group.pop(uuid)
    updated = dict(observations)
    updated[MEMBER_COUNT_GROUP] = group
    return updated


def fill_mobilization_project(db_path, table="mobilization"):
    """Set the project an activity was conducted for, leaving records that already have one.

    Needs a column named after ACTIVITY_CONCEPT in the run file.
    """
    api = client()
    connection = tracker.connect(db_path)
    rows = tracker.pending(connection, table)
    print("{} row(s) to process".format(len(rows)))

    for row in rows:
        uuid = str(row.get("uuid") or "").strip()
        try:
            fetched = api.get_json(paths.subject(uuid))
        except AvniError as exc:
            print("[{}] not fetched: {}".format(uuid, exc))
            tracker.set_status(connection, table, uuid, tracker.FETCH_FAILED)
            connection.commit()
            continue

        if (fetched.get("observations") or {}).get(ACTIVITY_CONCEPT):
            print("[{}] already has a project, left alone".format(uuid))
            continue

        body = subject_put_body(fetched)
        body["observations"][ACTIVITY_CONCEPT] = row[ACTIVITY_CONCEPT]
        tracker.set_status(connection, table, uuid, write(api, uuid, body))
        connection.commit()
    connection.close()


def write(api, uuid, body):
    response = api.put(paths.subject(uuid), body)
    if response.status_code != 200:
        print("[{}] write failed: {} {}".format(uuid, response.status_code, response.text[:300]))
        return tracker.WRITE_FAILED
    print("[{}] updated".format(uuid))
    return tracker.WRITTEN
