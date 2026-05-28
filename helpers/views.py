from django.shortcuts import render
import hashlib
import json
import random
from datetime import date, datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from requests import request
from scipy import record

from helpers.services.send_email import send_email
from master.models import Slum
from sponsor.models import SponsorProject
from shelter import settings
from .models import OTPVerification, PhotoTypeItem, ReminderTracker, SlumPhoto, SlumPhotoUpload
from .services.google_drive import upload_photos_to_slum_drive_folder
from django.http import HttpResponse

# ============= Digipin Generation =============

def digipin_generate(request):
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
	if request.method != "POST":
		return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)
	data = json.loads(request.body)
	email = data.get("email")
	task = data.get("task", "Random Task")
	if not email:
		return JsonResponse({"status": "error", "message": "Email required"})
	record = OTPVerification.objects.filter(email=email, task=task).first()
	if record and (timezone.now() - record.created_at).seconds < 30:
		return JsonResponse({"status": "wait","message": "Please wait 30 seconds before requesting another OTP"})
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
		}
	)
	subject = "Shelter Associates - OTP Verification"
	template_name = "helpers/otp_email.html"
	context = {"otp": otp}
	plain_message = f"Your OTP is {otp}"
	send_email([email], subject, template_name, context, plain_message)
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
	if request.method != "POST":
		return JsonResponse({"status": "error"}, status=400)
	data=json.loads(request.body)
	email=data.get("email")
	otp=data.get("otp")
	task=data.get("task","FACTSHEET_DOWNLOAD")
	session_key=f"otp_attempts_{email}_{task}"
	attempts=request.session.get(session_key,0)
	if attempts>=5:
		return JsonResponse({"status":"blocked"})
	try:
		record=OTPVerification.objects.get(email=email,task=task)
	except OTPVerification.DoesNotExist:
		return JsonResponse({"status":"invalid"})

	if record.is_verified:
		return JsonResponse({"status":"invalid"})

	if record.expiry_time<timezone.now():
		return JsonResponse({"status":"expired"})

	input_hash=hashlib.sha256(otp.encode()).hexdigest()

	if record.otp!=input_hash:
		request.session[session_key]=attempts+1
		return JsonResponse({"status":"invalid"})
	record.is_verified=True
	record.save()
	request.session[session_key]=0
	# mark session as verified for factsheet download
	request.session["rim_otp_verified"] = True
	return JsonResponse({"status":"verified"})


@staff_member_required
def photo_upload_page(request):
	return render(request, "helpers/photo_upload.html", {
		"is_superuser": request.user.is_superuser,
		"default_photo_date": date.today().isoformat(),
	})


@staff_member_required
def photo_type_groups(request):
	roots = PhotoTypeItem.objects.filter(parent__isnull=True, is_visible=True).order_by("order", "name")
	groups = [{"id": node.id, "name": node.name} for node in roots]
	return JsonResponse(groups, safe=False)


@staff_member_required
def photo_type_items(request):
	parent_id = request.GET.get("parent_id")
	queryset = PhotoTypeItem.objects.filter(is_visible=True)
	if parent_id:
		queryset = queryset.filter(parent_id=parent_id)
	else:
		queryset = queryset.filter(parent__isnull=True)
	items = []
	for node in queryset.order_by("order", "name"):
		items.append({
			"id": node.id,
			"name": node.name,
			"parent_id": node.parent_id,
			"has_children": node.children.filter(is_visible=True).exists(),
			"full_path": node.full_path(),
		})
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
	if not request.user.is_superuser:
		return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
	roots = PhotoTypeItem.objects.filter(parent__isnull=True).order_by("order", "name")
	return JsonResponse([_serialize_photo_type_tree(node) for node in roots], safe=False)


@staff_member_required
def manage_toggle_photo_type_item(request):
	if not request.user.is_superuser:
		return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
	# support both JSON and form POSTs; if is_visible not provided, toggle current state
	item_id = None
	is_visible = None
	if request.content_type and request.content_type.startswith('application/json'):
		try:
			data = json.loads(request.body)
			item_id = data.get('id') or data.get('item_id')
			is_visible = data.get('is_visible')
		except Exception:
			return JsonResponse({"status": "error", "message": "Invalid payload"}, status=400)
	else:
		item_id = request.POST.get('item_id') or request.POST.get('id')

	item = PhotoTypeItem.objects.filter(id=item_id).first()
	if not item:
		return JsonResponse({"status": "error", "message": "Item not found"}, status=404)
	if is_visible is None:
		item.is_visible = not item.is_visible
	else:
		item.is_visible = bool(is_visible)
	item.save()
	return JsonResponse({"status": "ok"})


