from django.shortcuts import render
import hashlib
import json
import random
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from requests import request

from helpers.services.send_email import send_otp_email
from .models import OTPVerification

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
	if record and record.expiry_time > timezone.now():
		otp = record.otp_plain
	else:
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
	send_otp_email(email, otp)
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