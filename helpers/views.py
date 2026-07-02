import hashlib
import json
import logging
import random
from datetime import date, datetime, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from requests import request
from scipy import record

from helpers.services.send_email import send_email
from master.models import Slum
from shelter import settings
from sponsor.models import SponsorProject

from .models import (
    OTPVerification,
    PhotoTypeItem,
    ReminderTracker,
    SlumPhoto,
    SlumPhotoUpload,
)
from .services.google_drive import upload_photos_to_slum_drive_folder
from .services.photo_upload import *
  
logger = logging.getLogger(__name__)

# ============= Digipin Generation =============


def digipin_generate(request):
    logger.info("digipin_generate: rendering digipin generate page")
    return render(request, "helpers/digipin_generate.html")


# ============= OTP Generation =============


# ----------------------------------------------------------------------
# SEND OTP API
#
# This API generates and sends an OTP to the provided email for a
# specific verification task.
#
# Security and industry-level protections implemented:
# 1. Request method validation (only POST allowed)
# 2. Email presence validation
# 3. Rate limiting: prevents requesting OTP more than once within 30 seconds
# 4. OTP reuse: if an OTP is already active (not expired), the same OTP is resent
# 5. OTP expiry: OTP is valid for 5 minutes
# 6. OTP hashing: OTP stored in DB as SHA256 hash instead of plaintext
# 7. Attempt counter reset when new OTP is issued
# 8. Unique constraint on (email, task) ensures one active OTP per task
#
# Returns:
# {status:"otp_sent"} when OTP email successfully triggered
# {status:"wait"} when rate limit prevents new OTP request
# ----------------------------------------------------------------------
@csrf_exempt
def send_otp(request):
    logger.info("send_otp: request received, method=%s", request.method)

    if request.method != "POST":
        logger.warning("send_otp: invalid request method=%s", request.method)
        return JsonResponse(
            {"status": "error", "message": "Invalid request"}, status=400
        )

    data = json.loads(request.body)
    email = data.get("email")
    task = data.get("task", "Random Task")
    logger.info("send_otp: processing OTP request for email=%s task=%s", email, task)

    if not email:
        logger.warning("send_otp: email missing in request payload")
        return JsonResponse({"status": "error", "message": "Email required"})

    record = OTPVerification.objects.filter(email=email, task=task).first()
    if record and (timezone.now() - record.created_at).seconds < 30:
        logger.info(
            "send_otp: rate limit triggered for email=%s task=%s", email, task
        )
        return JsonResponse(
            {
                "status": "wait",
                "message": "Please wait 30 seconds before requesting another OTP",
            }
        )

    otp = str(random.randint(100000, 999999))
    expiry = timezone.now() + timedelta(minutes=5)
    hashed_otp = hashlib.sha256(otp.encode()).hexdigest()

    obj, created = OTPVerification.objects.update_or_create(
        email=email,
        task=task,
        defaults={
            "otp": hashed_otp,
            "expiry_time": expiry,
            "is_verified": False,
        },
    )
    logger.info(
        "send_otp: OTPVerification record %s for email=%s task=%s",
        "created" if created else "updated",
        email,
        task,
    )

    subject = "Shelter Associates - OTP Verification"
    template_name = "helpers/otp_email.html"
    context = {"otp": otp}
    plain_message = f"Your OTP is {otp}"

    send_email([email], subject, template_name, context, plain_message)
    logger.info("send_otp: OTP email dispatched to email=%s task=%s", email, task)

    return JsonResponse({"status": "otp_sent"})


