from django.db import models
from django.conf import settings
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


class PhotoTypeItem(models.Model):
	name = models.CharField(max_length=200)
	parent = models.ForeignKey(
		"self",
		null=True,
		blank=True,
		related_name="children",
		on_delete=models.CASCADE,
	)
	is_visible = models.BooleanField(default=True)
	order = models.PositiveIntegerField(default=0)

	class Meta:
		ordering = ["parent_id", "order", "name"]
		verbose_name = "Photo type"
		verbose_name_plural = "Photo types"

	def __str__(self):
		return self.full_path()

	def path_nodes(self):
		nodes = []
		current = self
		while current is not None:
			nodes.append(current)
			current = current.parent
		nodes.reverse()
		return nodes

	def full_path(self):
		return " / ".join(node.name for node in self.path_nodes())

	def has_visible_children(self):
		return self.children.filter(is_visible=True).exists()


class SponsorProjectPhotoConfig(models.Model):
	"""Controls which SponsorProjects appear in the photo upload tool."""
	sponsor_project = models.OneToOneField(
		"sponsor.SponsorProject",
		on_delete=models.CASCADE,
		related_name="photo_config",
	)
	is_visible_in_photo_upload = models.BooleanField(
		default=False,
		help_text="If checked, this project appears in the photo upload sponsor dropdown.",
	)

	class Meta:
		verbose_name = "Sponsor Project Photo Config"
		verbose_name_plural = "Sponsor Project Photo Configs"

	def __str__(self):
		return "{} - {}".format(
			self.sponsor_project.name,
			"Visible" if self.is_visible_in_photo_upload else "Hidden",
		)



class SlumPhotoUpload(models.Model):
	slum = models.ForeignKey("master.Slum", on_delete=models.CASCADE, related_name="photo_uploads")
	photo_type_item = models.ForeignKey(
		"helpers.PhotoTypeItem",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
	)
	photo_type_item_name = models.CharField(max_length=200, blank=True)
	photo_type_path = models.CharField(max_length=500, blank=True)
	sponsor_project = models.ForeignKey(
		"sponsor.SponsorProject",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="photo_uploads",
	)
	event_name = models.CharField(max_length=200, blank=True)
	uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
	uploaded_at = models.DateTimeField(auto_now_add=True)
	hierarchy_path = models.CharField(max_length=500, blank=True)


class SlumPhoto(models.Model):
	upload_batch = models.ForeignKey(
		"helpers.SlumPhotoUpload", on_delete=models.CASCADE, related_name="files"
	)
	file_name = models.CharField(max_length=300)
	web_view_link = models.CharField(max_length=1000, blank=True)
	web_content_link = models.CharField(max_length=1000, blank=True)
	drive_file_id = models.CharField(max_length=200, blank=True)
	size_bytes = models.BigIntegerField(null=True, blank=True)
	content_type = models.CharField(max_length=100, blank=True)

	class Meta:
		verbose_name = "Slum Photo"
		verbose_name_plural = "Slum Photos"

	def __str__(self):
		return f"{self.upload_batch} - {self.file_name}"