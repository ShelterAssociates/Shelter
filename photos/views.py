"""Internal-only browser and exporter for household photos.

Browse city -> slum -> household, view photos, download one household's photos
instantly, or queue a whole slum for background export delivered by email.
Deliberately separate from the mastersheet: nothing here changes that grid.

Photos come from two eras -- the Kobo backup on local disk and Avni's S3 objects
via signed URLs -- resolved through photos.services.sources so the views don't
care which. See that module for the split.

Viewing and downloading are separate permissions: a city-scoped user may browse
their own city, but only a superuser may pull photos out in bulk.
"""

import json
import logging
import mimetypes
import os
import re
from urllib.parse import quote

from django.contrib.auth.decorators import permission_required
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from graphs.models import HouseholdData
from avni import media as avni_media
from helpers.models import ExportRequest
from helpers.validators import validate_shelter_email
from master.models import City, Slum
from mastersheet.models import ToiletConstruction
from photos.permissions import can_download_photos, can_view_protected_media
from photos.services import collect, export, runner, sources
from photos.utils import (
    financial_year_choices,
    household_number_variants,
    normalize_household_number,
)

logger = logging.getLogger(__name__)

FAMILY_HEAD_KEY = collect.FAMILY_HEAD_KEY


def permitted_cities(user):
    """Cities the user may see, matching Slum.has_permission's group semantics:
    a group named (or suffixed) with the city name grants access to that city."""
    if user.is_superuser:
        return City.objects.order_by("name__city_name")
    group_names = [
        name.split(":")[-1].strip()
        for name in user.groups.values_list("name", flat=True)
    ]
    return City.objects.filter(name__city_name__in=group_names).order_by(
        "name__city_name"
    )


def _slum_or_forbidden(request, slum_id):
    slum = get_object_or_404(Slum, pk=slum_id)
    if not slum.has_permission(request.user):
        return None, HttpResponseForbidden(
            "You do not have permission to access this slum."
        )
    return slum, None


@require_GET
@permission_required("mastersheet.can_view_mastersheet", raise_exception=True)
def photo_index(request):
    """City/slum picker, plus a box for looking one encounter up by UUID."""
    cities = permitted_cities(request.user)
    selected_city_id = request.GET.get("city_id")

    slums = Slum.objects.none()
    if selected_city_id:
        slums = Slum.objects.filter(
            electoral_ward__administrative_ward__city_id=selected_city_id
        ).order_by("name")

    return render(
        request,
        "photos/index.html",
        {
            "cities": cities,
            "slums": slums,
            "selected_city_id": selected_city_id,
            "can_download": can_download_photos(request.user),
        },
    )


@require_GET
@permission_required("mastersheet.can_view_mastersheet", raise_exception=True)
def photo_slum(request, slum_id):
    """Households in one slum.

    Local DB only -- no Avni calls. Asking Avni whether each household has
    photos would mean one API round trip per row, which would make this page
    unusable. Photo presence is discovered on the household page instead.
    """
    slum, forbidden = _slum_or_forbidden(request, slum_id)
    if forbidden:
        return forbidden

    show_all = request.GET.get("all") == "1"

    tc_numbers = {
        normalize_household_number(number)
        for number in ToiletConstruction.objects.filter(slum_id=slum.id).values_list(
            "household_number", flat=True
        )
    }

    queryset = HouseholdData.objects.filter(slum_id=slum.id)
    total_count = queryset.count()
    if not show_all:
        queryset = _with_recorded_activity(slum.id, tc_numbers)

    households = []
    for record in queryset.order_by("household_number"):
        ff_data = record.ff_data or {}
        lookup_number = normalize_household_number(record.household_number)
        source = sources.household_source(ff_data, record.rhs_data)
        households.append(
            {
                "household_number": record.household_number,
                "lookup_number": lookup_number,
                "family_name": ff_data.get(FAMILY_HEAD_KEY) or "",
                "has_factsheet": source != sources.SOURCE_NONE,
                "source": source,
                "source_label": {
                    sources.SOURCE_KOBO: "Kobo",
                    sources.SOURCE_AVNI: "Avni",
                }.get(source, ""),
                "has_construction": lookup_number in tc_numbers,
            }
        )

    return render(
        request,
        "photos/slum.html",
        {
            "slum": slum,
            "households": households,
            "show_all": show_all,
            "total_count": total_count,
            "shown_count": len(households),
            "can_download": can_download_photos(request.user),
            "photo_types": avni_media.PHOTO_TYPES,
            "fy_date_fields": collect.FY_DATE_FIELDS,
            "financial_years": financial_year_choices(),
        },
    )


