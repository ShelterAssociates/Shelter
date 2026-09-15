"""The AVNI sync console: queue syncs, dry-run counts, bulk updates, run history."""

import json
import os
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from openpyxl import Workbook

from avni import excel, metadata
from avni.client import AvniError
from avni.locations import mapped_slum_ids
from avni.models import AvniForm
from avni_console import catalog
from avni_console.models import BulkUpdate
from avni_console.permissions import can_write_avni, console_required, write_required
from avni_console.services import dry_run, headers, schedule
from graphs.jobs.dashboard_update import ACTIVE_CITY_NAMES
from master.models import City, Slum
from notification.models import JobRequest
from notification.services import queue

DASHBOARD_JOB = "dashboard_update"
BULK_JOB = "avni_bulk_update"
PREVIEW_ROWS = 10


def limits():
    return {
        "max_rows": getattr(settings, "AVNI_BULK_MAX_ROWS", 50),
        "workers": getattr(settings, "AVNI_BULK_WORKERS", 1),
        "dashboard_hour": getattr(settings, "AVNI_DASHBOARD_QUEUE_HOUR", 1),
    }


def request_payload(request):
    if request.content_type == "application/json":
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except ValueError:
            return {}
    return {key: request.POST.getlist(key) if len(request.POST.getlist(key)) > 1 else request.POST.get(key) for key in request.POST}


# -- console home -------------------------------------------------------------

@login_required
@console_required
@require_GET
def index(request):
    slums = Slum.objects.filter(id__in=mapped_slum_ids()).order_by("name").values("id", "name")
    cities = City.objects.filter(name__city_name__in=ACTIVE_CITY_NAMES).order_by("name__city_name")
    context = {
        "jobs": catalog.JOBS,
        "slums": list(slums),
        "cities": [(city.id, city.name.city_name) for city in cities],
        "subject_types": ["Household", "Structure"],
        "encounter_types": catalog.DIRECT_ENCOUNTER_TYPES,
        "limits": limits(),
        "can_write": can_write_avni(request.user),
        "cache_stale": metadata.cache_is_stale(),
        "recent": own_requests(request.user)[:8],
    }
    return render(request, "avni_console/index.html", context)


@login_required
@console_required
@require_POST
def dry_run_rhs(request):
    data = request_payload(request)
    try:
        params = catalog.build_params("rhs_sync", data)
    except catalog.ParamError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if not params.get("from_date"):
        return JsonResponse({"error": "A from date is required for a dry run."}, status=400)
    try:
        result = dry_run.count_households(params["subject_types"], params["from_date"])
    except AvniError as exc:
        return JsonResponse({"error": "AVNI did not answer: {}".format(exc)}, status=502)
    return JsonResponse(result)


@login_required
@console_required
@require_POST
def queue_job(request, job_key):
    job = catalog.BY_KEY.get(job_key)
    if job is None:
        raise Http404("Unknown job")
    try:
        params = catalog.build_params(job_key, request_payload(request))
    except catalog.ParamError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    if job.scheduled:
        when = schedule.next_run_at(limits()["dashboard_hour"])
        job_request = queue.enqueue(job_key, params, request.user, scheduled_for=when, dedupe_key=schedule.slot_key(job_key, when))
        message = "Queued. It will run tonight at {} IST; check the dashboards tomorrow morning.".format(
            timezone.localtime(when).strftime("%H:%M"))
        return JsonResponse({"status": "queued", "id": job_request.pk, "message": message})

    if duplicate_pending(job_key, params, request.user):
        return JsonResponse({"error": "You already have this exact request queued or running. See My runs."}, status=409)
    job_request = queue.enqueue(job_key, params, request.user)
    return JsonResponse({
        "status": "queued", "id": job_request.pk,
        "message": "Queued as run #{}. It starts within two minutes; you will get an email when it finishes.".format(job_request.pk),
    })


def duplicate_pending(job_key, params, user):
    return any(row.params == params for row in queue.pending(job_key, user))


# -- runs ---------------------------------------------------------------------

def own_requests(user):
    rows = JobRequest.objects.select_related("job_run", "requested_by")
    if not user.is_superuser:
        rows = rows.filter(requested_by=user)
    return rows


def visible_request(request, pk):
    job_request = get_object_or_404(own_requests(request.user), pk=pk)
    return job_request


@login_required
@console_required
@require_GET
def runs(request):
    requests_ = list(own_requests(request.user)[:200])
    for job_request in requests_:
        job_request.describe = catalog.describe(job_request.job_key, job_request.params)
        job_request.title = job_title(job_request.job_key)
    bulks = BulkUpdate.objects.select_related("form", "job_request")
    if not request.user.is_superuser:
        bulks = bulks.filter(requested_by=request.user)
    return render(request, "avni_console/runs.html", {"requests": requests_, "bulks": list(bulks[:100])})


