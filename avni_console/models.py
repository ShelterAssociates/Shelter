"""One uploaded spreadsheet to push into AVNI, and what happened to it."""

import os

from django.conf import settings
from django.db import models
from django.utils import timezone
from jsonfield import JSONField

BULK_STATUSES = (
    ("draft", "Draft (uploaded, not queued)"),
    ("queued", "Queued"),
    ("running", "Running"),
    ("done", "Done"),
    ("failed", "Failed"),
)

LEVELS = (
    ("registration", "The subject itself"),
    ("enrolment", "A program enrolment"),
    ("program_encounter", "A program encounter"),
    ("encounter", "An encounter"),
)


def upload_path(bulk_update, filename):
    directory = getattr(settings, "AVNI_BULK_UPLOAD_DIR_NAME", "avni_bulk_updates")
    stamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(directory, stamp, os.path.basename(filename))


class BulkUpdate(models.Model):
    requested_by = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL)
    form = models.ForeignKey("avni.AvniForm", on_delete=models.PROTECT)
    subject_type = models.CharField(max_length=300)
    level = models.CharField(max_length=30, choices=LEVELS)
    program = models.CharField(max_length=300, blank=True)
    encounter_type = models.CharField(max_length=300, blank=True)

    file = models.FileField(upload_to=upload_path)
    original_name = models.CharField(max_length=300)
    headers = JSONField(null=True, blank=True)
    header_map = JSONField(null=True, blank=True, help_text="Spreadsheet header -> concept name chosen in the preview")
    row_count = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=BULK_STATUSES, default="draft")
    dry_run = models.BooleanField(default=True)
    job_request = models.ForeignKey("notification.JobRequest", null=True, blank=True, on_delete=models.SET_NULL)
    result_file_path = models.CharField(max_length=1000, blank=True)
    summary = models.TextField(blank=True)
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_on",)
        verbose_name = "AVNI bulk update"

    def __str__(self):
        return "{} -> {} ({})".format(self.original_name, self.form, self.status)

    @property
    def target_label(self):
        parts = [self.subject_type, self.get_level_display().lower(), self.program, self.encounter_type]
        return " / ".join(part for part in parts if part)
