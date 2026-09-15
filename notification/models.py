from django.db import models
from django.utils import timezone
from jsonfield import JSONField

RUNNER_CHOICES = (("internal", "Internal"), ("external", "External"))

RUN_STATUSES = (
    ("running", "Running"),
    ("success", "Success"),
    ("partial", "Partial"),
    ("failed", "Failed"),
    ("crashed", "Crashed"),
)

STEP_STATUSES = (
    ("running", "Running"),
    ("success", "Success"),
    ("partial", "Partial"),
    ("failed", "Failed"),
    ("disabled", "Disabled in admin"),
)

TRIGGERS = (("cron", "Cron"), ("manual", "Manual"), ("chained", "Chained"))

RECIPIENT_KINDS = (("to", "To"), ("cc", "Cc"), ("bcc", "Bcc"))

DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class JobDefinition(models.Model):
    """A scheduled job the digest knows about, with the schedule it is expected on."""

    key = models.SlugField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    is_active = models.BooleanField(
        default=True,
        help_text="Off = the job does nothing when cron fires it, and the digest "
        "stops expecting it. Turn back on to resume; no code change needed.",
    )
    runner = models.CharField(max_length=20, choices=RUNNER_CHOICES, default="internal")

    expected_times = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated 24h times this job should start, e.g. 02:00,23:00. "
        "Blank means the digest never reports it as missed.",
    )
    expected_days = models.CharField(
        max_length=100,
        default="*",
        help_text="* for every day, or comma-separated mon,tue,wed,thu,fri,sat,sun.",
    )
    expected_days_of_month = models.CharField(
        max_length=100,
        blank=True,
        help_text="Comma-separated days of the month, e.g. 1,16 for a run every "
        "fortnight. Blank means any day.",
    )
    grace_minutes = models.PositiveIntegerField(
        default=90, help_text="How late a start may be before it counts as missed."
    )
    max_runtime_minutes = models.PositiveIntegerField(
        default=360, help_text="A run still going after this is reported as crashed."
    )

    include_in_digest = models.BooleanField(default=True)
    alert_on_failure = models.BooleanField(default=True)
    failure_alert_cooldown_minutes = models.PositiveIntegerField(default=0)

    thread_message_id = models.TextField(null=True, blank=True)
    last_digest_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("display_name",)
        verbose_name = "Job definition"

    def __str__(self):
        return self.display_name or self.key

    def expected_time_list(self):
        """[(hour, minute), ...] parsed from expected_times, bad entries skipped."""
        times = []
        for chunk in self.expected_times.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                hour, minute = chunk.split(":")
                times.append((int(hour), int(minute)))
            except ValueError:
                continue
        return times

    def expected_day_set(self):
        value = (self.expected_days or "*").strip()
        if value == "*":
            return set(DAY_KEYS)
        return {d.strip().lower() for d in value.split(",") if d.strip()}

    def disabled_steps(self):
        return set(
            self.step_configs.filter(is_enabled=False).values_list("step_name", flat=True)
        )

    def expected_month_day_set(self):
        """Days of the month this job runs on. Empty set means every day."""
        days = set()
        for chunk in (self.expected_days_of_month or "").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                days.add(int(chunk))
            except ValueError:
                continue
        return days


class JobStepConfig(models.Model):
    """Per-step on/off switch for a job, edited inline on the job in admin."""

    job = models.ForeignKey(
        JobDefinition, on_delete=models.CASCADE, related_name="step_configs"
    )
    step_name = models.CharField(max_length=200)
    is_enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("job", "step_name")
        ordering = ("job", "order", "step_name")
        verbose_name = "Job step switch"
        verbose_name_plural = "Job step switches"

    def __str__(self):
        return "{} / {} ({})".format(
            self.job.key, self.step_name, "on" if self.is_enabled else "off"
        )


class EmailContact(models.Model):
    """The one address book. Every outbound address in the app resolves to a row here."""

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Unchecking removes this address from every mail it is on.",
    )
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Email contact"

    def __str__(self):
        return "{} <{}>".format(self.name, self.email)


class EmailPurpose(models.Model):
    """A kind of outbound mail, e.g. job_digest or gis_reminder."""

    key = models.SlugField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_name",)
        verbose_name = "Email purpose"

    def __str__(self):
        return self.display_name or self.key


class EmailRecipient(models.Model):
    """Puts one contact on one purpose, as to/cc/bcc."""

    purpose = models.ForeignKey(
        EmailPurpose, on_delete=models.CASCADE, related_name="recipients"
    )
    contact = models.ForeignKey(
        EmailContact, on_delete=models.CASCADE, related_name="subscriptions"
    )
    kind = models.CharField(max_length=3, choices=RECIPIENT_KINDS, default="to")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("purpose", "contact", "kind")
        ordering = ("purpose", "kind", "contact__name")
        verbose_name = "Email recipient"

    def __str__(self):
        return "{} - {} ({})".format(self.purpose, self.contact.email, self.kind)


