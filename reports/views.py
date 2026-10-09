import json
import requests
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from .services.rim_compare import compare
from .services.rim_factsheet import rim_factsheet_view
from reports.models import (
    SponsorProjectMonthlyReportDetails,
    SponsorProjectReportDetails,
)
from reports.services.monthly_report_service import monthly_report_details
from survey import versioning


def wanted_version(request):
    """The RIM version asked for, or None for the live one."""
    raw = (request.GET.get("version") or "").strip()
    if not raw or raw.lower() == "current":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def rim_cache_key(slum_id, version):
    return "rim_context_{}_{}".format(slum_id, version if version is not None else "current")


def version_tag(version):
    """How a version appears in a report id: 'current' or 'v2'."""
    return "current" if version is None else "v{}".format(version)


def rim_report_id(slum_id, version, compared_with=None):
    """The PDF service keys stored files by report id, so each view needs its own."""
    base = str(slum_id) if version is None else "{}-v{}".format(slum_id, version)
    return base if compared_with is None else "{}-vs-{}".format(base, compared_with)


def previous_version(slum_id, version):
    """The archived RIM version just before the one being viewed, or None."""
    archived = versioning.rim_backup_versions(slum_id)
    earlier = [v for v in archived if version is None or v < version]
    return earlier[0] if earlier else None


def wanted_baseline(request, slum_id, version):
    """The version to compare against: the one asked for, else the one before.

    `against=current` is a real choice -- an older version can be read against
    the live survey -- so an absent parameter and `current` mean different
    things and None cannot stand for both.
    """
    raw = (request.GET.get("against") or "").strip()
    if not raw:
        return previous_version(slum_id, version)
    if raw.lower() == "current":
        return None
    try:
        return int(raw)
    except ValueError:
        return previous_version(slum_id, version)


def rim_context(slum_id, version):
    """The factsheet context for one version, briefly cached."""
    key = rim_cache_key(slum_id, version)
    context = cache.get(key)
    if context is None:
        context = rim_factsheet_view(slum_id, version=version)
        cache.set(key, context, timeout=120)
    return context


def version_label(version):
    return "Current" if version is None else "Version {}".format(version)


# Internal report tooling home page (RIM factsheet + donor report PDFs)
@staff_member_required
def report_view(request):
    """Renders the report home page with factsheet data if provided."""
    # Same index the KML upload page filters client-side, already limited to
    # the cities this user may see.
    from component.views import build_slum_search_index

    context = {"slum_search_index": build_slum_search_index(request.user)}

    if request.method == "POST":
        slum_id = request.POST.get("slum_id")
        factsheet_context = rim_factsheet_view(slum_id)

        if factsheet_context.get("meta_data", {}).get("_exists"):
            context["factsheet"] = factsheet_context

    return render(request, "report_home.html", context)


# HTML preview for RIM Factsheet
def rim_factsheet_html_report(request, slum_id):
    """Renders HTML preview for RIM Factsheet report."""
    context = rim_factsheet_view(slum_id, version=wanted_version(request))
    if not context.get("meta_data", {}).get("_exists"):
        return HttpResponse("Slum not found", status=404)

    return render(request, "reports/rim_factsheet/full_page/factsheet.html", context)


# Survey versions the reports page may show for a slum
@staff_member_required
def rim_versions(request, slum_id):
    """JSON: the RIM versions on offer, newest first."""
    choices = versioning.rim_choices_for(slum_id)
    return JsonResponse({
        "versions": [{"version": c["version"], "label": c["label"]} for c in choices],
    })


def rim_raw(slum_id, version):
    """The appraisal row as stored, which is what tells a picture apart.

    The URLs in the rendered context are signed afresh on every fetch, so they
    cannot be compared; the stored column behind them can.
    """
    return versioning.rim_at(slum_id, version)[1] or {}


def comparison_for(slum_id, version, baseline):
    """(comparison, baseline) for one version read against another."""
    if baseline == version:
        return None, baseline
    result = compare(
        rim_context(slum_id, baseline), rim_context(slum_id, version),
        old_raw=rim_raw(slum_id, baseline), new_raw=rim_raw(slum_id, version),
    )
    return result, baseline


def comparison_context(slum_id, version, result, earlier):
    return {
        "comparison": result,
        "old_label": version_label(earlier),
        "new_label": version_label(version),
        "meta_data": rim_context(slum_id, version).get("meta_data", {}),
    }