# ----------------------------------------------------------------------
# VERIFY OTP API
#
# This API verifies the OTP submitted by the user.
#
# Security checks implemented:
# 1. Only POST requests allowed
# 2. OTP record must exist for (email, task)
# 3. OTP must not already be verified
# 4. OTP must not be expired
# 5. OTP comparison done using SHA256 hash
# 6. Brute-force protection using session attempt counter (max 5 tries)
#
# If verification succeeds:
# - OTP record is marked as verified
# - session attempt counter is reset
#
# Returns:
# {status:"verified"} when OTP correct
# {status:"invalid"} when OTP incorrect
# {status:"expired"} when OTP expired
# {status:"blocked"} when too many attempts
# ----------------------------------------------------------------------
def verify_otp(request):
    logger.info("verify_otp: request received, method=%s", request.method)

    if request.method != "POST":
        logger.warning("verify_otp: invalid request method=%s", request.method)
        return JsonResponse({"status": "error"}, status=400)

    data = json.loads(request.body)
    email = data.get("email")
    otp = data.get("otp")
    task = data.get("task", "FACTSHEET_DOWNLOAD")
    logger.info("verify_otp: processing OTP verification for email=%s task=%s", email, task)

    session_key = f"otp_attempts_{email}_{task}"
    attempts = request.session.get(session_key, 0)

    if attempts >= 5:
        logger.warning(
            "verify_otp: blocked due to too many attempts for email=%s task=%s",
            email,
            task,
        )
        return JsonResponse({"status": "blocked"})

    try:
        record = OTPVerification.objects.get(email=email, task=task)
    except OTPVerification.DoesNotExist:
        logger.warning(
            "verify_otp: no OTP record found for email=%s task=%s", email, task
        )
        return JsonResponse({"status": "invalid"})

    if record.is_verified:
        logger.warning(
            "verify_otp: OTP already verified for email=%s task=%s", email, task
        )
        return JsonResponse({"status": "invalid"})

    if record.expiry_time < timezone.now():
        logger.info("verify_otp: OTP expired for email=%s task=%s", email, task)
        return JsonResponse({"status": "expired"})

    input_hash = hashlib.sha256(otp.encode()).hexdigest()

    if record.otp != input_hash:
        request.session[session_key] = attempts + 1
        logger.warning(
            "verify_otp: invalid OTP attempt %s for email=%s task=%s",
            attempts + 1,
            email,
            task,
        )
        return JsonResponse({"status": "invalid"})

    record.is_verified = True
    record.save()
    request.session[session_key] = 0
    # mark session as verified for factsheet download
    request.session["rim_otp_verified"] = True
    logger.info("verify_otp: OTP verified successfully for email=%s task=%s", email, task)

    return JsonResponse({"status": "verified"})


@staff_member_required
def photo_upload_page(request):
    logger.info("photo_upload_page: rendering page for user=%s", request.user)
    return render(
        request,
        "helpers/photo_upload.html",
        {
            "is_superuser": request.user.is_superuser,
            "default_photo_date": date.today().isoformat(),
        },
    )


@staff_member_required
def photo_type_groups(request):
    logger.info("photo_type_groups: fetching root photo type groups")
    roots = PhotoTypeItem.objects.filter(
        parent__isnull=True, is_visible=True
    ).order_by("order", "name")
    groups = [{"id": node.id, "name": node.name} for node in roots]
    logger.info("photo_type_groups: returning %s groups", len(groups))
    return JsonResponse(groups, safe=False)


@staff_member_required
def photo_type_items(request):
    parent_id = request.GET.get("parent_id")
    logger.info("photo_type_items: fetching items for parent_id=%s", parent_id)

    queryset = PhotoTypeItem.objects.filter(is_visible=True)
    if parent_id:
        queryset = queryset.filter(parent_id=parent_id)
    else:
        queryset = queryset.filter(parent__isnull=True)

    items = []
    for node in queryset.order_by("order", "name"):
        items.append(
            {
                "id": node.id,
                "name": node.name,
                "parent_id": node.parent_id,
                "has_children": node.children.filter(is_visible=True).exists(),
                "full_path": node.full_path(),
            }
        )

    logger.info("photo_type_items: returning %s items", len(items))
    return JsonResponse(items, safe=False)


def _serialize_photo_type_tree(node):
    children = [
        _serialize_photo_type_tree(child)
        for child in node.children.all().order_by("order", "name")
    ]
    return {
        "id": node.id,
        "name": node.name,
        "parent_id": node.parent_id,
        "is_visible": node.is_visible,
        "order": node.order,
        "full_path": node.full_path(),
        "children": children,
    }


@staff_member_required
def manage_photo_type_items(request):
    logger.info("manage_photo_type_items: request from user=%s", request.user)

    if not request.user.is_superuser:
        logger.warning(
            "manage_photo_type_items: forbidden access attempt by user=%s",
            request.user,
        )
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)

    roots = PhotoTypeItem.objects.filter(parent__isnull=True).order_by("order", "name")
    logger.info("manage_photo_type_items: returning tree for %s root nodes", len(roots))
    return JsonResponse(
        [_serialize_photo_type_tree(node) for node in roots], safe=False
    )


