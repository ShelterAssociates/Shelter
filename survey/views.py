"""Internal-only slum data version page: superusers only.

Starting a new version freezes a slum's current data into SlumVersionBackup and
opens the next one; the live tables keep serving the old version until the new
version's first household arrives. RIM is decided explicitly, never switched by
the sync. The same page maps several AVNI locations onto one slum, turns a
slum's sync off, and locks its locations against the nightly location refresh.
"""

import os
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from master.models import Slum
from survey import merging, slum_sync, versioning
from survey.models import SlumAlias, SlumDataVersion

PROVIDER = "avni"
CONFIRM_WORD = "START"
MERGE_WORD = "MERGE"


def superuser_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not getattr(request.user, "is_superuser", False):
            return HttpResponseForbidden("Slum data versions are limited to superusers.")
        return view(request, *args, **kwargs)
    return guarded


def lock_locations(slum_id, user):
    """A hand-made mapping must survive the nightly AVNI location refresh."""
    slum_sync.update(slum_id, user=user, alias_locked=True)


def dump_dir():
    path = getattr(settings, "SLUM_MERGE_DUMP_DIR", None) or os.path.join(settings.MEDIA_ROOT, "slum_merges")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def slum_search_index():
    """Flat slum -> full path rows for the search box, filtered in the browser.

    Mirrors the KML upload page's index (component.views.build_slum_search_index)
    but carries the version state instead of applying a city filter, since this
    page is superusers only. values_list, not select_related: three PolygonFields
    would otherwise be transferred and parsed per row.
    """
    rows = (
        Slum.objects.filter(
            electoral_ward__isnull=False, electoral_ward__administrative_ward__isnull=False,
        )
        .order_by("name")
        .values_list(
            "id", "name",
            "electoral_ward__name",
            "electoral_ward__administrative_ward__name",
            "electoral_ward__administrative_ward__city__name__city_name",
        )
    )
    versions = dict(
        SlumDataVersion.objects.order_by("slum_id", "version")
        .values_list("slum_id", "version")
    )
    waiting = set(
        SlumDataVersion.objects.filter(switched_on__isnull=True).values_list("slum_id", flat=True)
    )
    locations = {}
    for slum_id in SlumAlias.objects.filter(provider=PROVIDER).values_list("slum_id", flat=True):
        locations[slum_id] = locations.get(slum_id, 0) + 1
    return [
        {
            "id": sid, "name": name,
            "path": " / ".join(part for part in (city, aw, ew) if part),
            "version": versions.get(sid, 1),
            "waiting": sid in waiting,
            "locations": locations.get(sid, 0),
        }
        for sid, name, ew, aw, city in rows
    ]


def recently_versioned(limit=8):
    """The slums last given a new version, as a shortcut card."""
    rows = (
        SlumDataVersion.objects.select_related("slum")
        .order_by("-created_on")[:limit]
    )
    seen, recent = set(), []
    for row in rows:
        if row.slum_id in seen:
            continue
        seen.add(row.slum_id)
        recent.append({
            "id": row.slum_id, "name": row.slum.name, "version": row.version,
            "waiting": row.switched_on is None, "started_on": row.started_on,
        })
    return recent


@superuser_required
def slum_versions(request, slum_id=None):
    slum = get_object_or_404(Slum, pk=slum_id) if slum_id else None
    context = {
        "slum_search_index": slum_search_index(),
        "recent": recently_versioned(),
        "slum": slum,
        "rim_choices": versioning.RIM_CHOICES,
        "confirm_word": CONFIRM_WORD,
        "merge_word": MERGE_WORD,
    }
    if slum is not None:
        context.update(versioning.describe(slum.id))
        pending = context.get("pending")
        context["missing_backup"] = (
            [table.label for table in versioning.missing_backup_tables(slum.id, pending.version - 1)]
            if pending else []
        )
        context["setting"] = slum_sync.setting_for(slum.id)
        context["merge_candidates"] = [
            row for row in context["slum_search_index"] if row["id"] != slum.id
        ]
    return render(request, "survey/slum_versions.html", context)


@superuser_required
@require_POST
def save_settings(request, slum_id):
    slum_sync.update(
        slum_id,
        user=request.user,
        sync_enabled=bool(request.POST.get("sync_enabled")),
        alias_locked=bool(request.POST.get("alias_locked")),
        note=request.POST.get("note", ""),
    )
    messages.success(request, "Sync settings saved.")
    return redirect("survey:slum_detail", slum_id=slum_id)


@superuser_required
@require_POST
def add_location(request, slum_id):
    external_id = (request.POST.get("external_id") or "").strip()
    external_name = (request.POST.get("external_name") or "").strip()
    if not external_id:
        messages.error(request, "Give the AVNI location uuid.")
        return redirect("survey:slum_detail", slum_id=slum_id)
    taken = SlumAlias.objects.filter(provider=PROVIDER, external_id=external_id).first()
    if taken:
        messages.error(request, "That location is already mapped to slum {}.".format(taken.slum_id))
        return redirect("survey:slum_detail", slum_id=slum_id)
    has_primary = SlumAlias.objects.filter(provider=PROVIDER, slum_id=slum_id, is_primary=True).exists()
    SlumAlias.objects.create(
        slum_id=slum_id, provider=PROVIDER, external_id=external_id,
        external_name=external_name, is_primary=not has_primary,
    )
    lock_locations(slum_id, request.user)
    messages.success(
        request,
        "Location mapped and this slum's locations locked, so the AVNI refresh cannot change them. "
        "It is not the RIM source unless you make it one.",
    )
    return redirect("survey:slum_detail", slum_id=slum_id)