def job_title(job_key):
    job = catalog.BY_KEY.get(job_key)
    if job:
        return job.title
    return "Bulk update into AVNI" if job_key == BULK_JOB else job_key.replace("_", " ")


@login_required
@console_required
@require_GET
def run_detail(request, pk):
    job_request = visible_request(request, pk)
    run = job_request.job_run
    steps = list(run.steps.prefetch_related("city_stats")) if run else []
    bulk = BulkUpdate.objects.filter(job_request=job_request).first()
    context = {
        "job_request": job_request, "run": run, "steps": steps, "bulk": bulk,
        "title": job_title(job_request.job_key),
        "describe": catalog.describe(job_request.job_key, job_request.params),
        "has_detail_file": bool(run and run.detail_file_path and os.path.exists(run.detail_file_path)),
        "has_changes": bool(bulk and bulk.result_file_path and os.path.exists(bulk.result_file_path)),
    }
    return render(request, "avni_console/run_detail.html", context)


@login_required
@console_required
@require_GET
def run_detail_file(request, pk):
    job_request = visible_request(request, pk)
    run = job_request.job_run
    if not run or not run.detail_file_path or not os.path.exists(run.detail_file_path):
        raise Http404("No detail file for this run")
    return FileResponse(open(run.detail_file_path, "rb"), as_attachment=True, filename=os.path.basename(run.detail_file_path))


@login_required
@console_required
@require_GET
def run_changes_csv(request, pk):
    job_request = visible_request(request, pk)
    bulk = BulkUpdate.objects.filter(job_request=job_request).first()
    if not bulk or not bulk.result_file_path or not os.path.exists(bulk.result_file_path):
        raise Http404("No change list for this run")
    return FileResponse(open(bulk.result_file_path, "rb"), as_attachment=True, filename="changes-{}.csv".format(bulk.pk))


# -- form metadata for the picker --------------------------------------------

def form_json(form):
    return {"form_id": form.pk, "uuid": form.uuid, "name": form.name} if form else None


@login_required
@write_required
@require_GET
def levels_json(request):
    subject_type = request.GET.get("subject_type", "")
    levels = metadata.levels_for(subject_type)
    return JsonResponse({
        "subject_type": subject_type,
        "registration": form_json(levels["registration"]),
        "enrolments": [{"program": program, **form_json(form)} for program, form in levels["enrolments"]],
        "program_encounters": [{"program": program, "encounter_type": kind, **form_json(form)} for program, kind, form in levels["program_encounters"]],
        "encounters": [{"encounter_type": kind, **form_json(form)} for kind, form in levels["encounters"]],
    })


@login_required
@write_required
@require_GET
def questions_json(request, pk):
    form = get_object_or_404(AvniForm, pk=pk)
    questions = [
        {"question_name": q.question_name, "concept_name": q.concept_name, "data_type": q.data_type,
         "multi": q.is_multi_select, "answers": q.answers or [], "mandatory": q.is_mandatory,
         "group": q.group_name, "supported": q.data_type not in headers.UNSUPPORTED_TYPES}
        for q in metadata.questions_for(form)
    ]
    return JsonResponse({"form": form_json(form), "questions": questions, "reserved": sorted(headers.reserved_for(form)),
                         "fetched_on": form.fetched_on.isoformat()})


@login_required
@write_required
@require_GET
def template_xlsx(request, pk):
    form = get_object_or_404(AvniForm, pk=pk)
    book = Workbook()
    sheet = book.active
    sheet.title = "update"
    concepts = [q.concept_name for q in metadata.questions_for(form) if q.data_type not in headers.UNSUPPORTED_TYPES]
    sheet.append(["uuid"] + concepts + ["Voided"])
    buffer = BytesIO()
    book.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="avni-update-template-{}.xlsx"'.format(form.pk)
    return response


# -- bulk update flow ---------------------------------------------------------

@login_required
@write_required
def bulk_new(request):
    context = {"subject_types": metadata.subject_types(), "limits": limits(), "cache_stale": metadata.cache_is_stale(), "error": ""}
    if request.method != "POST":
        return render(request, "avni_console/bulk_new.html", context)
    try:
        bulk = create_bulk_update(request)
    except ValueError as exc:
        context["error"] = str(exc)
        return render(request, "avni_console/bulk_new.html", context)
    return redirect("avni_console:bulk_preview", pk=bulk.pk)


