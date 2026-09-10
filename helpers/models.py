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
    slum = models.ForeignKey(
        "master.Slum", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        unique_together = ("email", "task")

    def is_expired(self):
        return timezone.now() > self.expiry_time


# Stores form data submitted by users before performing actions like downloading a PDF
# Common fields are stored directly, while additional dynamic fields can be stored in JSON
class FormSubmission(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    task = models.CharField(max_length=50)
    slum = models.ForeignKey(
        "master.Slum", null=True, blank=True, on_delete=models.SET_NULL
    )
    extra_data = JSONField(blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "task"]),
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


class SponsorPhotoConfig(models.Model):
    """Controls which Sponsors appear in the photo upload tool."""

    sponsor = models.ForeignKey(
        "sponsor.Sponsor",
        on_delete=models.CASCADE,
        related_name="photo_configs",
    )
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="A unique display name shown to users in the photo upload dropdown.",
    )
    is_visible_in_photo_upload = models.BooleanField(
        default=False,
        help_text="If checked, this sponsor appears in the photo upload sponsor dropdown.",
    )

    class Meta:
        verbose_name = "Sponsor Photo Config"
        verbose_name_plural = "Sponsor Photo Configs"

    def __str__(self):
        return "{} - {}".format(
            self.name,
            "Visible" if self.is_visible_in_photo_upload else "Hidden",
        )
class SlumPhotoUpload(models.Model):
    PROJECT_TYPE_CHOICES = (
        ("OHOT", "OHOT"),
        ("MHM", "MHM"),
        ("Housing", "Housing"),
        ("Other", "Other"),
    )

    slum = models.ForeignKey(
        "master.Slum",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="photo_uploads",
    )
    project_type = models.CharField(
        max_length=20, choices=PROJECT_TYPE_CHOICES, default="OHOT"
    )
    project_type_other = models.CharField(max_length=200, blank=True)
    photo_type_item = models.ForeignKey(
        "helpers.PhotoTypeItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    photo_type_item_name = models.CharField(max_length=200, blank=True)
    photo_type_path = models.CharField(max_length=500, blank=True)
    photo_date = models.DateField(null=True, blank=True)
    is_city_level = models.BooleanField(default=False)
    is_other_upload = models.BooleanField(default=False)
    custom_folder_name = models.CharField(max_length=200, blank=True)
    photo_comment = models.TextField(blank=True)
    sponsor_config = models.ForeignKey(
        "helpers.SponsorPhotoConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="photo_uploads",
    )
    event_name = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
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


# ---------------------------------------------------------------------------
# Unified register of every generated download/export across the whole app.
#
# Before this, RIM and GIS exports tracked nothing at all -- state lived only in
# a uuid4 directory name on disk, so a failed export left no trace anywhere and
# nobody could see what had been requested. This is the one table that answers
# "who asked for which download, when, and did it work".
# ---------------------------------------------------------------------------

EXPORT_TYPES = (
    ("photo", "Photo export"),
    ("rim", "RIM data"),
    ("gis", "GIS export"),
)

EXPORT_STATUSES = (
    ("queued", "Queued"),
    ("running", "Running"),
    ("done", "Done"),
    ("failed", "Failed"),
)


class ExportRequest(models.Model):
    """One requested download, of any type.

    Photo exports use this as a real work queue: rows are created `queued` and
    picked up by the run_photo_exports management command. RIM and GIS exports
    still run in their own background threads and use this purely as a record.
    """

    export_type = models.CharField(max_length=20, choices=EXPORT_TYPES)
    status = models.CharField(
        max_length=20, choices=EXPORT_STATUSES, default="queued"
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    email = models.CharField(max_length=254, blank=True)

    # Human-readable description of what was asked for, e.g.
    # "Slum: Ganesh Nagar (412 households, Family Photo + Toilet Photo)".
    scope = models.CharField(max_length=500, blank=True)
    slum = models.ForeignKey(
        "master.Slum", null=True, blank=True, on_delete=models.SET_NULL
    )
    # Type-specific request parameters: photo types, household numbers,
    # financial year, chosen date field, etc.
    params = JSONField(null=True, blank=True)

    item_count = models.IntegerField(default=0)
    bytes_total = models.BigIntegerField(default=0)
    # Absolute path of the generated file. Not a FileField: these are transient
    # artefacts deleted by the nightly cleanup script, and a dangling FileField
    # is worse than a dangling string.
    file_path = models.CharField(max_length=1000, null=True, blank=True)

    # [{"household": "0022", "label": "Family Photo", "error": "..."}]
    failures = JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)

    created_on = models.DateTimeField(default=timezone.now)
    started_on = models.DateTimeField(null=True, blank=True)
    finished_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Export request"
        verbose_name_plural = "Export requests"
        ordering = ("-created_on",)
        indexes = [
            # Exactly what the photo export runner queries.
            models.Index(fields=["status", "created_on"]),
        ]

    def __str__(self):
        return "{} - {} ({})".format(
            self.get_export_type_display(), self.scope or "-", self.status
        )

    @property
    def size_display(self):
        """Human-readable size for the admin list."""
        size = float(self.bytes_total or 0)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return "{:.1f} {}".format(size, unit)
            size /= 1024

    @property
    def failure_count(self):
        return len(self.failures or [])
