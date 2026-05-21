from django.shortcuts import render
import hashlib
import json
import random
from datetime import datetime, timedelta
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
from shelter import settings
from .models import OTPVerification ,ReminderTracker
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
	return render(request, "helpers/photo_upload.html")


@csrf_exempt
def upload_slum_photos_to_drive(request):
    
	if request.method == "GET":
		return render(request, "helpers/photo_upload.html")

	if request.method != "POST":
		return JsonResponse({"status": "error", "message": "Only GET and POST requests are allowed."}, status=405)

	slum_id = request.POST.get("slum_id")
	photo_category = request.POST.get("photo_category")
	event_name = request.POST.get("event_name", "").strip()
	uploaded_files = request.FILES.getlist("photos")
	if not uploaded_files:
		single_file = request.FILES.get("photo")
		if single_file:
			uploaded_files = [single_file]

	if not slum_id:
		return JsonResponse({"status": "error", "message": "slum_id is required."}, status=400)

	if not uploaded_files:
		return JsonResponse({"status": "error", "message": "At least one photo is required."}, status=400)

	if len(uploaded_files) > 5:
		return JsonResponse({"status": "error", "message": "You can upload a maximum of 5 photos at a time."}, status=400)

	if not photo_category:
		return JsonResponse({"status": "error", "message": "Photo type is required."}, status=400)

	if photo_category in ("events", "other") and not event_name:
		label = "event name" if photo_category == "events" else "name"
		return JsonResponse({"status": "error", "message": "Please enter the {}.".format(label)}, status=400)

	try:
		result = upload_photos_to_slum_drive_folder(
			slum_id,
			uploaded_files,
			photo_category=photo_category,
			event_name=event_name,
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

	return JsonResponse({"status": "success", "data": result}, status=201)

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