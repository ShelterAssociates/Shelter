from django.db import models
from django.utils import timezone
from jsonfield import JSONField
# Stores OTPs sent for different verification tasks (PDF download, email verification, etc.)
# Each email + task combination will have only one OTP record which gets updated on new request
class OTPVerification(models.Model):
	email = models.EmailField()
	otp = models.CharField(max_length=128)
	task = models.CharField(max_length=50)
	is_verified = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now=True)
	expiry_time = models.DateTimeField()

	class Meta:
		unique_together = ('email','task')

	def is_expired(self):
		return timezone.now() > self.expiry_time


# Stores form data submitted by users before performing actions like downloading a PDF
# Common fields are stored directly, while additional dynamic fields can be stored in JSON
class FormSubmission(models.Model):
	name = models.CharField(max_length=200)
	email = models.EmailField()
	mobile = models.CharField(max_length=15)
	task = models.CharField(max_length=50)
	extra_data = JSONField(blank=True, null=True)
	otp_verified = models.BooleanField(default=False)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.TextField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		indexes = [
			models.Index(fields=['email','task']),
		]

	def __str__(self):
		return f"{self.email} - {self.task}"