class JobRun(models.Model):
    """One invocation of a job."""

    job = models.ForeignKey(
        JobDefinition, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="runs",
    )
    job_key = models.SlugField(max_length=100)
    parent_run = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )

    status = models.CharField(max_length=20, choices=RUN_STATUSES, default="running")
    trigger = models.CharField(max_length=20, choices=TRIGGERS, default="cron")
    hostname = models.CharField(max_length=200, blank=True)
    pid = models.IntegerField(null=True, blank=True)

    started_on = models.DateTimeField(default=timezone.now)
    finished_on = models.DateTimeField(null=True, blank=True)

    records_total = models.IntegerField(default=0)
    records_ok = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)

    window_label = models.CharField(max_length=200, blank=True)
    error = models.TextField(null=True, blank=True)
    detail_file_path = models.CharField(max_length=1000, null=True, blank=True)

    alert_sent_at = models.DateTimeField(null=True, blank=True)
    included_in_digest_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-started_on",)
        indexes = [models.Index(fields=["job_key", "started_on"])]

    def __str__(self):
        return "{} - {} ({})".format(self.job_key, self.started_on, self.status)

    @property
    def records_skipped(self):
        return max(self.records_total - self.records_ok - self.records_failed, 0)

    @property
    def duration_display(self):
        if not self.finished_on:
            return "-"
        seconds = int((self.finished_on - self.started_on).total_seconds())
        return "{}m {}s".format(seconds // 60, seconds % 60)


class JobStep(models.Model):
    """One unit of work inside a run, typically a single sync method."""

    run = models.ForeignKey(JobRun, on_delete=models.CASCADE, related_name="steps")
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STEP_STATUSES, default="running")

    started_on = models.DateTimeField(default=timezone.now)
    finished_on = models.DateTimeField(null=True, blank=True)

    records_total = models.IntegerField(default=0)
    records_ok = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    records_skipped = models.IntegerField(default=0)

    error = models.TextField(null=True, blank=True)
    sample_failures = JSONField(null=True, blank=True)
    extras = JSONField(null=True, blank=True)

    class Meta:
        ordering = ("run", "order")

    def __str__(self):
        return "{} / {}".format(self.run.job_key, self.name)

    @property
    def failure_count(self):
        return len(self.sample_failures or [])


class JobStepCityStat(models.Model):
    """Per-city rollup for one step. This is what the digest body renders."""

    step = models.ForeignKey(JobStep, on_delete=models.CASCADE, related_name="city_stats")
    city = models.ForeignKey(
        "master.City", null=True, blank=True, on_delete=models.SET_NULL
    )
    city_name = models.CharField(max_length=200)

    records_ok = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    records_skipped = models.IntegerField(default=0)

    class Meta:
        unique_together = ("step", "city_name")
        ordering = ("city_name",)
        verbose_name = "Job step city stat"

    def __str__(self):
        return "{} - {}".format(self.city_name, self.step.name)


REQUEST_STATUSES = (
    ("queued", "Queued"),
    ("running", "Running"),
    ("done", "Done"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
)


class JobRequest(models.Model):
    """A job someone asked for (console button, admin, shell), waiting for the queue runner.

    The runner claims due requests oldest-first, executes them as a JobRun and
    links the two. `dedupe_key` lets repeat requests merge into one pending row.
    """

    job_key = models.SlugField(max_length=100)
    params = JSONField(null=True, blank=True)
    requested_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="job_requests"
    )
    status = models.CharField(max_length=20, choices=REQUEST_STATUSES, default="queued")
    scheduled_for = models.DateTimeField(default=timezone.now)
    dedupe_key = models.CharField(max_length=200, blank=True, db_index=True)
    job_run = models.ForeignKey(
        JobRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="requests"
    )
    summary = models.TextField(blank=True)
    error = models.TextField(null=True, blank=True)
    created_on = models.DateTimeField(default=timezone.now)
    started_on = models.DateTimeField(null=True, blank=True)
    finished_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_on",)
        indexes = [models.Index(fields=["status", "scheduled_for"])]

    def __str__(self):
        return "{} #{} ({})".format(self.job_key, self.pk, self.status)

    @property
    def is_pending(self):
        return self.status in ("queued", "running")

    @property
    def requested_by_label(self):
        user = self.requested_by
        if user is None:
            return "system"
        return "{} (id {})".format(user.get_username(), user.pk)
