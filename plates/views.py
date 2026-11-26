"""Plates pages. Every view: login, then can_use_plates (template pages: can_edit_templates). Batches are reached
by their random public_id and only by their owner or a superuser; anyone else gets the same 403 either way."""

import base64
import io
import os

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_GET, require_POST

from helpers.validators import validate_shelter_email
from plates import forms
from plates.models import PlateAsset, PlateBatch, PlateFont, PlateTemplate
from plates.permissions import can_edit_templates, forbidden, plates_required, templates_required
from plates.services import activity, batch as batches, editor, email, excel, formats, linkpattern, naming, qr, retention, rows
from plates.services.render import PlateRenderer, save_png, with_options
from plates.services.resources import MissingResource, Resources
from plates.services.textfit import TextDoesNotFit

LOGIN_URL = "/accounts/login/"
SHOWN_ROWS = 50
TOO_LONG = {
    "slum": "The slum name is too long for this template, even at the smallest size. Shorten it or pick another template.",
    "code": "The code is too wide for this template, even at the smallest size. Pick another template.",
}
FORMAT_CACHE = {}


def private(response):
    response["Cache-Control"] = "private, no-store"
    return response


def png_response(image, dpi, file_name=None):
    buffer = io.BytesIO()
    save_png(image, buffer, dpi)
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    if file_name:
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(file_name)
    return private(response)


def own_batch(request, public_id):
    """The batch, or None when it does not exist or belongs to someone else (the caller answers 403 for both)."""
    batch = PlateBatch.objects.select_related("template", "requested_by", "job_request").filter(public_id=public_id).first()
    if batch is None or (batch.requested_by_id != request.user.id and not request.user.is_superuser):
        return None
    return batch


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def home(request):
    recent = PlateBatch.objects.filter(requested_by=request.user).select_related("template")[:8]
    return render(request, "plates/home.html", {"recent": recent, "can_edit": can_edit_templates(request.user)})


def template_types():
    return [{"id": template.pk, "type": template.plate_type, "is_default": template.is_default} for template in forms.usable_templates()]


def single_preview(form, request):
    template = form.cleaned_data["template"]
    spec = with_options(template.spec(), holes=form.cleaned_data["holes"], side_panel=form.cleaned_data["side_panel"])
    renderer = PlateRenderer(spec, Resources.from_database())
    try:
        image = renderer.render(form.row)
    except TextDoesNotFit as exc:
        form.add_error(None, TOO_LONG.get(exc.element_id, str(exc)))
        return None, None
    activity.log(request, "single_plate", template=template, detail=rows.plate_code(form.row, template.plate_type))
    return template, image