@staff_member_required
def manage_toggle_photo_type_item(request):
    logger.info("manage_toggle_photo_type_item: request from user=%s", request.user)

    if not request.user.is_superuser:
        logger.warning(
            "manage_toggle_photo_type_item: forbidden access attempt by user=%s",
            request.user,
        )
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)

    # support both JSON and form POSTs; if is_visible not provided, toggle current state
    item_id = None
    is_visible = None
    if request.content_type and request.content_type.startswith("application/json"):
        try:
            data = json.loads(request.body)
            item_id = data.get("id") or data.get("item_id")
            is_visible = data.get("is_visible")
        except Exception:
            logger.exception("manage_toggle_photo_type_item: invalid JSON payload")
            return JsonResponse(
                {"status": "error", "message": "Invalid payload"}, status=400
            )
    else:
        item_id = request.POST.get("item_id") or request.POST.get("id")

    logger.info(
        "manage_toggle_photo_type_item: toggling item_id=%s is_visible=%s",
        item_id,
        is_visible,
    )

    item = PhotoTypeItem.objects.filter(id=item_id).first()
    if not item:
        logger.warning("manage_toggle_photo_type_item: item_id=%s not found", item_id)
        return JsonResponse(
            {"status": "error", "message": "Item not found"}, status=404
        )

    if is_visible is None:
        item.is_visible = not item.is_visible
    else:
        item.is_visible = bool(is_visible)
    item.save()
    logger.info(
        "manage_toggle_photo_type_item: item_id=%s is_visible now=%s",
        item_id,
        item.is_visible,
    )

    return JsonResponse({"status": "ok"})


@staff_member_required
def manage_add_photo_type_item(request):
    logger.info("manage_add_photo_type_item: request from user=%s", request.user)

    if not request.user.is_superuser:
        logger.warning(
            "manage_add_photo_type_item: forbidden access attempt by user=%s",
            request.user,
        )
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)

    try:
        if request.content_type and request.content_type.startswith("application/json"):
            data = json.loads(request.body)
            parent_id = data.get("parent_id")
            name = (data.get("name") or "").strip()
            order = int(data.get("order") or 0)
        else:
            parent_id = request.POST.get("parent_id")
            name = (request.POST.get("name") or "").strip()
            order = int(request.POST.get("order") or 0)
    except Exception:
        logger.exception("manage_add_photo_type_item: invalid payload")
        return JsonResponse(
            {"status": "error", "message": "Invalid payload"}, status=400
        )

    logger.info(
        "manage_add_photo_type_item: creating item name=%s parent_id=%s order=%s",
        name,
        parent_id,
        order,
    )

    if not name:
        logger.warning("manage_add_photo_type_item: name is required but missing")
        return JsonResponse(
            {"status": "error", "message": "Name is required"}, status=400
        )
    if len(name) > 200:
        logger.warning("manage_add_photo_type_item: name too long, length=%s", len(name))
        return JsonResponse({"status": "error", "message": "Name too long"}, status=400)

    parent = None
    if parent_id:
        parent = PhotoTypeItem.objects.filter(id=parent_id).first()
        if not parent:
            logger.warning(
                "manage_add_photo_type_item: parent_id=%s not found", parent_id
            )
            return JsonResponse(
                {"status": "error", "message": "Parent item not found"}, status=404
            )

    obj = PhotoTypeItem.objects.create(
        parent=parent, name=name, is_visible=True, order=order
    )
    logger.info(
        "manage_add_photo_type_item: created item id=%s name=%s parent_id=%s",
        obj.id,
        obj.name,
        obj.parent_id,
    )

    return JsonResponse(
        {"status": "ok", "id": obj.id, "name": obj.name, "parent_id": obj.parent_id}
    )


@staff_member_required
def photo_type_list(request):
    # Deprecated: replaced by photo_type_groups/photo_type_items
    logger.info("photo_type_list: deprecated endpoint called")
    return JsonResponse([], safe=False)


@staff_member_required
def event_list(request):
    logger.info("event_list: endpoint called")
    return JsonResponse([], safe=False)

@staff_member_required
def sponsor_list(request):
    logger.info("sponsor_list: fetching visible sponsor photo configs")

    configs = (
        SponsorPhotoConfig.objects.filter(is_visible_in_photo_upload=True)
        .select_related("sponsor")
        .values("id", "name", "sponsor__organization_name")
    )

    response_data = []
    for config in configs:
        response_data.append(
            {
                "id": config.get("id"),
                "name": config.get("name"),
                "sponsor_name": config.get("sponsor__organization_name") or "",
            }
        )

    logger.info("sponsor_list: returning %s sponsor configs", len(response_data))
    return JsonResponse(response_data, safe=False)

