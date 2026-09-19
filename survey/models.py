"""Tool-agnostic mirror of survey data: one row per record, answers normalized.

Nothing here knows about AVNI. A provider (avni.provider.AvniProvider today)
turns its own records into survey.contracts.NormalizedRecord; the store writes
them into Record + Answer against the standard Concept dictionary.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

KIND_CHOICES = (
    ("subject", "Subject registration"),
    ("enrolment", "Program enrolment"),
    ("encounter", "Encounter"),
    ("program_encounter", "Program encounter"),
)

DATA_TYPE_CHOICES = (
    ("coded", "Coded"), ("numeric", "Numeric"), ("text", "Text"), ("date", "Date"),
    ("datetime", "Date and time"), ("time", "Time"), ("media", "Media"),
    ("location", "Location"), ("group", "Question group"), ("reference", "Reference"),
    ("answer", "Answer only"), ("unknown", "Unknown"),
)

SOURCE_CHOICES = (("catalog", "Form catalog"), ("observed", "Seen in a record"))


class Concept(models.Model):
    """One standard question or answer, shared by every provider."""

    key = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=500, db_index=True)
    data_type = models.CharField(max_length=30, choices=DATA_TYPE_CHOICES, default="unknown")
    is_question = models.BooleanField(default=False)
    is_answer = models.BooleanField(default=False)
    sa_text = models.CharField(max_length=500, blank=True, help_text="Text reports and exports should show")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="observed")
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "survey_concept"
        ordering = ("key",)

    def __str__(self):
        return self.key


class ConceptAlias(models.Model):
    """How one provider spells a concept: its own id and name."""

    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="aliases")
    provider = models.CharField(max_length=30)
    external_id = models.CharField(max_length=200, blank=True)
    external_name = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "survey_concept_alias"
        ordering = ("provider", "external_name")
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                condition=~Q(external_id=""),
                name="survey_alias_provider_id",
            ),
            models.UniqueConstraint(
                fields=["provider", "external_name"],
                condition=~Q(external_name=""),
                name="survey_alias_provider_name",
            ),
        ]

    def __str__(self):
        return "{}:{}".format(self.provider, self.external_name or self.external_id)


class SlumAlias(models.Model):
    """How one provider identifies a slum: its own id (AVNI: the AddressLevel uuid)."""

    slum = models.ForeignKey("master.Slum", on_delete=models.CASCADE, related_name="aliases")
    provider = models.CharField(max_length=30)
    external_id = models.CharField(max_length=200)
    external_name = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "survey_slum_alias"
        unique_together = (("slum", "provider"), ("provider", "external_id"))
        ordering = ("provider", "slum")
        verbose_name = "Slum alias"
        verbose_name_plural = "Slum aliases"

    def __str__(self):
        return "{}:{} -> {}".format(self.provider, self.external_id, self.slum)


class SlumDataVersion(models.Model):
    """A slum's data starts again from `started_on`; earlier versions are frozen."""

    slum = models.ForeignKey("master.Slum", on_delete=models.CASCADE, related_name="survey_versions")
    version = models.PositiveSmallIntegerField()
    started_on = models.DateTimeField()
    note = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "survey_slum_data_version"
        unique_together = ("slum", "version")
        ordering = ("slum", "version")
        verbose_name = "Slum data version"

    def __str__(self):
        return "{} v{}".format(self.slum, self.version)


class SyncSwitch(models.Model):
    """Admin on/off for one form of one subject type, with a subject-level parent."""

    provider = models.CharField(max_length=30)
    subject_type = models.CharField(max_length=100)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    program = models.CharField(max_length=300, blank=True)
    encounter_type = models.CharField(max_length=300, blank=True)
    label = models.CharField(max_length=300, blank=True)
    form_external_id = models.CharField(max_length=200, blank=True)
    is_enabled = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True, help_text="Still present in the provider's form catalog")

    class Meta:
        db_table = "survey_sync_switch"
        unique_together = ("provider", "subject_type", "kind", "program", "encounter_type")
        ordering = ("subject_type", "kind", "program", "encounter_type")
        verbose_name = "Sync switch"
        verbose_name_plural = "Sync switches"

    def __str__(self):
        parts = [self.subject_type, self.kind, self.program, self.encounter_type]
        return " / ".join(part for part in parts if part)