# What changed between the chosen version and the one before it
@staff_member_required
def rim_comparison(request, slum_id):
    """HTML of the changed fields, or nothing at all when they match."""
    version = wanted_version(request)
    baseline = wanted_baseline(request, slum_id, version)
    result, earlier = comparison_for(slum_id, version, baseline)
    if not result:
        return HttpResponse("")
    return render(
        request,
        "reports/rim_factsheet/compare.html",
        comparison_context(slum_id, version, result, earlier),
    )


# Trigger PDF generation for the comparison
@staff_member_required
def rim_comparison_pdf_generation(request, slum_id):
    """Sends the comparison to the PDF service under its own report id."""
    version = wanted_version(request)
    baseline = wanted_baseline(request, slum_id, version)
    result, earlier = comparison_for(slum_id, version, baseline)
    if not result:
        return HttpResponse("Nothing changed between these versions", status=406)

    context = comparison_context(slum_id, version, result, earlier)
    html = render_to_string("reports/rim_factsheet/pdf/compare_pdf.html", context)
    meta = context["meta_data"]
    name = "RIM_Changes_{}_{}_{}_to_{}".format(
        str(meta.get("city_name", "City")).replace(" ", "_").replace("/", "_"),
        str(meta.get("slum_name", "Slum")).replace(" ", "_").replace("/", "_"),
        version_tag(earlier),
        version_tag(version),
    )
    try:
        resp = requests.post(
            settings.PDF_SERVICE_URL,
            headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
            json={
                "html": html,
                "report_id": rim_report_id(slum_id, version, compared_with=version_tag(earlier)),
                "file_name": name,
                "force_generate": request.GET.get("force_generate", "false").lower() == "true",
                # Deliberately the existing type: the PDF service only knows
                # rim_factsheet and donor_report, and the report id keeps the
                # stored file apart from the factsheet's own.
                "report_type": "rim_factsheet",
            },
            timeout=120,
        )
        if resp.status_code == 200:
            return HttpResponse("PDF generated and saved successfully", status=202)
        return HttpResponse("PDF generation failed", status=500)
    except requests.exceptions.Timeout:
        return HttpResponse("PDF generation timed out", status=504)


# Trigger PDF generation for RIM Factsheet
def rim_factsheet_pdf_generation(request, slum_id):
    """Generates PDF for RIM Factsheet and sends to PDF service."""
    force_generate = request.GET.get("force_generate", "false").lower() == "true"
    version = wanted_version(request)
    context = rim_context(slum_id, version)

    if context.get("data") == "NA":
        return HttpResponse("No data available for PDF generation", status=405)
    elif context.get("meta_data", {}).get("_exists") == False:
        return HttpResponse("Slum not found", status=406)

    html = render_to_string("reports/rim_factsheet/pdf/factsheet_pdf.html", context)
    try:
        resp = requests.post(
            settings.PDF_SERVICE_URL,
            headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
            json={
                "html": html,
                "report_id": rim_report_id(slum_id, version),
                "file_name": f"RIM_Factsheet_{context.get('meta_data',{}).get('city_name','City').replace(' ','_').replace('/','_')}_{context.get('meta_data',{}).get('slum_name','Slum').replace(' ','_').replace('/','_')}{'' if version is None else f'_v{version}'}",
                "force_generate": force_generate,
                "report_type": "rim_factsheet",
            },
            timeout=120,
        )

        if resp.status_code == 200:
            return HttpResponse("PDF generated and saved successfully", status=202)

        return HttpResponse("PDF generation failed", status=500)

    except requests.exceptions.Timeout:
        return HttpResponse("PDF generation timed out", status=504)


# Preview generated RIM Factsheet PDF in browser
def rim_factsheet_preview(request, slum_id):
    """Renders preview of RIM Factsheet PDF in browser without download."""
    version = wanted_version(request)
    context = rim_context(slum_id, version)

    if context.get("data") == "NA":
        return HttpResponse("No data available for PDF generation", status=404)
    elif context.get("meta_data", {}).get("_exists") == False:
        return HttpResponse("Slum not found", status=404)

    html = render_to_string(
        "reports/rim_factsheet/preview/factsheet_preview.html", context
    )
    return HttpResponse(html)