@csrf_exempt
def upload_slum_photos_to_drive(request):
    logger.info("upload_slum_photos_to_drive: request received, method=%s", request.method)

    if request.method == "GET":
        logger.info("upload_slum_photos_to_drive: rendering upload page")
        return render(request, "helpers/photo_upload.html", {
            "default_photo_date": date.today().isoformat(),
            "is_superuser": request.user.is_superuser,
        })

    if request.method != "POST":
        logger.warning("upload_slum_photos_to_drive: invalid method=%s", request.method)
        return JsonResponse({"status": "error", "message": "Only GET and POST requests are allowed."}, status=405)

    slum_id = request.POST.get("slum_id")
    city_id = request.POST.get("city_id")
    photo_type_item_id = request.POST.get("photo_type_item_id")
    sponsor_project_id = request.POST.get("sponsor_project_id")
    project_type = (request.POST.get("project_type") or "").strip()
    project_type_other = (request.POST.get("project_type_other") or "").strip()
    photo_comment = (request.POST.get("photo_comment") or "").strip()
    photo_date = request.POST.get("photo_date")
    is_city_level = str(request.POST.get("is_city_level") or "").lower() in ("1", "true", "on", "yes")
    is_other_upload = str(request.POST.get("is_other_upload") or "").lower() in ("1", "true", "on", "yes")
    custom_folder_name = (request.POST.get("custom_folder_name") or "").strip()

    logger.info(
        "upload_slum_photos_to_drive: payload slum_id=%s city_id=%s photo_type_item_id=%s "
        "sponsor_project_id=%s project_type=%s is_city_level=%s is_other_upload=%s custom_folder_name=%s",
        slum_id, city_id, photo_type_item_id, sponsor_project_id, project_type,
        is_city_level, is_other_upload, custom_folder_name,
    )

    is_city_level, is_other_upload = normalize_upload_scope(is_city_level, is_other_upload, city_id, slum_id, custom_folder_name)

    uploaded_files = collect_uploaded_photos(request.FILES)
    logger.info("upload_slum_photos_to_drive: %s file(s) received", len(uploaded_files))

    if not uploaded_files:
        logger.warning("upload_slum_photos_to_drive: no photos provided")
        return JsonResponse({"status": "error", "message": "At least one photo is required."}, status=400)

    if len(uploaded_files) > 5:
        logger.warning("upload_slum_photos_to_drive: too many files uploaded, count=%s", len(uploaded_files))
        return JsonResponse({"status": "error", "message": "You can upload a maximum of 5 photos at a time."}, status=400)

    if is_city_level and is_other_upload:
        logger.warning("upload_slum_photos_to_drive: both is_city_level and is_other_upload set")
        return JsonResponse({"status": "error", "message": "City level upload and other upload cannot both be enabled."}, status=400)

    if not is_city_level and not is_other_upload and not slum_id:
        logger.warning("upload_slum_photos_to_drive: slum_id missing")
        return JsonResponse({"status": "error", "message": "slum_id is required."}, status=400)

    selected_photo_date, error = validate_photo_date(photo_date)
    if error:
        logger.warning("upload_slum_photos_to_drive: %s (photo_date=%s)", error, photo_date)
        return JsonResponse({"status": "error", "message": error}, status=400)

    project_type_other, error = validate_project_type(project_type, project_type_other)
    if error:
        logger.warning("upload_slum_photos_to_drive: %s (project_type=%s)", error, project_type)
        return JsonResponse({"status": "error", "message": error}, status=400)

    photo_type_item = None
    if not is_other_upload:
        photo_type_item, error = resolve_photo_type_item(photo_type_item_id, is_city_level, city_id)
        if error:
            logger.warning("upload_slum_photos_to_drive: %s (photo_type_item_id=%s)", error, photo_type_item_id)
            return JsonResponse({"status": "error", "message": error}, status=400)
    elif not custom_folder_name:
        logger.warning("upload_slum_photos_to_drive: custom_folder_name missing for other upload")
        return JsonResponse({"status": "error", "message": "Custom folder name is required for other upload."}, status=400)

    photo_type_path = photo_type_item.full_path() if photo_type_item else ""
    sponsor_config = resolve_sponsor_config(sponsor_project_id)
    logger.info("upload_slum_photos_to_drive: starting drive upload for slum_id=%s photo_type_path=%s", slum_id, photo_type_path)

    try:
        result = upload_photos_to_slum_drive_folder(
            slum_id=slum_id if not is_city_level and not is_other_upload else None,
            uploaded_files=uploaded_files,
            project_type=project_type,
            project_type_other=project_type_other,
            photo_type_item=photo_type_item,
            sponsor_config=sponsor_config,
            photo_date=photo_date,
            is_city_level=is_city_level,
            is_other_upload=is_other_upload,
            custom_folder_name=custom_folder_name,
            city_id=city_id if is_city_level else None,
        )
    except ObjectDoesNotExist:
        logger.warning("upload_slum_photos_to_drive: slum not found for slum_id=%s", slum_id)
        return JsonResponse({"status": "error", "message": "Slum not found."}, status=404)
    except ImproperlyConfigured as exc:
        logger.exception("upload_slum_photos_to_drive: service improperly configured")
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)
    except Exception as exc:
        logger.exception("upload_slum_photos_to_drive: photo upload service failed")
        return JsonResponse({"status": "error", "message": "Photo upload service failed.", "details": str(exc)}, status=500)

    logger.info("upload_slum_photos_to_drive: drive upload succeeded for slum_id=%s, %s file(s) processed", slum_id, len(result.get("files", [])))

    slum = Slum.objects.filter(id=slum_id).first()
    if not slum and not is_city_level and not is_other_upload:
        logger.warning("upload_slum_photos_to_drive: slum not found for slum_id=%s after upload", slum_id)
        return JsonResponse({"status": "error", "message": "Slum not found."}, status=404)

    hierarchy = result.get("hierarchy") or []
    hierarchy_path = " / ".join([item for item in hierarchy if item])

    upload_batch = SlumPhotoUpload.objects.create(
        slum=slum,
        project_type=project_type,
        project_type_other=project_type_other,
        photo_type_item=photo_type_item,
        photo_type_item_name=photo_type_item.name if photo_type_item else "",
        photo_type_path=photo_type_path,
        sponsor_config=sponsor_config,
        event_name="",
        uploaded_by=request.user if request.user.is_authenticated else None,
        hierarchy_path=hierarchy_path,
        photo_date=selected_photo_date,
        is_city_level=is_city_level,
        is_other_upload=is_other_upload,
        custom_folder_name=custom_folder_name,
        photo_comment=photo_comment,
    )
    logger.info("upload_slum_photos_to_drive: created upload_batch id=%s", upload_batch.id)

    files_response = save_slum_photos(upload_batch, result.get("files", []))
    logger.info("upload_slum_photos_to_drive: saved %s SlumPhoto record(s) for upload_batch id=%s", len(files_response), upload_batch.id)

    response_data = {
        "upload_batch_id": upload_batch.id,
        "files": files_response,
        "hierarchy": hierarchy,
        "photo_date": selected_photo_date.isoformat(),
        "is_city_level": is_city_level,
        "is_other_upload": is_other_upload,
        "custom_folder_name": custom_folder_name,
        "photo_type_path": photo_type_path,
        "photo_type_item_name": photo_type_item.name if photo_type_item else "",
        "photo_category": result.get("photo_category"),
        "photo_category_label": result.get("photo_category_label"),
        "photo_category_folder": result.get("photo_category_folder"),
        "drive_path_display": result.get("drive_path_display"),
        "project_type": project_type,
        "project_type_other": project_type_other,
        "photo_comment": photo_comment,
    }

    logger.info("upload_slum_photos_to_drive: request completed successfully for upload_batch id=%s", upload_batch.id)
    return JsonResponse({"status": "success", "data": response_data}, status=200)

