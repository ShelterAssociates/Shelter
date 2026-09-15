import os
import subprocess
import sys
from datetime import timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.utils import timezone

from .models import (
    EmailContact,
    EmailPurpose,
    EmailRecipient,
    JobDefinition,
    JobRequest,
    JobRun,
    JobStep,
    JobStepCityStat,
    JobStepConfig,
)


class EmailRecipientInline(admin.TabularInline):
    model = EmailRecipient
    extra = 1
    autocomplete_fields = ("contact",)


@admin.register(EmailContact)
class EmailContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "is_active", "purpose_list")
    list_filter = ("is_active",)
    search_fields = ("name", "email", "notes")

    def get_form(self, request, obj=None, **kwargs):
        form = super(EmailContactAdmin, self).get_form(request, obj, **kwargs)
        if "email" in form.base_fields:
            form.base_fields["email"].help_text = (
                "Some of these mails carry internal-only data: household numbers, "
                "slum names and error traces. Only add addresses cleared to see "
                "mastersheet data."
            )
        return form

    def purpose_list(self, obj):
        return ", ".join(
            sorted(
                {
                    "{} ({})".format(s.purpose.key, s.kind)
                    for s in obj.subscriptions.filter(is_active=True)
                }
            )
        ) or "-"

    purpose_list.short_description = "Subscribed to"


@admin.register(EmailPurpose)
class EmailPurposeAdmin(admin.ModelAdmin):
    list_display = ("display_name", "key", "is_active", "recipient_summary")
    list_filter = ("is_active",)
    search_fields = ("key", "display_name", "description")
    prepopulated_fields = {"key": ("display_name",)}
    inlines = [EmailRecipientInline]

    def recipient_summary(self, obj):
        rows = obj.recipients.filter(is_active=True, contact__is_active=True)
        counts = {}
        for row in rows:
            counts[row.kind] = counts.get(row.kind, 0) + 1
        return ", ".join("{} {}".format(v, k) for k, v in sorted(counts.items())) or "-"

    recipient_summary.short_description = "Recipients"


@admin.register(EmailRecipient)
class EmailRecipientAdmin(admin.ModelAdmin):
    list_display = ("purpose", "contact", "kind", "is_active")
    list_filter = ("purpose", "kind", "is_active")
    search_fields = ("contact__name", "contact__email", "purpose__key")
    autocomplete_fields = ("contact", "purpose")


class JobStepConfigInline(admin.TabularInline):
    model = JobStepConfig
    extra = 0
    fields = ("step_name", "is_enabled", "order")
    verbose_name_plural = "Step switches (untick to skip a step; rows appear after the first run)"


@admin.register(JobDefinition)
class JobDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "key",
        "is_active",
        "expected_times",
        "expected_days",
        "expected_days_of_month",
        "last_run",
        "include_in_digest",
        "alert_on_failure",
    )
    list_editable = ("is_active",)
    list_filter = ("is_active", "include_in_digest", "alert_on_failure", "runner")
    search_fields = ("key", "display_name")
    prepopulated_fields = {"key": ("display_name",)}
    inlines = [JobStepConfigInline]
    actions = ["run_now"]

    def last_run(self, obj):
        run = obj.runs.order_by("-started_on").first()
        if run is None:
            return "-"
        return "{} ({})".format(
            timezone.localtime(run.started_on).strftime("%d %b %H:%M"), run.status
        )

    last_run.short_description = "Last run"

    def run_now(self, request, queryset):
        """Launch run_job for each selected job as a detached process."""
        for job in queryset:
            if job.runner != "internal":
                self.message_user(
                    request, "{} is an external job; run its script instead.".format(job),
                    messages.WARNING,
                )
                continue
            if not job.is_active:
                self.message_user(
                    request, "{} is switched off; enable it first.".format(job),
                    messages.WARNING,
                )
                continue
            stale = timezone.now() - timedelta(minutes=job.max_runtime_minutes)
            if job.runs.filter(status="running", started_on__gte=stale).exists():
                self.message_user(
                    request, "{} is already running.".format(job), messages.WARNING
                )
                continue
            run_id = _launch_job(job.key)
            self.message_user(
                request,
                "{} started (pid {}). Watch it under Job runs; you will be emailed "
                "if it fails.".format(job, run_id),
                messages.SUCCESS,
            )

    run_now.short_description = "Run selected jobs now"


def _launch_job(key):
    log_dir = os.path.join(settings.PARENT_DIR, "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    log_path = os.path.join(
        log_dir, "manual_{}_{}.log".format(key, timezone.localtime().strftime("%Y%m%d_%H%M%S"))
    )
    with open(log_path, "ab") as log:
        proc = subprocess.Popen(
            [sys.executable, os.path.join(settings.BASE_DIR, "manage.py"),
             "run_job", key, "--trigger", "manual"],
            cwd=settings.BASE_DIR, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return proc.pid


class JobStepCityStatInline(admin.TabularInline):
    model = JobStepCityStat
    extra = 0
    can_delete = False
    readonly_fields = ("city_name", "records_ok", "records_failed", "records_skipped")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(JobStep)
class JobStepAdmin(admin.ModelAdmin):
    list_display = (
        "run",
        "name",
        "status",
        "records_total",
        "records_ok",
        "records_failed",
        "records_skipped",
    )
    list_filter = ("status", "name")
    search_fields = ("name", "run__job_key")
    inlines = [JobStepCityStatInline]
    readonly_fields = tuple(f.name for f in JobStep._meta.fields)

    def has_add_permission(self, request):
        return False


class JobStepInline(admin.TabularInline):
    model = JobStep
    extra = 0
    can_delete = False
    show_change_link = True
    fields = (
        "name",
        "status",
        "records_total",
        "records_ok",
        "records_failed",
        "records_skipped",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = (
        "job_key",
        "status",
        "started_on",
        "duration_display",
        "records_total",
        "records_ok",
        "records_failed",
        "window_label",
    )
    list_filter = ("status", "job_key", "trigger")
    search_fields = ("job_key", "error")
    date_hierarchy = "started_on"
    inlines = [JobStepInline]
    readonly_fields = tuple(f.name for f in JobRun._meta.fields) + ("duration_display",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(JobRequest)
class JobRequestAdmin(admin.ModelAdmin):
    list_display = ("job_key", "status", "requested_by", "scheduled_for", "created_on", "finished_on", "summary")
    list_filter = ("status", "job_key")
    search_fields = ("job_key", "dedupe_key", "error", "requested_by__username")
    date_hierarchy = "created_on"
    readonly_fields = tuple(f.name for f in JobRequest._meta.fields)
    actions = ["requeue", "cancel"]

    def has_add_permission(self, request):
        return False

    def requeue(self, request, queryset):
        """Put finished requests back in the queue, due now."""
        count = 0
        for job_request in queryset.exclude(status__in=("queued", "running")):
            job_request.status = "queued"
            job_request.scheduled_for = timezone.now()
            job_request.error = None
            job_request.summary = ""
            job_request.job_run = None
            job_request.started_on = None
            job_request.finished_on = None
            job_request.save()
            count += 1
        self.message_user(request, "{} request(s) queued again.".format(count), messages.SUCCESS)

    requeue.short_description = "Queue selected requests again"

    def cancel(self, request, queryset):
        count = queryset.filter(status="queued").update(status="cancelled", finished_on=timezone.now())
        self.message_user(request, "{} queued request(s) cancelled.".format(count), messages.SUCCESS)

    cancel.short_description = "Cancel selected queued requests"
