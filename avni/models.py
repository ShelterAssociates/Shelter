"""Cached AVNI form definitions: which forms exist, what they are for, what they ask."""

from django.db import models
from django.utils import timezone
from jsonfield import JSONField

# Form types the console offers for bulk update; cancellation/exit forms are not.
FORM_TYPES = (
    ("IndividualProfile", "Subject registration"),
    ("ProgramEnrolment", "Program enrolment"),
    ("ProgramEncounter", "Program encounter"),
    ("Encounter", "Encounter"),
)


class AvniForm(models.Model):
    uuid = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=300)
    form_type = models.CharField(max_length=60, choices=FORM_TYPES)
    definition = JSONField(null=True, blank=True)
    fetched_on = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "AVNI form"

    def __str__(self):
        return "{} ({})".format(self.name, self.get_form_type_display())


class AvniFormMapping(models.Model):
    """Which subject type (and program / encounter type) a form belongs to."""

    uuid = models.CharField(max_length=100, unique=True)
    form = models.ForeignKey(AvniForm, on_delete=models.CASCADE, related_name="mappings")
    subject_type = models.CharField(max_length=300)
    program = models.CharField(max_length=300, blank=True)
    encounter_type = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("subject_type", "program", "encounter_type")
        verbose_name = "AVNI form mapping"

    def __str__(self):
        parts = [self.subject_type, self.program, self.encounter_type]
        return " / ".join(part for part in parts if part) + " -> " + self.form.name


class AvniFormQuestion(models.Model):
    """One question of a form: the name the team sees and the concept name AVNI needs."""

    form = models.ForeignKey(AvniForm, on_delete=models.CASCADE, related_name="questions")
    uuid = models.CharField(max_length=100)
    parent_uuid = models.CharField(max_length=100, blank=True, help_text="Form element uuid of the question group this belongs to")
    group_name = models.CharField(max_length=300, blank=True)
    question_name = models.CharField(max_length=500)
    concept_name = models.CharField(max_length=500)
    concept_uuid = models.CharField(max_length=100, blank=True)
    data_type = models.CharField(max_length=60)
    is_multi_select = models.BooleanField(default=False)
    answers = JSONField(null=True, blank=True)
    is_mandatory = models.BooleanField(default=False)
    display_order = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("form", "uuid")
        ordering = ("form", "display_order", "id")
        verbose_name = "AVNI form question"

    def __str__(self):
        return "{} -> {}".format(self.question_name, self.concept_name)