def create_bulk_update(request):
    subject_type = request.POST.get("subject_type", "").strip()
    level = request.POST.get("level", "registration")
    program = request.POST.get("program", "").strip()
    encounter_type = request.POST.get("encounter_type", "").strip()
    upload = request.FILES.get("file")
    if not upload:
        raise ValueError("Choose an .xlsx file.")
    if not upload.name.lower().endswith((".xlsx", ".xlsm")):
        raise ValueError("Only .xlsx files are accepted (save the sheet as Excel Workbook).")
    try:
        form = metadata.form_for(subject_type, level, program=program, encounter_type=encounter_type)
    except ValueError as exc:
        raise ValueError(str(exc))
    if form is None:
        raise ValueError("No form in AVNI for {} / {} {} {}. Refresh the form cache if it was added recently.".format(
            subject_type, level, program, encounter_type).replace("  ", " "))

    bulk = BulkUpdate(requested_by=request.user, form=form, subject_type=subject_type, level=level, program=program,
                      encounter_type=encounter_type, original_name=upload.name[:300])
    bulk.file.save(upload.name, upload)
    try:
        header_list, rows = checked_rows(bulk.file.path)
    except ValueError:
        bulk.file.delete(save=False)
        bulk.delete()
        raise
    bulk.headers = header_list
    bulk.header_map = {}
    bulk.row_count = len(rows)
    bulk.save()
    return bulk


def checked_rows(path):
    """Headers and rows of an upload, or ValueError with the message to show the user."""
    try:
        header_list, rows = excel.read_rows(path)
    except Exception as exc:
        raise ValueError("The file could not be read as a spreadsheet: {}".format(exc))
    max_rows = limits()["max_rows"]
    if len(rows) > max_rows:
        raise ValueError("This file has {} rows; the limit here is {} rows per file. For larger updates ask the developer, "
                         "who can run it from the shell without the limit.".format(len(rows), max_rows))
    if not any(headers.normalize(h) in headers.ID_HEADERS for h in header_list):
        raise ValueError("The first row must contain a 'uuid' column.")
    if not rows:
        raise ValueError("The file has no data rows.")
    return header_list, rows


def own_bulk(request, pk):
    bulk = get_object_or_404(BulkUpdate.objects.select_related("form", "job_request"), pk=pk)
    if bulk.requested_by_id != request.user.id and not request.user.is_superuser:
        raise PermissionDeniedForBulk()
    return bulk


class PermissionDeniedForBulk(Exception):
    pass


@login_required
@write_required
def bulk_preview(request, pk):
    try:
        bulk = own_bulk(request, pk)
    except PermissionDeniedForBulk:
        return HttpResponseForbidden("Not your upload.")
    header_map = dict(bulk.header_map or {})
    message = ""
    if request.method == "POST":
        header_map.update(chosen_from_post(request.POST))
        bulk.header_map = header_map
        bulk.save(update_fields=["header_map"])
    resolutions = headers.resolve_headers(bulk.form, bulk.headers or [], header_map)
    problems = headers.problems(resolutions)
    pending_run = bulk.job_request if bulk.job_request and bulk.job_request.is_pending else None

    if request.method == "POST" and request.POST.get("action") in ("dry_run", "apply"):
        if problems:
            message = "Fix the columns first: " + " ".join(problems)
        elif pending_run:
            message = "This upload is already queued (run #{}). Wait for it to finish.".format(pending_run.pk)
        else:
            dry = request.POST["action"] == "dry_run"
            job_request = queue.enqueue(BULK_JOB, {"bulk_update_id": bulk.pk, "dry_run": dry}, request.user)
            bulk.job_request = job_request
            bulk.status = "queued"
            bulk.dry_run = dry
            bulk.save()
            return redirect("avni_console:bulk_detail", pk=bulk.pk)

    header_list, rows = excel.read_rows(bulk.file.path)
    context = {
        "bulk": bulk, "resolutions": resolutions, "problems": problems, "message": message,
        "can_run": not problems and not pending_run, "pending_run": pending_run,
        "preview_headers": header_list, "preview_rows": [[row.get(h) for h in header_list] for row in rows[:PREVIEW_ROWS]],
        "questions": [q.concept_name for q in metadata.questions_for(bulk.form) if q.data_type not in headers.UNSUPPORTED_TYPES],
        "limits": limits(),
    }
    return render(request, "avni_console/bulk_preview.html", context)


def chosen_from_post(post):
    chosen = {}
    for key in post:
        if key.startswith("map__"):
            value = post.get(key, "").strip()
            if value:
                chosen[key[len("map__"):]] = value
    return chosen


@login_required
@write_required
@require_GET
def bulk_detail(request, pk):
    try:
        bulk = own_bulk(request, pk)
    except PermissionDeniedForBulk:
        return HttpResponseForbidden("Not your upload.")
    run = bulk.job_request.job_run if bulk.job_request else None
    context = {
        "bulk": bulk, "job_request": bulk.job_request, "run": run,
        "has_changes": bool(bulk.result_file_path and os.path.exists(bulk.result_file_path)),
        "can_write": can_write_avni(request.user),
    }
    return render(request, "avni_console/bulk_detail.html", context)