# Download generated RIM Factsheet PDF
def rim_factsheet_pdf_fetch(request, slum_id):
    """Fetches and forces download of generated RIM Factsheet PDF.

    - Public users: require OTP verification
    - Internal team: logged-in staff skip OTP
    """
    is_internal = request.user.is_authenticated and request.user.is_staff

    # 🔐 If not internal, enforce OTP scoped to this specific slum
    if not is_internal:
        if str(request.session.get("rim_otp_verified_slum_id")) != str(slum_id):
            return HttpResponseForbidden("OTP verification required")

    version = wanted_version(request)
    compared_with = (
        version_tag(wanted_baseline(request, slum_id, version))
        if request.GET.get("compare") == "1" else None
    )
    report_id = rim_report_id(slum_id, version, compared_with=compared_with)
    try:
        resp = requests.get(
            f"{settings.PDF_FETCH_URL}?report_id={report_id}&report_type=rim_factsheet",
            headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
            timeout=30,
        )

        if resp.status_code == 200:
            response = HttpResponse(resp.content, content_type="application/pdf")
            content_disposition = resp.headers.get("Content-Disposition")

            if content_disposition:
                response["Content-Disposition"] = content_disposition
            else:
                response["Content-Disposition"] = (
                    f'attachment; filename="RIM_Factsheet_{slum_id}.pdf"'
                )

            response["Content-Length"] = len(resp.content)

            # Only invalidate OTP session for public users
            if not is_internal:
                request.session["rim_otp_verified_slum_id"] = None

            return response

        return HttpResponse("PDF not ready", status=404)

    except requests.exceptions.Timeout:
        return HttpResponse("PDF fetch timed out", status=504)


# ====================== Donar Report Views ======================


# Trigger PDF generation for monthly donor report
@staff_member_required
def monthly_donor_report_pdf_generation(request, report_id):
    """Generates PDF for monthly donor report and sends to PDF service."""
    cache_key = f"monthly_report_{report_id}"
    context = cache.get(cache_key)

    if context is None:
        data = monthly_report_details(request, report_id)
        context = {"data": data, "base_url": request.build_absolute_uri("/")[:-1]}
        cache.set(cache_key, context, timeout=120)

    if not context.get("data"):
        return HttpResponse("No data available for PDF generation", status=405)

    html = render_to_string("reports/donor_report/monthly_report_pdf.html", context)
    data = context.get("data")

    try:
        resp = requests.post(
            settings.PDF_SERVICE_URL,
            headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
            json={
                "html": html,
                "report_id": report_id,
                "file_name": f"Donor_Monthly_Report_{data['project']['sponsor_name'].replace(' ', '_')}_{data['month'].replace(' ', '_')}",
                "force_generate": True,
                "report_type": "donor_report",
            },
            timeout=120,
        )

        if resp.status_code == 200:
            return HttpResponse("PDF generated and saved successfully", status=202)

        return HttpResponse("PDF generation failed", status=500)

    except requests.exceptions.Timeout:
        return HttpResponse("PDF generation timed out", status=504)


# Download generated monthly donor report PDF
@staff_member_required
def monthly_donor_report_pdf_fetch(request, report_id):
    """Fetches and forces download of generated monthly donor report PDF."""
    try:
        resp = requests.get(
            f"{settings.PDF_FETCH_URL}?report_id={report_id}&report_type=donor_report",
            headers={"X-PDF-KEY": settings.PDF_SECRET_KEY},
            timeout=30,
        )

        if resp.status_code == 200:
            response = HttpResponse(resp.content, content_type="application/pdf")
            content_disposition = resp.headers.get("Content-Disposition")

            if content_disposition:
                response["Content-Disposition"] = content_disposition
            else:
                response["Content-Disposition"] = (
                    f'attachment; filename="report_{report_id}.pdf"'
                )

            response["Content-Length"] = len(resp.content)
            return response

        return HttpResponse("PDF not ready", status=404)

    except requests.exceptions.Timeout:
        return HttpResponse("PDF fetch timed out", status=504)


# Get all donor projects
@staff_member_required
def donor_projects(request):
    """Retrieves list of all donor projects with IDs and names."""
    projects = SponsorProjectReportDetails.objects.select_related(
        "sponsor_project"
    ).all()

    data = []
    for project in projects:
        data.append({"id": project.id, "name": str(project.sponsor_project)})

    return JsonResponse({"projects": data})


# Get report months for a specific project
@staff_member_required
def project_months(request, project_id):
    """Retrieves completed monthly reports for a specific project."""
    monthly_reports = SponsorProjectMonthlyReportDetails.objects.filter(
        project_report_id=project_id, status="completed"
    ).order_by("month")

    data = []
    for report in monthly_reports:
        data.append({"id": report.id, "month": report.month.strftime("%B %Y")})

    return JsonResponse({"months": data})
