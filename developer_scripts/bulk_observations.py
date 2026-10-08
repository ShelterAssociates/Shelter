"""Set one observation on many records, driven by a sqlite run file.

The run file (see tracker) holds a `uuid` column, a `status` column and the
column carrying each record's new value:

    from developer_scripts import bulk_observations
    bulk_observations.run("/path/changes.db", "changes",
                          concept="Functioning of the structure", column="fs")

`workers` above 1 fetches and writes in parallel; the shared AVNI client makes
every worker use one token and back off on the same throttle. Status is written
from the main thread only, so the sqlite connection stays single-threaded.

This writes to live AVNI. There is no dry run, so check the run file first.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from avni import paths
from avni.client import AvniError, client
from developer_scripts import tracker
from developer_scripts.payload import subject_put_body

RETRY_ATTEMPTS = 3

PATHS = {
    "subject": paths.subject,
    "encounter": paths.encounter,
    "programEnrolment": paths.program_enrolment,
}


def run(db_path, table, concept, column, kind="subject", workers=1, batch_size=100, pause_seconds=5, api=None):
    """Walk the pending rows in batches and report how each one ended."""
    api = api or client()
    connection = tracker.connect(db_path)
    rows = tracker.pending(connection, table)
    print("{} row(s) to process".format(len(rows)))
    counts = {}
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        for result in results_for(batch, concept, column, kind, workers, api):
            tracker.set_status(connection, table, result["uuid"], result["status"])
            counts[result["status"]] = counts.get(result["status"], 0) + 1
        connection.commit()
        print("processed {}/{}".format(min(start + batch_size, len(rows)), len(rows)))
        if pause_seconds and start + batch_size < len(rows):
            time.sleep(pause_seconds)
    connection.close()
    print("written: {}, fetch failed: {}, write failed: {}, errored: {}".format(
        counts.get(tracker.WRITTEN, 0), counts.get(tracker.FETCH_FAILED, 0),
        counts.get(tracker.WRITE_FAILED, 0), counts.get(tracker.ERRORED, 0),
    ))
    return counts


def results_for(batch, concept, column, kind, workers, api):
    if workers <= 1:
        return [guarded(row, concept, column, kind, api) for row in batch]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(guarded, row, concept, column, kind, api) for row in batch]
        return [future.result() for future in as_completed(futures)]


def guarded(row, concept, column, kind, api):
    """One row, retrying network failures; any other error is recorded, never raised."""
    uuid = str(row.get("uuid") or "").strip()
    delay = 1
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return update_one(row, concept, column, kind, api)
        except requests.RequestException as exc:
            if attempt == RETRY_ATTEMPTS:
                print("[{}] gave up after {} attempts: {}".format(uuid, RETRY_ATTEMPTS, exc))
                return {"uuid": uuid, "status": tracker.ERRORED}
            time.sleep(delay)
            delay *= 2
        except Exception as exc:
            print("[{}] errored: {}: {}".format(uuid, type(exc).__name__, exc))
            return {"uuid": uuid, "status": tracker.ERRORED}


def update_one(row, concept, column, kind, api):
    uuid = str(row.get("uuid") or "").strip()
    path = PATHS[kind](uuid)
    try:
        fetched = api.get_json(path)
    except AvniError as exc:
        print("[{}] not fetched: {}".format(uuid, exc))
        return {"uuid": uuid, "status": tracker.FETCH_FAILED}

    body = subject_put_body(fetched) if kind == "subject" else dict(fetched)
    observations = dict(body.get("observations") or {})
    observations[concept] = row[column]
    body["observations"] = observations

    response = api.put(path, body)
    if response.status_code != 200:
        print("[{}] write failed: {} {}".format(uuid, response.status_code, response.text[:300]))
        return {"uuid": uuid, "status": tracker.WRITE_FAILED}
    print("[{}] {} = {!r}".format(uuid, concept, row[column]))
    return {"uuid": uuid, "status": tracker.WRITTEN}