def _pending_duplicate_export(user, slum, email, params):
    """The same photo export this user already has queued or running, if any.

    Guards against a double-click or an impatient re-click: without it the
    runner would build, zip and email the identical archive twice, and bill the
    disk for both. Only `queued` and `running` block -- once a job is `done` or
    `failed`, asking again is a legitimate request.

    `params` is a `jsonfield.JSONField`, which has no reliable SQL lookup, so
    the handful of pending rows are compared in Python instead. Lists are sorted
    before comparison because the browser sends the selected household numbers
    in whatever order the user ticked them.
    """

    def normalise(values):
        return {
            key: sorted(value) if isinstance(value, list) else value
            # estimated_photos is a derived count, not a filter -- two requests
            # that differ only there are still the same export.
            for key, value in values.items()
            if key != "estimated_photos"
        }

    wanted = normalise(params)
    pending = ExportRequest.objects.filter(
        export_type="photo",
        status__in=("queued", "running"),
        requested_by=user,
        slum=slum,
        email=email,
    )
    for job in pending:
        if normalise(job.params or {}) == wanted:
            return job
    return None


def _with_recorded_activity(slum_id, tc_numbers):
    """Households with some recorded programme activity.

    Photos only exist for households that were surveyed, and most were not --
    across the database only ~1.8% have an Avni factsheet, though the Kobo
    backup covers many more. Listing every household would mean clicking
    through hundreds of empty ones.

    Three local signals, no Avni calls: an Avni factsheet (ff_uuid), a Kobo
    factsheet (_attachments), or recorded construction progress (a
    ToiletConstruction row). All three are needed -- a household can have Daily
    Reporting agreement photos and no factsheet at all, so filtering on the
    factsheet alone would hide exactly the households with agreement photos.
    """
    by_factsheet = HouseholdData.objects.filter(
        slum_id=slum_id, ff_data__icontains="ff_uuid"
    )
    by_kobo = HouseholdData.objects.filter(
        slum_id=slum_id, ff_data__icontains="_attachments"
    )
    # HouseholdData zero-pads household numbers inconsistently, so match every
    # padded variant of the numbers ToiletConstruction knows about.
    variants = set()
    for number in tc_numbers:
        variants |= household_number_variants(number)
    by_construction = HouseholdData.objects.filter(
        slum_id=slum_id, household_number__in=sorted(variants)
    )
    return (by_factsheet | by_kobo | by_construction).distinct()


@require_GET
@permission_required("mastersheet.can_view_mastersheet", raise_exception=True)
def photo_household(request, slum_id, household_number):
    """One household's photos, from Avni or the Kobo backup."""
    slum, forbidden = _slum_or_forbidden(request, slum_id)
    if forbidden:
        return forbidden

    lookup_number = normalize_household_number(household_number)
    record = collect.find_household(slum.id, lookup_number)

    context = {
        "slum": slum,
        "household_number": household_number,
        "family_name": "",
        "programs": None,
        "error": None,
        "can_download": can_download_photos(request.user),
        "source": sources.SOURCE_NONE,
    }

    if record is None:
        context["error"] = "No household {} found in {}.".format(
            household_number, slum.name
        )
        return render(request, "photos/household.html", context)

    context["family_name"] = (record.ff_data or {}).get(FAMILY_HEAD_KEY) or ""
    context["source"] = sources.household_source(record.ff_data, record.rhs_data)
    context["has_construction"] = ToiletConstruction.objects.filter(
        slum_id=slum.id, household_number__in=sorted(
            household_number_variants(lookup_number)
        )
    ).exists()

    # Cheap for a single household (3-4 extra calls), so include direct
    # encounters here even though bulk export skips them.
    groups, error = collect.household_groups(record, include_direct_encounters=True)
    if error:
        context["error"] = error
        return render(request, "photos/household.html", context)

    context["programs"] = groups
    context["photo_count"] = sum(group["photo_count"] for group in groups)
    return render(request, "photos/household.html", context)