@superuser_required
@require_POST
def remove_location(request, slum_id):
    SlumAlias.objects.filter(
        provider=PROVIDER, slum_id=slum_id, external_id=request.POST.get("external_id"),
    ).delete()
    lock_locations(slum_id, request.user)
    messages.success(request, "Location unmapped, and this slum's locations stay locked.")
    return redirect("survey:slum_detail", slum_id=slum_id)


@superuser_required
@require_POST
def make_primary(request, slum_id):
    try:
        versioning.set_rim_source(slum_id, request.POST.get("external_id"), PROVIDER)
        lock_locations(slum_id, request.user)
        messages.success(request, "RIM source changed and the locations locked. Run the RIM sync to pull from it.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("survey:slum_detail", slum_id=slum_id)


@superuser_required
@require_POST
def start_version(request, slum_id):
    if request.POST.get("confirm", "").strip().upper() != CONFIRM_WORD:
        messages.error(request, "Type {} to confirm.".format(CONFIRM_WORD))
        return redirect("survey:slum_detail", slum_id=slum_id)
    try:
        result = versioning.start_new_version(
            slum_id,
            user=request.user,
            rim_choice=request.POST.get("rim_choice", versioning.RIM_KEEP),
            rim_location=request.POST.get("rim_location") or None,
            note=request.POST.get("note", ""),
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("survey:slum_detail", slum_id=slum_id)
    kept = sum(result["archived"].values())
    messages.success(
        request,
        "Version {} started. {} rows backed up. The live tables keep serving the old version "
        "until the first new household arrives.".format(result["version"].version, kept),
    )
    if result["rim_cleared"]:
        messages.warning(
            request,
            "RIM was cleared ({} rows). The factsheet stays hidden until a RIM sync runs.".format(
                sum(result["rim_cleared"].values())
            ),
        )
    return redirect("survey:slum_detail", slum_id=slum_id)


@superuser_required
@require_POST
def backfill_backup(request, slum_id):
    """Archive anything the waiting version has not backed up yet.

    Needed when a version was started before a table joined the registry, or
    straight through the admin. Only offered while the version is still waiting,
    because the live rows then still are the outgoing version's data.
    """
    pending = versioning.pending_version(slum_id)
    if pending is None:
        messages.error(request, "No version is waiting, so there is nothing safe to back up.")
        return redirect("survey:slum_detail", slum_id=slum_id)
    added = versioning.ensure_backup(slum_id, pending.version - 1)
    if added:
        messages.success(request, "Backed up {}.".format(added))
    else:
        messages.info(request, "Version {} is already fully backed up.".format(pending.version - 1))
    return redirect("survey:slum_detail", slum_id=slum_id)


@superuser_required
@require_POST
def merge_slum(request, slum_id):
    source_id = request.POST.get("source_id")
    if not source_id:
        messages.error(request, "Choose the slum to merge in.")
        return redirect("survey:slum_detail", slum_id=slum_id)
    source_id = int(source_id)
    if request.POST.get("dry_run"):
        report = merging.plan_merge(source_id, int(slum_id))
        messages.info(request, "Dry run - would move: {}, plus {} survey record(s).".format(
            report["moving"] or "nothing", report["records"],
        ))
        if report["unreadable"]:
            messages.error(request, "These tables do not match their models, so run the migrations first: {}".format(
                ", ".join(sorted(report["unreadable"])),
            ))
        if report["blocked"]:
            messages.error(request, "Blocked by existing keys in: {}".format(", ".join(sorted(report["blocked"]))))
        if not report["unreadable"] and not report["blocked"]:
            messages.success(request, "Nothing blocks this merge.")
        return redirect("survey:slum_detail", slum_id=slum_id)
    if request.POST.get("confirm", "").strip().upper() != MERGE_WORD:
        messages.error(request, "Type {} to confirm. This deletes the other slum and cannot be undone.".format(MERGE_WORD))
        return redirect("survey:slum_detail", slum_id=slum_id)
    path = os.path.join(
        dump_dir(), "merge_{}_into_{}_{}.json".format(source_id, slum_id, timezone.now().strftime("%Y%m%d%H%M%S")),
    )
    try:
        moved = merging.merge(
            source_id, int(slum_id), version=versioning.current_number(slum_id), dump_path=path,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("survey:slum_detail", slum_id=slum_id)
    messages.success(request, "Merged and deleted slum {}. Moved {}. Backup written to {}.".format(
        source_id, moved, path,
    ))
    return redirect("survey:slum_detail", slum_id=slum_id)
