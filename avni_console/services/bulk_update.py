"""Apply an uploaded spreadsheet to AVNI, one record per row.

Registry job `avni_bulk_update` (params: bulk_update_id, dry_run, workers) and
`apply_file()` for the developer's shell. Every row ends in changes.csv
(uuid, field, old, new, status, error) next to the job's detail file.
"""

import csv
import logging
import os
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.files import File
from django.db import close_old_connections
from django.utils import timezone

from avni import excel
from avni.client import AvniError, client
from avni.models import AvniForm
from avni_console.models import BulkUpdate
from avni_console.services import headers, payload, values
from notification.services import reporting

logger = logging.getLogger(__name__)

Line = namedtuple("Line", "uuid field old new status error")
RowResult = namedtuple("RowResult", "uuid lines failed error")

CSV_COLUMNS = ("uuid", "field", "old", "new", "status", "error")


class Plan(object):
    """Resolved columns of one upload: which header feeds which concept / top-level field."""

    def __init__(self, bulk, resolutions):
        self.bulk = bulk
        self.id_header = next(r.header for r in resolutions if r.kind == "id")
        self.questions = {r.header: r.question for r in resolutions if r.question is not None and r.kind in headers.OK_KINDS}
        self.reserved = {r.header: r.concept_name for r in resolutions if r.kind == "reserved"}

    @property
    def concepts(self):
        return [question.concept_name for question in self.questions.values()]


def run(recorder, params=None):
    params = params or {}
    bulk = BulkUpdate.objects.filter(pk=params.get("bulk_update_id")).first()
    if bulk is None:
        raise ValueError("bulk_update_id {} does not exist".format(params.get("bulk_update_id")))
    dry_run = bool(params.get("dry_run", True))
    workers = int(params.get("workers") or getattr(settings, "AVNI_BULK_WORKERS", 1))
    mark(bulk, "running", dry_run=dry_run)
    recorder.set_window("{}{} rows from {}".format("DRY RUN: " if dry_run else "", bulk.row_count, bulk.original_name))

    with recorder.step("resolve") as step:
        try:
            plan, rows = prepare(bulk)
        except Exception as exc:
            step.note_error("{}: {}".format(type(exc).__name__, exc))
            mark(bulk, "failed", summary="Columns could not be resolved: {}".format(exc))
            return

    with recorder.step("update", loggers=[__name__]) as step:
        step.expect(len(rows))
        results = process_rows(bulk, plan, rows, dry_run, workers)
        lines = record_results(results)

    path = write_changes(bulk, recorder, lines)
    bulk.result_file_path = path
    mark(bulk, "done", summary=summarize(lines, dry_run))


def prepare(bulk):
    """(Plan, rows) or raise ValueError listing the header problems."""
    header_list, rows = excel.read_rows(bulk.file.path)
    resolutions = headers.resolve_headers(bulk.form, header_list, bulk.header_map or {})
    problems = headers.problems(resolutions)
    if problems:
        raise ValueError("; ".join(problems))
    return Plan(bulk, resolutions), rows


def process_rows(bulk, plan, rows, dry_run, workers):
    api = client()
    if workers <= 1:
        return [process_row(bulk, plan, row, api, dry_run) for row in rows]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda row: process_row_in_thread(bulk, plan, row, api, dry_run), rows))


def process_row_in_thread(bulk, plan, row, api, dry_run):
    try:
        return process_row(bulk, plan, row, api, dry_run)
    finally:
        close_old_connections()


def process_row(bulk, plan, row, api, dry_run):
    """Fetch, diff, and (unless dry run) write one row. Never raises."""
    uuid = str(row.get(plan.id_header) or "").strip()
    if not uuid:
        return RowResult("", [Line("", "", "", "", "failed", "row has no uuid")], True, "row has no uuid")
    try:
        fetched = api.get_json(payload.PATH_BUILDERS[bulk.form.form_type](uuid))
        changes, top_level = row_changes(plan, row)
        changes = payload.real_changes(bulk.form, fetched, changes)
        top_level = {field: value for field, value in top_level.items() if not payload.same(fetched.get(field), value)}
    except (AvniError, values.CellError) as exc:
        return RowResult(uuid, [Line(uuid, "", "", "", "failed", str(exc))], True, str(exc))
    if not changes and not top_level:
        return RowResult(uuid, [Line(uuid, "", "", "", "unchanged", "")], False, "")

    old = payload.current_values(bulk.form, fetched, list(changes), list(top_level))
    lines = [Line(uuid, field, show(old.get(field)), show(value), "would_update" if dry_run else "updated", "")
             for field, value in list(changes.items()) + list(top_level.items())]
    if dry_run:
        return RowResult(uuid, lines, False, "")
    error = send_write(bulk, uuid, fetched, changes, top_level, api)
    if error:
        return RowResult(uuid, [line._replace(status="failed", error=error) for line in lines], True, error)
    return RowResult(uuid, lines, False, "")