@require_POST
@permission_required("mastersheet.can_view_mastersheet", raise_exception=True)
def photo_household_download(request, slum_id, household_number):
    """Instant zip of one household's photos.

    Synchronous and unqueued on purpose: a single household is a handful of
    photos (a few MB), so making someone wait for a cron tick and an email
    would be absurd. Bulk slum exports go through the queue instead.
    """
    if not can_download_photos(request.user):
        return HttpResponseForbidden("You do not have permission to download photos.")

    slum, forbidden = _slum_or_forbidden(request, slum_id)
    if forbidden:
        return forbidden

    lookup_number = normalize_household_number(household_number)
    record = collect.find_household(slum.id, lookup_number)
    if record is None:
        return HttpResponse("Household not found.", status=404)

    selected = request.POST.getlist("labels") or None
    groups, error = collect.household_groups(record)
    if error:
        return HttpResponse(error, status=502)

    entries = collect.entries_from_groups(
        groups, slum.name, record.household_number, selected_labels=selected
    )
    if not entries:
        return HttpResponse("No photos selected for this household.", status=400)

    max_photos = settings_value("PHOTO_INSTANT_MAX_PHOTOS", 60)
    if len(entries) > max_photos:
        return HttpResponse(
            "This household has {} photos, more than the {} allowed for an "
            "instant download. Use the slum export instead.".format(
                len(entries), max_photos
            ),
            status=400,
        )

    content, written, failures = export.build_zip_bytes(entries)
    max_mb = settings_value("PHOTO_INSTANT_MAX_MB", 80)
    if len(content) > max_mb * 1024 * 1024:
        return HttpResponse(
            "This download would be {:.0f} MB, over the {} MB instant limit. "
            "Use the slum export instead.".format(
                len(content) / 1024 / 1024, max_mb
            ),
            status=400,
        )
    if not written:
        return HttpResponse(
            "None of the selected photos could be retrieved.", status=502
        )

    filename = "{}-{}-photos.zip".format(
        export.safe_path_component(slum.name, "slum").replace(" ", "-").lower(),
        export.safe_path_component(record.household_number, "household"),
    )
    response = HttpResponse(content, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
    if failures:
        response["X-Photo-Failures"] = str(len(failures))
    return response


def settings_value(name, default):
    from django.conf import settings

    return getattr(settings, name, default)


@require_POST
@permission_required("mastersheet.can_view_mastersheet", raise_exception=True)
def photo_export_submit(request, slum_id):
    """Queue a slum-level photo export."""
    if not can_download_photos(request.user):
        return JsonResponse(
            {"error": "You do not have permission to download photos."}, status=403
        )

    slum, forbidden = _slum_or_forbidden(request, slum_id)
    if forbidden:
        return JsonResponse(
            {"error": "You do not have permission to access this slum."}, status=403
        )

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except ValueError:
        return JsonResponse({"error": "Invalid request."}, status=400)

    email = (payload.get("email") or "").strip()
    if not validate_shelter_email(email):
        return JsonResponse(
            {"error": "Enter a @shelter-associates.org email address."}, status=400
        )

    photo_types = [
        photo_type
        for photo_type in (payload.get("photo_types") or [])
        if photo_type in avni_media.PHOTO_TYPE_KEYS
    ]
    household_numbers = payload.get("household_numbers") or None
    date_field = payload.get("date_field") or None
    financial_year = payload.get("financial_year") or None
    if date_field and date_field not in collect.FY_DATE_FIELD_NAMES:
        return JsonResponse({"error": "Unknown date field."}, status=400)

    records = collect.slum_household_records(
        slum.id,
        household_numbers=household_numbers,
        date_field=date_field,
        fy_start_year=financial_year,
    )
    if not records:
        return JsonResponse(
            {"error": "No households match those filters."}, status=400
        )

    estimated = collect.estimate_slum_photo_count(records, photo_types)
    ok, message = runner.check_disk(estimated)
    if not ok:
        # Refuse before queueing, and tell the developer -- freeing space is
        # their job, and the requester can do nothing about it.
        logger.error("Photo export refused for %s: %s", slum.name, message)
        return JsonResponse({"error": message}, status=507)

    scope = "Slum: {} ({} households".format(slum.name, len(records))
    if photo_types:
        scope += ", {}".format(", ".join(photo_types))
    if date_field and financial_year:
        scope += ", FY {}".format(financial_year)
    scope += ")"

    params = {
        "photo_types": photo_types,
        "household_numbers": household_numbers,
        "date_field": date_field,
        "financial_year": financial_year,
        "estimated_photos": estimated,
    }

    duplicate = _pending_duplicate_export(request.user, slum, email, params)
    if duplicate:
        return JsonResponse(
            {
                "error": (
                    "You already have this exact export {} (request #{}). "
                    "You will be emailed when it is ready -- no need to queue "
                    "it again.".format(duplicate.get_status_display().lower(), duplicate.pk)
                ),
                "duplicate_of": duplicate.pk,
            },
            status=409,
        )

    job = ExportRequest.objects.create(
        export_type="photo",
        status="queued",
        requested_by=request.user,
        email=email,
        scope=scope[:500],
        slum=slum,
        params=params,
    )
    return JsonResponse(
        {
            "status": "queued",
            "id": job.pk,
            "message": (
                "Queued about {} photos from {} households. You will be emailed "
                "a download link when it is ready.".format(estimated, len(records))
            ),
        }
    )


@require_GET
@permission_required("mastersheet.can_view_mastersheet", raise_exception=True)
def photo_export_list(request):
    """The requester's own photo exports."""
    if not can_download_photos(request.user):
        return HttpResponseForbidden("You do not have permission to download photos.")
    exports = ExportRequest.objects.filter(
        export_type="photo", requested_by=request.user
    )[:100]
    return render(request, "photos/exports.html", {"exports": exports})


@require_GET
@permission_required("mastersheet.can_view_mastersheet", raise_exception=True)
def photo_export_download(request, export_id):
    """Download a finished export.

    Authenticated, permission-checked and ownership-checked -- unlike the RIM
    and GIS download views, which have no auth at all. Streams with
    FileResponse rather than reading the whole (potentially multi-GB) file into
    memory.
    """
    if not can_download_photos(request.user):
        return HttpResponseForbidden("You do not have permission to download photos.")

    job = get_object_or_404(ExportRequest, pk=export_id, export_type="photo")
    if job.requested_by_id != request.user.id and not request.user.is_superuser:
        return HttpResponseForbidden("This export belongs to another user.")
    if job.status != "done" or not job.file_path:
        return HttpResponse(
            "This export is not ready (status: {}).".format(job.status), status=404
        )
    if not os.path.exists(job.file_path):
        return HttpResponse(
            "This export has expired and been cleaned up. Request it again.",
            status=404,
        )

    response = FileResponse(
        open(job.file_path, "rb"), content_type="application/zip"
    )
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(
        os.path.basename(job.file_path)
    )
    response["Content-Length"] = os.path.getsize(job.file_path)
    return response


@require_GET
@permission_required("mastersheet.can_view_mastersheet", raise_exception=True)
def photo_encounter(request):
    """One program encounter looked up directly by UUID."""
    encounter_uuid = (request.GET.get("uuid") or "").strip()
    context = {
        "encounter_uuid": encounter_uuid,
        "encounter": None,
        "error": None,
        "can_download": can_download_photos(request.user),
    }

    if not encounter_uuid:
        context["error"] = "Enter a program encounter UUID."
        return render(request, "photos/encounter.html", context)

    encounter = avni_media.resolve_encounter_photos(encounter_uuid)
    if encounter is None:
        context["error"] = (
            "No program encounter found in Avni for that UUID, or Avni could "
            "not be reached."
        )
        return render(request, "photos/encounter.html", context)

    context["encounter"] = encounter
    return render(request, "photos/encounter.html", context)


# ---------------------------------------------------------------------------
# Protected media
#
# Kobo-era photos live under MEDIA_ROOT/shelter/attachments/, which nginx serves
# straight off disk. That made every one of those ~17,766 households' family and
# toilet photos downloadable by anyone with the URL, no login required. They are
# now served only through this view, and nginx denies the raw path.
# ---------------------------------------------------------------------------

# The only MEDIA_ROOT subtree this view will ever serve.
PROTECTED_MEDIA_PREFIX = "shelter/attachments"


def protected_media_url(relative_path):
    """URL for a protected media file, for templates and serialisers."""
    from django.urls import reverse

    return reverse("photos:protected_media", args=[relative_path])


@require_GET
def protected_media(request, relative_path):
    """Serve one Kobo photo, authenticated.

    Permission comes from can_view_protected_media rather than a single
    permission_required decorator, because these files are linked from both the
    mastersheet grid and the sponsor factsheet report, which have different
    access rules. No legitimate user loses access; anonymous ones do.
    """
    from django.conf import settings

    if not can_view_protected_media(request.user):
        return HttpResponseForbidden("You do not have permission to view this photo.")

    # Normalise before doing anything else: without this, "a/../../../etc/passwd"
    # would escape MEDIA_ROOT.
    cleaned = os.path.normpath(relative_path).replace("\\", "/").lstrip("/")
    if not cleaned.startswith(PROTECTED_MEDIA_PREFIX + "/"):
        return HttpResponseForbidden("Not a protected media path.")

    full_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, cleaned))
    media_root = os.path.normpath(settings.MEDIA_ROOT)
    # Belt and braces: confirm the resolved path really is inside MEDIA_ROOT.
    if not full_path.startswith(media_root + os.sep):
        return HttpResponseForbidden("Not a protected media path.")

    if not os.path.isfile(full_path):
        return HttpResponse("Photo not found on the server.", status=404)

    content_type, _encoding = mimetypes.guess_type(full_path)
    response = FileResponse(
        open(full_path, "rb"), content_type=content_type or "application/octet-stream"
    )
    response["Content-Length"] = os.path.getsize(full_path)
    # Private: it is household data, and the URL is stable.
    response["Cache-Control"] = "private, max-age=300"
    return response


