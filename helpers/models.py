from django.db import models
from django.utils import timezone
from jsonfield import JSONField
import uuid
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


class ReminderTracker(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    STATUS_CHOICES = (("PENDING", "Pending"), ("COMPLETED", "Completed"))
    reminder_type = models.CharField(max_length=100)
    month = models.IntegerField()
    year = models.IntegerField()
    email = models.EmailField()
    subject = models.TextField(null=True, blank=True)
    recipient_data = JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    reminder_sent_count = models.IntegerField(default=0)
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    thread_message_id = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "reminder_tracker"
        unique_together = ("reminder_type", "month", "year", "email")

    def __str__(self):
        return f"{self.reminder_type} - {self.month}/{self.year} - {self.email}"