def preview_data(image):
    small = image.resize((image.width // 2, image.height // 2))
    buffer = io.BytesIO()
    small.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


@login_required(login_url=LOGIN_URL)
@plates_required
def single(request):
    form = forms.SingleForm(request.POST or None, initial={"plate_type": request.GET.get("type", "digipin"), "holes": True})
    context = {"form": form, "template_types": template_types()}
    if request.method == "POST" and form.is_valid():
        if activity.single_plates_left(request.user) <= 0:
            form.add_error(None, "You have made 60 plates in the last minute. Wait a minute and try again.")
        else:
            template, image = single_preview(form, request)
            if image is not None and request.POST.get("action") == "download":
                name = naming.plate_base_name(rows.plate_code(form.row, template.plate_type), form.row["house_no"]) + ".png"
                return png_response(image, template.dpi, name)
            if image is not None:
                context.update(preview=preview_data(image), warnings=form.warnings, template=template)
    return render(request, "plates/single.html", context)


@login_required(login_url=LOGIN_URL)
@plates_required
def bulk_new(request):
    form = forms.UploadForm(request.POST or None, request.FILES or None, initial={"plate_type": request.GET.get("type", "digipin"), "holes": True})
    if request.method == "POST" and form.is_valid():
        batch, error = create_draft(request, form)
        if batch is not None:
            return redirect("plates:bulk_check", public_id=batch.public_id)
        form.add_error("file", error)
    return render(request, "plates/bulk_new.html", {"form": form, "template_types": template_types()})


def create_draft(request, form):
    """A draft batch with the upload stored privately; refused (and removed) when the headers are wrong."""
    upload, template = form.cleaned_data["file"], form.cleaned_data["template"]
    batch = PlateBatch(template=template, plate_type=template.plate_type, source="excel", original_name=os.path.basename(upload.name)[:255],
                       sheet_name=form.cleaned_data.get("sheet_name", ""), requested_by=request.user, email=request.user.email or "",
                       holes=form.cleaned_data["holes"], side_panel=form.cleaned_data["side_panel"])
    batch.upload.save("upload.xlsx", upload, save=True)
    try:
        sheet = excel.read_sheet(batch.upload.path, batch.sheet_name)
        excel.column_positions(sheet.headers, batch.plate_type)
    except excel.UploadError as exc:
        batch.upload.delete(save=False)
        batch.delete()
        return None, str(exc)
    except Exception:
        batch.upload.delete(save=False)
        batch.delete()
        return None, "The file could not be read as an Excel workbook. Save it as an Excel Workbook (.xlsx) and try again."
    batch.sheet_name = sheet.title
    batch.save(update_fields=["sheet_name"])
    activity.log(request, "upload", batch=batch, template=template)
    return batch, None


def check_draft(batch):
    """(renderer, CheckResult or None, error)."""
    try:
        renderer, checked = batches.checked_batch(batch)
    except excel.UploadError as exc:
        return None, None, str(exc)
    batches.apply_check(batch, checked)
    batch.save()
    return renderer, checked, ""


@login_required(login_url=LOGIN_URL)
@plates_required
def bulk_check(request, public_id):
    batch = own_batch(request, public_id)
    if batch is None:
        return forbidden()
    if batch.status != "draft":
        return redirect("plates:batch_detail", public_id=batch.public_id)
    if request.method == "POST" and request.POST.get("sheet_name") in excel.sheet_names(batch.upload.path):
        batch.sheet_name = request.POST["sheet_name"]
        batch.save(update_fields=["sheet_name"])
    renderer, checked, error = check_draft(batch)
    demos = checked.demos(renderer) if checked else []
    request.session["plates_demo_{}".format(batch.public_id.hex)] = [result.number for result in demos]
    return render(request, "plates/bulk_check.html", check_context(batch, checked, demos, error, request.GET.get("message", "")))


def check_context(batch, checked, demos, error, message):
    return {
        "default_email": batch.email or (batch.requested_by.email if batch.requested_by else ""),
        "batch": batch, "checked": checked, "demos": demos, "error": error, "message": message,
        "sheets": excel.sheet_names(batch.upload.path) if batch.upload else [],
        "skipped": checked.skipped[:SHOWN_ROWS] if checked else [], "warned": checked.warned[:SHOWN_ROWS] if checked else [],
        "duplicates": list(checked.duplicate_codes.items())[:SHOWN_ROWS] if checked else [],
        "renamed": checked.renamed[:SHOWN_ROWS] if checked else [], "shown": SHOWN_ROWS,
        "size_text": "{} x {} mm ({} x {} in) at {} DPI".format(batch.template.width_mm, batch.template.height_mm,
                                                             round(float(batch.template.width_mm) / 25.4, 2),
                                                             round(float(batch.template.height_mm) / 25.4, 2), batch.template.dpi),
    }


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def bulk_demo_image(request, public_id, row_number):
    """One demo plate drawn in memory for a row chosen by the check page; never saved."""
    batch = own_batch(request, public_id)
    if batch is None:
        return forbidden()
    if batch.status != "draft" or row_number not in request.session.get("plates_demo_{}".format(batch.public_id.hex), []):
        raise Http404()
    renderer, checked = batches.checked_batch(batch)
    result = next((item for item in checked.made if item.number == row_number), None)
    if result is None:
        raise Http404()
    return png_response(renderer.render(result.row), batch.template.dpi)


@login_required(login_url=LOGIN_URL)
@require_POST
@plates_required
def bulk_confirm(request, public_id):
    batch = own_batch(request, public_id)
    if batch is None:
        return forbidden()
    if request.POST.get("checked_demo") != "yes":
        return redirect_with_message(batch, 'Tick "I have checked the demo plates" to continue.')
    address = (request.POST.get("email") or "").strip()
    if not validate_shelter_email(address) or "<" in address or ">" in address or len(address) > 254:
        return redirect_with_message(batch, "Enter the @shelter-associates.org email address that should get the notifications.")
    try:
        checked = batches.checked_batch(batch)[1]
        batch = batches.confirm(batch, request.user, checked, address)
    except (batches.BatchError, excel.UploadError) as exc:
        return redirect_with_message(batch, str(exc))
    activity.log(request, "confirm", batch=batch, template=batch.template)
    return redirect("plates:batch_detail", public_id=batch.public_id)


def redirect_with_message(batch, message):
    target = "plates:bulk_check" if batch.status == "draft" else "plates:batch_detail"
    return redirect("{}?{}".format(reverse(target, args=[batch.public_id]), urlencode({"message": message})))


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def bulk_skipped(request, public_id):
    """Every skipped, warned or duplicate row of a draft's check, as an Excel list."""
    batch = own_batch(request, public_id)
    if batch is None:
        return forbidden()
    if batch.status != "draft":
        raise Http404()
    checked = batches.checked_batch(batch)[1]
    buffer = io.BytesIO()
    excel.write_problem_list(buffer, checked)
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="rows-to-check.xlsx"'
    return private(response)


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def batches_list(request):
    shown = PlateBatch.objects.select_related("template", "requested_by", "job_request")
    if not request.user.is_superuser:
        shown = shown.filter(requested_by=request.user)
    shown = list(shown[:200])
    for item in shown:
        batches.reconcile(item)
        retention.expire_if_gone(item)
    return render(request, "plates/batches.html", {"batches": shown})


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def batch_detail(request, public_id):
    batch = own_batch(request, public_id)
    if batch is None:
        return forbidden()
    if batch.status == "draft":
        return redirect("plates:bulk_check", public_id=batch.public_id)
    batches.reconcile(batch)
    expired = retention.expire_if_gone(batch)
    context = {
        "batch": batch, "available_until": retention.available_until(batch), "expired": expired,
        "expired_message": retention.EXPIRED_MESSAGE, "can_generate_again": batches.can_generate_again(batch),
        "message": request.GET.get("message", ""), "is_owner": batch.requested_by_id == request.user.id,
        "to_make": max(batch.row_count - batch.skipped_count, 0),
    }
    return render(request, "plates/batch_detail.html", context)


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def batch_download(request, public_id):
    batch = own_batch(request, public_id)
    if batch is None:
        return forbidden()
    if retention.expire_if_gone(batch) or batch.status != "done":
        return render(request, "plates/download_gone.html", {"batch": batch, "message": retention.EXPIRED_MESSAGE
                                                              if batch.status == "expired" else "This batch has no download yet."})
    activity.log(request, "download", batch=batch, template=batch.template)
    response = FileResponse(open(batch.file_path, "rb"), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(os.path.basename(batch.file_path))
    response["Content-Length"] = os.path.getsize(batch.file_path)
    return private(response)


@login_required(login_url=LOGIN_URL)
@require_POST
@plates_required
def batch_cancel(request, public_id):
    batch = own_batch(request, public_id)
    if batch is None:
        return forbidden()
    if batch.status not in ("draft", "queued"):
        return redirect_with_message(batch, "Only a draft or a queued batch can be cancelled.")
    try:
        batch = batches.cancel(batch, request.user)
    except batches.BatchError as exc:
        return redirect_with_message(batch, str(exc))
    activity.log(request, "cancel", batch=batch, template=batch.template)
    return redirect("plates:batch_detail", public_id=batch.public_id)


@login_required(login_url=LOGIN_URL)
@require_POST
@plates_required
def batch_regenerate(request, public_id):
    batch = own_batch(request, public_id)
    if batch is None:
        return forbidden()
    try:
        fresh = batches.generate_again(batch, request.user)
    except batches.BatchError as exc:
        return redirect_with_message(batch, str(exc))
    activity.log(request, "generate_again", batch=fresh, template=fresh.template, detail="from batch {}".format(batch.pk))
    return redirect("plates:bulk_check", public_id=fresh.public_id)


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def excel_format_download(request, plate_type):
    if plate_type not in rows.CODE_HEADERS:
        raise Http404()
    if plate_type not in FORMAT_CACHE:
        FORMAT_CACHE[plate_type] = formats.workbook_bytes(plate_type)
    response = HttpResponse(FORMAT_CACHE[plate_type], content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(formats.file_name(plate_type))
    return private(response)


def template_or_404(pk):
    template = PlateTemplate.objects.select_related("background_image", "parent").filter(pk=pk).first()
    if template is None:
        raise Http404()
    return template


def sample_png(spec, worst=False, scale=1):
    """The template drawn with a sample (or worst-case) row, as PNG bytes; scale < 1 draws at a lower DPI (previews)."""
    rows_for = editor.WORST_ROWS if worst else editor.SAMPLE_ROWS
    drawn = dict(spec, dpi=max(1, int(spec["dpi"] * scale)))
    try:
        image = PlateRenderer(drawn, Resources.from_database()).render(rows_for[spec["plate_type"]])
    except (TextDoesNotFit, MissingResource):
        return None
    buffer = io.BytesIO()
    save_png(image, buffer, drawn["dpi"])
    return buffer.getvalue()


@login_required(login_url=LOGIN_URL)
@require_GET
@templates_required
def templates(request):
    context = {
        "latest": PlateTemplate.objects.filter(versions__isnull=True, is_active=True).order_by("plate_type", "-is_default", "name"),
        "archived_count": PlateTemplate.objects.filter(versions__isnull=True, is_active=False).count(),
        "assets": PlateAsset.objects.all(), "fonts": PlateFont.objects.all(),
        "asset_form": forms.AssetForm(), "font_form": forms.FontForm(), "message": request.GET.get("message", ""),
    }
    return render(request, "plates/templates.html", context)


def editor_page(request, form, template):
    context = {
        "form": form, "template": template, "read_only": bool(template and not template.is_latest),
        "patterns": linkpattern.STARTING_PATTERNS, "variables": linkpattern.VARIABLES,
        "fonts": list(PlateFont.objects.values_list("name", flat=True)),
        "assets": [{"id": asset.pk, "kind": asset.kind, "name": asset.name} for asset in PlateAsset.objects.all()],
    }
    return render(request, "plates/template_edit.html", context)


def save_template(request, template, form):
    was_new = template.pk is None
    old_spec = {} if was_new else template.spec()
    saved, changed = editor.save(template, form.spec, form.values, request.user)
    if changed:
        activity.log(request, "template_created" if was_new else "template_changed", template=saved, detail="version {}".format(saved.version))
        lines = ["New template"] if was_new else editor.describe_changes(old_spec, saved.spec())
        email.send_template_changed(saved, request.user, lines, sample_png(saved.spec(), scale=0.5))
    return saved


@login_required(login_url=LOGIN_URL)
@templates_required
def template_new(request):
    plate_type = request.GET.get("type") if request.GET.get("type") in rows.CODE_HEADERS else "digipin"
    start = forms.usable_templates(plate_type).filter(is_default=True).first() or forms.usable_templates(plate_type).first()
    base = start.spec() if start else {"plate_type": plate_type, "width_mm": 127, "height_mm": 38.1, "dpi": 600}
    base["plate_type"] = plate_type
    form = forms.TemplateForm(request.POST or None, base=base, resources=Resources.from_database(),
                              initial=forms.initial_for(base, "New {} template".format(rows.CODE_HEADERS[plate_type])))
    if request.method == "POST" and form.is_valid():
        saved = save_template(request, PlateTemplate(plate_type=form.spec["plate_type"]), form)
        return redirect("plates:template_edit", pk=saved.pk)
    return editor_page(request, form, None)


@login_required(login_url=LOGIN_URL)
@templates_required
def template_edit(request, pk):
    template = template_or_404(pk)
    base = template.spec()
    form = forms.TemplateForm(request.POST or None, base=base, resources=Resources.from_database(),
                              initial=forms.initial_for(base, template.name, template.is_default, template.is_active))
    if request.method == "POST" and template.is_latest and form.is_valid():
        if form.spec["plate_type"] != template.plate_type:
            form.add_error("plate_type", "The plate type of a template cannot change. Copy it and make a new one instead.")
        else:
            saved = save_template(request, template, form)
            return redirect("plates:template_edit", pk=saved.pk)
    return editor_page(request, form, template)


@login_required(login_url=LOGIN_URL)
@require_POST
@templates_required
def template_copy(request, pk):
    source = template_or_404(pk)
    copy = PlateTemplate(plate_type=source.plate_type, name="Copy of {}".format(source.name)[:120], created_by=request.user)
    editor.apply_look(copy, source.spec())
    copy.save()
    activity.log(request, "template_created", template=copy, detail="copy of template {} v{}".format(source.pk, source.version))
    return redirect("plates:template_edit", pk=copy.pk)


@login_required(login_url=LOGIN_URL)
@require_POST
@templates_required
def template_preview(request):
    """Live preview of the editor form, unsaved: {"image": data URI or "", "problems": [...]}."""
    base_template = PlateTemplate.objects.filter(pk=request.POST.get("base") or 0).first()
    resources = Resources.from_database()
    form = forms.TemplateForm(request.POST, base=base_template.spec() if base_template else {}, resources=resources, check_layout=False)
    if not form.is_valid():
        problems = ["{}: {}".format(field if field != "__all__" else "Template", " ".join(errors)) for field, errors in form.errors.items()]
        return JsonResponse({"image": "", "problems": problems})
    problems = editor.problems(form.spec, resources)
    png = sample_png(form.spec, worst=request.POST.get("worst") == "1", scale=0.5)
    image = "data:image/png;base64," + base64.b64encode(png).decode("ascii") if png else ""
    return JsonResponse({"image": image, "problems": problems})


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def template_image(request, pk):
    """A saved template drawn with a sample row (login-checked; never a /media URL)."""
    template = template_or_404(pk)
    png = sample_png(template.spec(), worst=request.GET.get("worst") == "1", scale=0.5 if request.GET.get("small") else 1)
    if png is None:
        raise Http404()
    return private(HttpResponse(png, content_type="image/png"))


@login_required(login_url=LOGIN_URL)
@require_POST
@templates_required
def link_preview(request):
    """QR link helper: the link filled for a sample row, the save checks, and a test QR."""
    plate_type = request.POST.get("plate_type") if request.POST.get("plate_type") in rows.CODE_HEADERS else "digipin"
    pattern = (request.POST.get("pattern") or "").strip()
    problems = linkpattern.problems(pattern, plate_type)
    link = linkpattern.fill(pattern, editor.SAMPLE_ROWS[plate_type]) if not problems else ""
    image = ""
    if link:
        buffer = io.BytesIO()
        qr.qr_image(link, 240, quiet_zone=2).save(buffer, "PNG")
        image = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    return JsonResponse({"link": link, "problems": problems, "qr": image})


@login_required(login_url=LOGIN_URL)
@require_POST
@templates_required
def asset_upload(request):
    form = forms.AssetForm(request.POST, request.FILES)
    if not form.is_valid():
        return redirect("{}?{}".format(reverse("plates:templates"), urlencode({"message": "Logo not saved: " + " ".join(
            " ".join(errors) for errors in form.errors.values())})))
    asset = form.save()
    activity.log(request, "asset_uploaded", detail="{} ({})".format(asset.name, asset.kind))
    return redirect("{}?{}".format(reverse("plates:templates"), urlencode({"message": "Saved {}.".format(asset.name)})))


@login_required(login_url=LOGIN_URL)
@require_POST
@templates_required
def font_upload(request):
    form = forms.FontForm(request.POST, request.FILES)
    if not form.is_valid():
        return redirect("{}?{}".format(reverse("plates:templates"), urlencode({"message": "Font not saved: " + " ".join(
            " ".join(errors) for errors in form.errors.values())})))
    font = form.save()
    activity.log(request, "font_uploaded", detail=font.name)
    return redirect("{}?{}".format(reverse("plates:templates"), urlencode({"message": "Saved {}.".format(font.name)})))


GUIDE_PDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "plates", "plates-guide.pdf")


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def help_page(request):
    return render(request, "plates/help.html")


@login_required(login_url=LOGIN_URL)
@require_GET
@plates_required
def help_pdf(request):
    if not os.path.isfile(GUIDE_PDF):
        raise Http404()
    return private(FileResponse(open(GUIDE_PDF, "rb"), as_attachment=True, filename="plates-guide.pdf", content_type="application/pdf"))


def templates_redirect(message, page="plates:templates"):
    return redirect("{}?{}".format(reverse(page), urlencode({"message": message})))


@login_required(login_url=LOGIN_URL)
@require_GET
@templates_required
def templates_archived(request):
    context = {
        "archived": PlateTemplate.objects.filter(versions__isnull=True, is_active=False).order_by("plate_type", "name"),
        "older": PlateTemplate.objects.filter(versions__isnull=False).distinct().order_by("plate_type", "name", "-version"),
        "message": request.GET.get("message", ""),
    }
    return render(request, "plates/templates_archived.html", context)


@login_required(login_url=LOGIN_URL)
@require_POST
@templates_required
def template_archive(request, pk):
    template = template_or_404(pk)
    if not template.is_latest:
        return templates_redirect("Only the current version of a template can be archived.")
    was_default = template.is_default
    editor.archive(template)
    activity.log(request, "template_changed", template=template, detail="archived")
    note = " It was the default, so choose another default {} template.".format(template.get_plate_type_display()) if was_default else ""
    return templates_redirect("Archived {}. It is hidden from every picker; find it under Archived templates to restore or delete it.{}".format(template.name, note))


@login_required(login_url=LOGIN_URL)
@require_POST
@templates_required
def template_restore(request, pk):
    template = template_or_404(pk)
    if not editor.is_archived(template):
        return templates_redirect("This template is not archived.", "plates:templates_archived")
    editor.restore(template)
    activity.log(request, "template_changed", template=template, detail="restored from the archive")
    return templates_redirect("Restored {}. It is back in the pickers.".format(template.name))


@login_required(login_url=LOGIN_URL)
@templates_required
def template_delete(request, pk):
    """GET: confirmation page. POST: delete the archived template and all its versions."""
    template = template_or_404(pk)
    if request.method == "POST":
        name = template.name
        try:
            removed = editor.delete_permanently(template)
        except ValueError as exc:
            return templates_redirect(str(exc), "plates:templates_archived")
        activity.log(request, "template_changed", detail="deleted {} permanently ({} version{})".format(name, removed, "" if removed == 1 else "s"))
        return templates_redirect("Deleted {} permanently ({} version{}).".format(name, removed, "" if removed == 1 else "s"), "plates:templates_archived")
    context = {"template": template, "archived": editor.is_archived(template), "versions": editor.family(template),
               "batches": editor.batch_count(template)}
    return render(request, "plates/template_delete.html", context)