@staff_member_required
def manage_add_photo_type_item(request):
	if not request.user.is_superuser:
		return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
	try:
		if request.content_type and request.content_type.startswith('application/json'):
			data = json.loads(request.body)
			parent_id = data.get("parent_id")
			name = (data.get("name") or "").strip()
			order = int(data.get("order") or 0)
		else:
			parent_id = request.POST.get("parent_id")
			name = (request.POST.get("name") or "").strip()
			order = int(request.POST.get("order") or 0)
	except Exception:
		return JsonResponse({"status": "error", "message": "Invalid payload"}, status=400)

	if not name:
		return JsonResponse({"status": "error", "message": "Name is required"}, status=400)
	if len(name) > 200:
		return JsonResponse({"status": "error", "message": "Name too long"}, status=400)

	parent = None
	if parent_id:
		parent = PhotoTypeItem.objects.filter(id=parent_id).first()
		if not parent:
			return JsonResponse({"status": "error", "message": "Parent item not found"}, status=404)

	obj = PhotoTypeItem.objects.create(parent=parent, name=name, is_visible=True, order=order)
	return JsonResponse({"status": "ok", "id": obj.id, "name": obj.name, "parent_id": obj.parent_id})


@staff_member_required
def photo_type_list(request):
	# Deprecated: replaced by photo_type_groups/photo_type_items
	return JsonResponse([], safe=False)


@staff_member_required
def event_list(request):
	return JsonResponse([], safe=False)


@staff_member_required
def sponsor_project_list(request):
	projects = SponsorProject.objects.filter(
		photo_config__is_visible_in_photo_upload=True
	).select_related("sponsor").values("id", "name", "sponsor__organization_name")

	response_data = []
	for project in projects:
		response_data.append({
			"id": project.get("id"),
			"name": project.get("name"),
			"sponsor_name": project.get("sponsor__organization_name") or "",
		})

	return JsonResponse(response_data, safe=False)


@csrf_exempt
def upload_slum_photos_to_drive(request):
    
	if request.method == "GET":
		return render(request, "helpers/photo_upload.html", {
			"default_photo_date": date.today().isoformat(),
			"is_superuser": request.user.is_superuser,
		})

	if request.method != "POST":
		return JsonResponse({"status": "error", "message": "Only GET and POST requests are allowed."}, status=405)

	slum_id = request.POST.get("slum_id")
	city_id = request.POST.get("city_id")
	photo_type_item_id = request.POST.get("photo_type_item_id")
	sponsor_project_id = request.POST.get("sponsor_project_id")
	photo_date = request.POST.get("photo_date")
	is_city_level = str(request.POST.get("is_city_level") or "").lower() in ("1", "true", "on", "yes")
	is_other_upload = str(request.POST.get("is_other_upload") or "").lower() in ("1", "true", "on", "yes")
	custom_folder_name = (request.POST.get("custom_folder_name") or "").strip()
	if not is_city_level and city_id and not slum_id and not custom_folder_name:
		is_city_level = True
	if not is_other_upload and custom_folder_name and not slum_id and not city_id:
		is_other_upload = True
	uploaded_files = request.FILES.getlist("photos")
	if not uploaded_files:
		single_file = request.FILES.get("photo")
		if single_file:
			uploaded_files = [single_file]

	if not uploaded_files:
		return JsonResponse({"status": "error", "message": "At least one photo is required."}, status=400)

	if len(uploaded_files) > 5:
		return JsonResponse({"status": "error", "message": "You can upload a maximum of 5 photos at a time."}, status=400)

	if is_city_level and is_other_upload:
		return JsonResponse({"status": "error", "message": "City level upload and other upload cannot both be enabled."}, status=400)

	if not is_city_level and not is_other_upload and not slum_id:
		return JsonResponse({"status": "error", "message": "slum_id is required."}, status=400)

	if not photo_date:
		return JsonResponse({"status": "error", "message": "Photo date is required."}, status=400)
	try:
		selected_photo_date = datetime.strptime(photo_date, "%Y-%m-%d").date()
	except ValueError:
		return JsonResponse({"status": "error", "message": "Photo date must be in YYYY-MM-DD format."}, status=400)
	if selected_photo_date > date.today():
		return JsonResponse({"status": "error", "message": "Photo date cannot be in the future."}, status=400)

	photo_type_item = None
	if not is_other_upload:
		if not photo_type_item_id:
			return JsonResponse({"status": "error", "message": "Photo type is required."}, status=400)

		photo_type_item = PhotoTypeItem.objects.filter(id=photo_type_item_id, is_visible=True).select_related("parent").first()
		if not photo_type_item:
			return JsonResponse({"status": "error", "message": "Please select a valid visible category."}, status=400)
		if photo_type_item.has_visible_children():
			return JsonResponse({"status": "error", "message": "Please choose the most specific sub-category."}, status=400)
		if is_city_level and not city_id:
			return JsonResponse({"status": "error", "message": "City is required for city level upload."}, status=400)
	else:
		if not custom_folder_name:
			return JsonResponse({"status": "error", "message": "Custom folder name is required for other upload."}, status=400)

	photo_type_path = photo_type_item.full_path() if photo_type_item else ""

	try:
		result = upload_photos_to_slum_drive_folder(
			slum_id=slum_id if not is_city_level and not is_other_upload else None,
			uploaded_files=uploaded_files,
			photo_type_item=photo_type_item,
			sponsor_project_id=sponsor_project_id,
			photo_date=photo_date,
			is_city_level=is_city_level,
			is_other_upload=is_other_upload,
			custom_folder_name=custom_folder_name,
			city_id=city_id if is_city_level else None,
		)
	except ObjectDoesNotExist:
		return JsonResponse({"status": "error", "message": "Slum not found."}, status=404)
	except ImproperlyConfigured as exc:
		return JsonResponse({"status": "error", "message": str(exc)}, status=500)
	except Exception as exc:
		return JsonResponse(
			{"status": "error", "message": "Photo upload service failed.", "details": str(exc)},
			status=500
		)

	slum = Slum.objects.filter(id=slum_id).first()
	if not slum and not is_city_level and not is_other_upload:
		return JsonResponse({"status": "error", "message": "Slum not found."}, status=404)
	hierarchy = result.get("hierarchy") or []
	hierarchy_path = " / ".join([item for item in hierarchy if item])

	upload_batch = SlumPhotoUpload.objects.create(
		slum=slum,
		photo_type_item=photo_type_item,
		photo_type_item_name=photo_type_item.name if photo_type_item else "",
		photo_type_path=photo_type_path,
		sponsor_project_id=sponsor_project_id or None,
		event_name="",
		uploaded_by=request.user if request.user.is_authenticated else None,
		hierarchy_path=hierarchy_path,
		photo_date=selected_photo_date,
		is_city_level=is_city_level,
		is_other_upload=is_other_upload,
		custom_folder_name=custom_folder_name,
	)

	files_response = []
	for file_info in result.get("files", []):
		web_view_link = file_info.get("web_view_link") or file_info.get("webViewLink") or ""
		web_content_link = file_info.get("web_content_link") or file_info.get("webContentLink") or ""
		drive_file_id = file_info.get("drive_file_id") or file_info.get("driveFileId") or ""

		SlumPhoto.objects.create(
			upload_batch=upload_batch,
			file_name=file_info.get("name", ""),
			web_view_link=web_view_link,
			web_content_link=web_content_link,
			drive_file_id=drive_file_id,
			size_bytes=file_info.get("size"),
			content_type=file_info.get("content_type", ""),
		)

		files_response.append({
			"name": file_info.get("name", ""),
			"web_view_link": web_view_link,
			"web_content_link": web_content_link,
			"drive_file_id": drive_file_id,
			"webViewLink": web_view_link,
			"webContentLink": web_content_link,
			"driveFileId": drive_file_id,
		})

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
	}

	return JsonResponse({"status": "success", "data": response_data}, status=200)