def row_changes(plan, row):
    changes, top_level = {}, {}
    for header, question in plan.questions.items():
        value = values.coerce(row.get(header), question)
        if value is not values.NO_CHANGE:
            changes[question.concept_name] = value
    for header, field in plan.reserved.items():
        value = values.coerce_reserved(field, row.get(header))
        if value is values.NO_CHANGE:
            continue
        if value is values.CLEAR:
            raise values.CellError("'{}' cannot be cleared".format(field))
        top_level[field] = value
    return changes, top_level


def send_write(bulk, uuid, fetched, changes, top_level, api):
    """Empty string on success, otherwise the server's message."""
    write = payload.build_write(bulk.form, bulk.subject_type, uuid, fetched, changes, top_level)
    try:
        response = api.patch(write.path, write.body) if write.method == "PATCH" else api.put(write.path, write.body)
    except Exception as exc:  # noqa: BLE001 - network failure is a row failure
        return "{}: {}".format(type(exc).__name__, exc)
    if response.status_code >= 300:
        return "AVNI {} {}: {}".format(write.method, response.status_code, (response.text or "")[:300])
    return ""


def record_results(results):
    """Record every row on the active step (main thread) and flatten the csv lines."""
    lines = []
    for result in results:
        with reporting.record(key=result.uuid or None):
            if result.failed:
                reporting.fail(RuntimeError(result.error))
        lines.extend(result.lines)
    return lines


def show(value):
    if value is values.CLEAR:
        return "__CLEAR__"
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item) for item in value)
    if isinstance(value, dict):
        return "; ".join("{}={}".format(key, item) for key, item in value.items())
    return str(value)


def write_changes(bulk, recorder, lines):
    """changes.csv next to the uploaded file, so it outlives the 24 h job-report cleanup."""
    directory = os.path.dirname(bulk.file.path)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "changes-run{}.csv".format(recorder.model.pk))
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_COLUMNS)
        for line in lines:
            writer.writerow(line)
    return path


def summarize(lines, dry_run):
    counts = {}
    for line in lines:
        counts[line.status] = counts.get(line.status, 0) + 1
    rows_failed = len({line.uuid for line in lines if line.status == "failed"})
    changed = counts.get("would_update", 0) + counts.get("updated", 0)
    return "{}{} field change(s), {} row(s) unchanged, {} row(s) failed".format(
        "DRY RUN: " if dry_run else "", changed, counts.get("unchanged", 0), rows_failed
    )


def mark(bulk, status, summary=None, dry_run=None):
    bulk.status = status
    if summary is not None:
        bulk.summary = summary
    if dry_run is not None:
        bulk.dry_run = dry_run
    bulk.save()


def apply_file(path, form_uuid, subject_type, dry_run=True, workers=None, max_rows=None, requested_by=None,
               level="registration", program="", encounter_type=""):
    """Developer shell entry point: same audit trail (BulkUpdate, JobRequest, JobRun, csv, email) as the console.

        python manage.py shell -c "from avni_console.services.bulk_update import apply_file; \\
            apply_file('/path/fix.xlsx', '<form uuid>', 'Household', dry_run=False, workers=4)"
    """
    from notification.services import queue

    form = AvniForm.objects.get(uuid=form_uuid)
    header_list, rows = excel.read_rows(path)
    if max_rows is not None and len(rows) > max_rows:
        raise ValueError("{} rows is over the limit of {}".format(len(rows), max_rows))
    bulk = BulkUpdate(requested_by=requested_by, form=form, subject_type=subject_type, level=level, program=program,
                      encounter_type=encounter_type, original_name=os.path.basename(path), headers=header_list,
                      header_map={}, row_count=len(rows), dry_run=dry_run)
    with open(path, "rb") as handle:
        bulk.file.save(os.path.basename(path), File(handle))
    request = queue.enqueue("avni_bulk_update", {"bulk_update_id": bulk.pk, "dry_run": dry_run, "workers": workers}, requested_by)
    request.status = "running"
    request.started_on = timezone.now()
    request.save()
    bulk.job_request = request
    bulk.status = "queued"
    bulk.save()
    queue.run(request)
    bulk.refresh_from_db()
    return bulk