def send_reminder(
    request,
    to_emails,
    reminder_type,
    template_name,
    subject,
    context,
    cc=None,
    bcc=None,
):
    """Create or update a monthly reminder tracker and send the reminder email."""

    logger.info(
        "send_reminder: reminder_type=%s to_emails=%s", reminder_type, to_emails
    )

    current_date = datetime.now()
    primary_email = to_emails[0]

    tracker, created = ReminderTracker.objects.get_or_create(
        reminder_type=reminder_type,
        month=current_date.month,
        year=current_date.year,
        email=primary_email,
    )
    logger.info(
        "send_reminder: tracker %s for reminder_type=%s email=%s",
        "created" if created else "fetched",
        reminder_type,
        primary_email,
    )

    if tracker.status == "COMPLETED":
        logger.info(
            "send_reminder: tracker already completed for reminder_type=%s email=%s, skipping",
            reminder_type,
            primary_email,
        )
        return

    confirm_path = reverse("confirm_reminder")
    confirm_url = f"{settings.BASE_APP_URL}{confirm_path}?uuid={tracker.uuid}"
    context["confirm_url"] = confirm_url

    plain_message = subject
    message_id = send_email(
        to_emails,
        subject,
        template_name,
        context,
        plain_message,
        tracker.thread_message_id,
        cc,
        bcc,
    )
    logger.info(
        "send_reminder: reminder email sent for reminder_type=%s email=%s message_id=%s",
        reminder_type,
        primary_email,
        message_id,
    )

    if not tracker.thread_message_id:
        tracker.thread_message_id = message_id
    if not tracker.subject:
        tracker.subject = subject

    tracker.recipient_data = {"to": to_emails, "cc": cc or [], "bcc": bcc or []}
    tracker.reminder_sent_count += 1
    tracker.last_reminder_sent_at = timezone.now()
    tracker.save()

    logger.info(
        "send_reminder: tracker updated, reminder_sent_count=%s for reminder_type=%s email=%s",
        tracker.reminder_sent_count,
        reminder_type,
        primary_email,
    )