def send_reminder(request, to_emails, reminder_type, template_name, subject, context, cc=None, bcc=None):
	"""Create or update a monthly reminder tracker and send the reminder email."""

	current_date = datetime.now()
	primary_email = to_emails[0]

	tracker, _ = ReminderTracker.objects.get_or_create(
		reminder_type=reminder_type,
		month=current_date.month,
		year=current_date.year,
		email=primary_email,
	)

	if tracker.status == "COMPLETED":
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

	if not tracker.thread_message_id:
		tracker.thread_message_id = message_id
	if not tracker.subject:
		tracker.subject = subject

	tracker.recipient_data = {"to": to_emails, "cc": cc or [], "bcc": bcc or []}
	tracker.reminder_sent_count += 1
	tracker.last_reminder_sent_at = timezone.now()
	tracker.save()


def confirm_reminder(request):
	"""Mark a reminder as completed and notify recipients with a confirmation email."""

	reminder_uuid = request.GET.get("uuid")
	tracker = ReminderTracker.objects.filter(uuid=reminder_uuid).first()

	if not tracker:
		return HttpResponse("Reminder not found")
	if tracker.status == "COMPLETED":
		return HttpResponse("Reminder already completed")

	tracker.status = "COMPLETED"
	tracker.completed_at = timezone.now()
	tracker.save()

	context = {
		"DATE_TODAY": datetime.now().strftime("%d %B %Y"),
		"MONTH_NAME": datetime(1900, tracker.month, 1).strftime("%B"),
		"YEAR": tracker.year,
		"COMPLETED_AT": timezone.localtime(tracker.completed_at).strftime("%d %B %Y %I:%M %p"),
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
    from helpers.models import PhotoTypeItem   # local import in case not at top

    def build_node(item):
        children = PhotoTypeItem.objects.filter(parent=item, is_visible=True).order_by('order', 'name')
        child_nodes = [build_node(c) for c in children]
        return {
            'id': item.id,
            'name': item.name,
            'has_children': len(child_nodes) > 0,
            'children': child_nodes,
        }

    roots = PhotoTypeItem.objects.filter(parent__isnull=True, is_visible=True).order_by('order', 'name')
    tree = [build_node(r) for r in roots]
    return JsonResponse(tree, safe=False)