# ---------------------------------------------------------------------------
# Avni photo redirect
#
# Avni signs media URLs with X-Amz-Expires=120 -- two minutes. That is fine for
# rendering a thumbnail (it loads immediately) but not for the link behind it:
# open a household page, read it for a few minutes, click a photo, and S3
# answers 403. This view re-signs at click time so the link always works.
#
# Only the href goes through here. Thumbnail `src` keeps the batch-signed URL,
# so a page of photos still costs one signing round trip, not one per image.
# ---------------------------------------------------------------------------

# Signing is done with our own Avni credentials, so only Avni's own media host
# may be passed in -- otherwise this would be an open redirect.
AVNI_MEDIA_HOST_RE = re.compile(r"^https://s3[.-][\w-]+\.amazonaws\.com/", re.IGNORECASE)


def avni_photo_url(raw_url):
    """Click-through URL for an Avni photo (re-signed on demand)."""
    from django.urls import reverse

    return "{}?u={}".format(
        reverse("photos:photo_redirect"), quote(raw_url or "", safe="")
    )


@require_GET
def photo_redirect(request):
    """Re-sign one Avni photo URL and redirect to it."""
    if not can_view_protected_media(request.user):
        return HttpResponseForbidden("You do not have permission to view this photo.")

    raw_url = (request.GET.get("u") or "").strip()
    if not raw_url or not AVNI_MEDIA_HOST_RE.match(raw_url):
        return HttpResponseForbidden("Not an Avni media URL.")

    signed = avni_media.sign_urls([raw_url]).get(raw_url)
    if not signed or signed == raw_url:
        return HttpResponse(
            "Could not get a fresh link for this photo. Try reloading the page.",
            status=502,
        )
    return HttpResponseRedirect(signed)


@require_GET
def photo_sign(request):
    """Return a freshly signed URL for one Avni photo, as JSON.

    Called by the browser once per thumbnail after the page has rendered.
    Signing is one HTTP round trip to Avni per photo; doing it during the
    request would hold the whole page hostage to the slowest one, and the
    signature expires in 120 seconds regardless. Fetching lazily means the page
    paints immediately and each photo fills in on its own.
    """
    if not can_view_protected_media(request.user):
        return JsonResponse({"error": "Not permitted."}, status=403)

    raw_url = (request.GET.get("u") or "").strip()
    if not raw_url or not AVNI_MEDIA_HOST_RE.match(raw_url):
        return JsonResponse({"error": "Not an Avni media URL."}, status=400)

    signed = avni_media.sign_urls([raw_url]).get(raw_url)
    if not signed or signed == raw_url:
        return JsonResponse({"error": "Could not sign this photo."}, status=502)
    return JsonResponse({"url": signed})
