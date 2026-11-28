"""AVNI records in a JSON-lines file, so a repair can run where AVNI must not be called.

`export` (run where AVNI is reachable) fetches records one by one, at the shared
client's pace, and appends one line per record: {"kind", "id", "record"} or
{"kind", "id", "missing": status}. It resumes from the lines already written.
`load` (run anywhere, production included) feeds the bundle through the normal
sync (survey.connector.sync_record) with FileApi as the only AVNI there is, so
every write goes through the same writers as the nightly sync.
"""

import csv
import json
import os
from collections import Counter

from django.db import transaction

from avni import paths
from avni.client import AvniError, client, use_client
from avni.provider import AvniProvider, retrying
from graphs.models import HouseholdData, MemberProgramData
from survey import connector, duplicates
from survey.store import SyncContext, parse_moment

PATHS = {"subject": paths.subject, "enrolment": paths.program_enrolment, "program_encounter": paths.program_encounter}
HOUSEHOLD_TYPES = ("Household", "Structure", "Detailed Socio Economic Survey")
LOAD_ORDER = ("household", "member", "enrolment", "program_encounter")


class DryRun(Exception):
    pass


def read_ids(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return [(row["kind"], row["uuid"]) for row in csv.DictReader(handle) if row.get("uuid")]


def read_bundle(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def export(ids_path, out_path, api=None, out=print):
    """Fetch every (kind, uuid) not yet in the bundle and append it. Returns counts."""
    api = api or client()
    done = {(line["kind"], line["id"]) for line in read_bundle(out_path)}
    wanted = [item for item in read_ids(ids_path) if item not in done]
    counts = Counter()
    with open(out_path, "a", encoding="utf-8") as handle:
        for number, (kind, uuid) in enumerate(wanted, 1):
            path = PATHS[kind](uuid)
            try:
                line = {"kind": kind, "id": uuid, "record": retrying(lambda: api.get_json(path), label=path)}
                counts["fetched"] += 1
            except AvniError as exc:
                line = {"kind": kind, "id": uuid, "missing": exc.status_code}
                counts["missing"] += 1
            handle.write(json.dumps(line) + "\n")
            if number % 500 == 0:
                handle.flush()
                out("{} of {} fetched".format(number, len(wanted)))
    out("Fetched {}, missing in AVNI {}, already in the bundle {}.".format(
        counts["fetched"], counts["missing"], len(done)))
    return counts


class FileApi(object):
    """The bundle as a read-only AVNI: records by id, empty lists, 404 for anything else."""

    def __init__(self, records):
        self.records = records
        self.calls = []

    def get_json(self, path, timeout=None):
        self.calls.append(path)
        for kind, build in PATHS.items():
            prefix = build("")
            if path.startswith(prefix) and (kind, path[len(prefix):]) in self.records:
                return json.loads(json.dumps(self.records[(kind, path[len(prefix):])]))
        raise AvniError(404, path, "not in the bundle")

    def iter_pages(self, path, timeout=None):
        yield []


def load_group(kind, record):
    if kind != "subject":
        return kind
    return "household" if record.get("Subject type") in HOUSEHOLD_TYPES else "member"


def older_than_stored(record):
    """An enrolment older than the one already stored for its member (one row per member)."""
    started = parse_moment(record.get("Enrolment datetime"))
    stored = (MemberProgramData.objects.filter(member__member_uuid=record.get("Subject ID"))
              .exclude(program_uuid=record.get("ID")).values_list("created_date", flat=True).first())
    return bool(started and stored and stored > started.date())


def link_households(links):
    """Stamp the AVNI id on rows that have none, matched by slum and number. Returns rows stamped."""
    from survey.identity import household_number_from

    wanted = {(line["slum_id"], household_number_from(line["number"])): line["uuid"] for line in links}
    stamped = 0
    rows = HouseholdData.objects.filter(slum_id__in={slum for slum, number in wanted}).only("id", "slum_id", "household_number", "rhs_data")
    for row in rows.iterator():
        uuid = wanted.get((row.slum_id, household_number_from(row.household_number)))
        data = row.rhs_data or {}
        if uuid and not data.get("rhs_uuid"):
            data["rhs_uuid"] = uuid
            HouseholdData.objects.filter(id=row.id).update(rhs_data=data)
            stamped += 1
    return stamped


def load(path, apply=False, report="bundle_load_report.csv", out=print):
    """Load a bundle through the normal sync, offline. Dry run unless `apply`. Returns counts."""
    everything = read_bundle(path)
    groups = [line for line in everything if line.get("kind") == "duplicate"]
    links = [line for line in everything if line.get("kind") == "link"]
    lines = [line for line in everything if "record" in line]
    records = {(line["kind"], line["id"]): line["record"] for line in lines}
    lines.sort(key=lambda line: LOAD_ORDER.index(load_group(line["kind"], line["record"])))
    api = FileApi(records)
    counts, results = Counter(), []
    use_client(api)
    try:
        with transaction.atomic():
            context = SyncContext(AvniProvider(api=api))
            for line in lines:
                kind, record = line["kind"], line["record"]
                if kind == "enrolment" and older_than_stored(record):
                    result = "older than stored"
                else:
                    result = "saved" if connector.sync_record(kind, record, context) else "not saved"
                counts[result] += 1
                results.append((kind, line["id"], record.get("Subject type") or "", result))
            counts["linked"] = link_households(links) if links else 0
            for group in groups:
                if group.get("dup_kind", "household") == "household":
                    saved = duplicates.remember_household("avni", group["slum_id"], group.get("city_id"), group["number"], group["ids"])
                else:
                    saved = duplicates.remember("avni", group["dup_kind"], group["key"], group["ids"], slum_id=group["slum_id"],
                                                city_id=group.get("city_id"), household_number=group.get("number", ""),
                                                details=group.get("details") or {})
                if group.get("in_mail") is False and saved.in_mail:
                    saved.in_mail = False
                    saved.save(update_fields=["in_mail"])
                counts["duplicate groups"] += 1
            if not apply:
                raise DryRun()
    except DryRun:
        pass
    finally:
        use_client(None)
    with open(report, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kind", "id", "subject_type", "result"])
        writer.writerows(results)
    out("{} records: {}.".format(len(lines), ", ".join("{} {}".format(n, r) for r, n in sorted(counts.items()))))
    out("Report: {}".format(report))
    out("Written." if apply else "Dry run: nothing written. Run again with --apply to write.")
    return counts