def confirm_reminder(request):
    """Mark a reminder as completed and notify recipients with a confirmation email."""

    reminder_uuid = request.GET.get("uuid")
    logger.info("confirm_reminder: request received for uuid=%s", reminder_uuid)

    tracker = ReminderTracker.objects.filter(uuid=reminder_uuid).first()

    if not tracker:
        logger.warning("confirm_reminder: no tracker found for uuid=%s", reminder_uuid)
        return HttpResponse("Reminder not found")

    if tracker.status == "COMPLETED":
        logger.info(
            "confirm_reminder: tracker uuid=%s already completed", reminder_uuid
        )
        return HttpResponse("Reminder already completed")

    tracker.status = "COMPLETED"
    tracker.completed_at = timezone.now()
    tracker.save()
    logger.info("confirm_reminder: tracker uuid=%s marked as completed", reminder_uuid)

    context = {
        "DATE_TODAY": datetime.now().strftime("%d %B %Y"),
        "MONTH_NAME": datetime(1900, tracker.month, 1).strftime("%B"),
        "YEAR": tracker.year,
        "COMPLETED_AT": timezone.localtime(tracker.completed_at).strftime(
            "%d %B %Y %I:%M %p"
        ),
    }

    plain_message = "GIS Sync Confirmation"
    recipient_data = tracker.recipient_data or {}

    send_email(
        recipient_data.get("to", []),
        tracker.subject,
        "helpers/gis_confirmation_email.html",
        context,
        plain_message,
        tracker.thread_message_id,
        recipient_data.get("cc", []),
        recipient_data.get("bcc", []),
    )
    logger.info(
        "confirm_reminder: confirmation email sent for uuid=%s to=%s",
        reminder_uuid,
        recipient_data.get("to", []),
    )

    return HttpResponse("Reminder confirmed successfully")


@staff_member_required
def photo_type_tree(request):
    """
    Returns the full PhotoTypeItem tree as nested JSON.
    Used by the flowchart guide on the photo upload page.

    Response format:
    [
        {
            "id": 1,
            "name": "Activity",
            "has_children": true,
            "children": [
                {
                    "id": 5,
                    "name": "Formal activity",
                    "has_children": true,
                    "children": [ ... ]
                },
                ...
            ]
        },
        ...
    ]
    """
    from helpers.models import PhotoTypeItem  # local import in case not at top

    logger.info("photo_type_tree: building full photo type tree")

    def build_node(item):
        children = PhotoTypeItem.objects.filter(parent=item, is_visible=True).order_by(
            "order", "name"
        )
        child_nodes = [build_node(c) for c in children]
        return {
            "id": item.id,
            "name": item.name,
            "has_children": len(child_nodes) > 0,
            "children": child_nodes,
        }

    roots = PhotoTypeItem.objects.filter(parent__isnull=True, is_visible=True).order_by(
        "order", "name"
    )
    tree = [build_node(r) for r in roots]

    logger.info("photo_type_tree: built tree with %s root node(s)", len(tree))

    return JsonResponse(tree, safe=False)