class Record(models.Model):
    """One provider record (registration, enrolment, encounter) at one data version."""

    provider = models.CharField(max_length=30)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    external_id = models.CharField(max_length=200, db_index=True)
    version = models.PositiveSmallIntegerField(default=1)

    subject_external_id = models.CharField(max_length=200, db_index=True, blank=True)
    subject_type = models.CharField(max_length=100, blank=True)
    program = models.CharField(max_length=300, blank=True)
    encounter_type = models.CharField(max_length=300, blank=True)
    form_external_id = models.CharField(max_length=200, blank=True)
    form_name = models.CharField(max_length=300, blank=True)

    household = models.ForeignKey(
        "graphs.HouseholdData", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="survey_records",
    )
    slum = models.ForeignKey("master.Slum", on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey("master.City", on_delete=models.SET_NULL, null=True, blank=True)
    slum_name = models.CharField(max_length=300, blank=True)
    household_number = models.CharField(max_length=20, blank=True, db_index=True)

    record_datetime = models.DateTimeField(null=True, blank=True, db_index=True)
    earliest_scheduled = models.DateTimeField(null=True, blank=True)
    max_scheduled = models.DateTimeField(null=True, blank=True)
    cancel_datetime = models.DateTimeField(null=True, blank=True)
    exit_datetime = models.DateTimeField(null=True, blank=True)

    is_voided = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, blank=True)
    last_modified_at = models.DateTimeField(null=True, blank=True)
    synced_on = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "survey_record"
        ordering = ("-record_datetime", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id", "version"],
                name="survey_record_external_version",
            ),
            models.UniqueConstraint(
                fields=["slum", "household_number", "version"],
                condition=Q(kind="subject", is_voided=False, slum__isnull=False) & ~Q(household_number=""),
                name="survey_record_one_active_household",
            ),
        ]
        indexes = [
            models.Index(fields=["household", "kind", "encounter_type"], name="survey_rec_household_idx"),
            models.Index(fields=["kind", "encounter_type", "record_datetime"], name="survey_rec_kind_date_idx"),
        ]

    def __str__(self):
        return "{} {} {}".format(self.kind, self.encounter_type or self.subject_type, self.external_id)

    @property
    def is_filled(self):
        """A done visit: not cancelled and carrying its own date."""
        return self.cancel_datetime is None and self.record_datetime is not None

    def answers_by_key(self):
        """{concept key: value | [values] | [{child key: value}, ...]} for this record."""
        flat = {}
        groups = {}
        rows = self.answers.select_related("question", "group", "answer").order_by("position", "id")
        for row in rows:
            if row.group_id:
                entry = groups.setdefault(row.group.key, {}).setdefault(row.repeat_index, {})
                _add_answer(entry, row.question.key, row.value())
            else:
                _add_answer(flat, row.question.key, row.value())
        for group_key, repeats in groups.items():
            flat[group_key] = [repeats[index] for index in sorted(repeats)]
        return flat


def _add_answer(bucket, key, value):
    """Second and later answers to the same question turn the entry into a list."""
    if key not in bucket:
        bucket[key] = value
    elif isinstance(bucket[key], list):
        bucket[key].append(value)
    else:
        bucket[key] = [bucket[key], value]


class Answer(models.Model):
    """One answer to one question of one record."""

    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Concept, on_delete=models.PROTECT, related_name="asked_in")
    group = models.ForeignKey(
        Concept, on_delete=models.PROTECT, null=True, blank=True, related_name="groups_in"
    )
    repeat_index = models.PositiveSmallIntegerField(default=0)
    answer = models.ForeignKey(
        Concept, on_delete=models.PROTECT, null=True, blank=True, related_name="answered_in"
    )
    value_text = models.TextField(blank=True)
    value_number = models.FloatField(null=True, blank=True)
    value_date = models.DateTimeField(null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "survey_answer"
        ordering = ("record", "position", "id")
        indexes = [models.Index(fields=["question", "answer"], name="survey_answer_q_a_idx")]

    def __str__(self):
        return "{} = {}".format(self.question_id, self.value_text[:50])

    def value(self):
        if self.value_number is not None:
            return self.value_number
        if self.value_date is not None:
            return self.value_date
        return self.value_text
