"""Cached AVNI form definitions: which forms exist, what they are for, what they ask."""

from colorfield.fields import ColorField
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
    shows_map = models.BooleanField(
        default=False, verbose_name="opens the slum map",
        help_text="Subject registration forms only: the app picks the structure on the map before this form.")

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


class AvniMapFilter(models.Model):
    """A coded concept the mobile map offers as a household filter, picked from the cached AVNI form questions."""

    question = models.ForeignKey(
        AvniFormQuestion, on_delete=models.PROTECT, related_name="map_filters",
        limit_choices_to={"data_type": "Coded", "is_active": True}, verbose_name="concept",
    )
    concept_uuid = models.CharField(max_length=100, unique=True, editable=False)
    concept_name = models.CharField(max_length=500, editable=False)
    order = models.FloatField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order", "concept_name")
        verbose_name = "Map filter"

    def save(self, *args, **kwargs):
        self.concept_uuid = self.question.concept_uuid
        self.concept_name = self.question.concept_name
        super(AvniMapFilter, self).save(*args, **kwargs)

    def __str__(self):
        return self.concept_name


# The prefix of a filter id, per form type; the app keys its per-household records by it.
FILTER_KIND = {
    "IndividualProfile": "reg",
    "ProgramEnrolment": "enrol",
    "ProgramEncounter": "penc",
    "Encounter": "enc",
}
DATE_QUESTION = {"data_type__in": ("Date", "DateTime"), "is_active": True}
WINDOW_CHOICES = (("overall", "Overall"), ("current_fy", "Current financial year"))
ROLLUP_CHOICES = (("household", "The household itself"), ("member", "The household's members"))
STAGE_KINDS = (("progress", "Progress"), ("cancelled", "Cancelled"))


class AvniFilterPreset(models.Model):
    """A named, versioned set of form filters the mobile map offers, assigned to cities and slums."""

    name = models.CharField(max_length=200)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_on = models.DateTimeField(default=timezone.now)
    occupancy_question = models.ForeignKey(
        AvniFormQuestion, on_delete=models.PROTECT, null=True, blank=True, related_name="occupancy_presets",
        limit_choices_to={"data_type": "Coded", "is_active": True}, verbose_name="occupancy question",
        help_text="Coded question saying what the structure is. Forms are only expected for the answers below.",
    )
    occupied_answers = JSONField(
        null=True, blank=True, verbose_name="occupied answers",
        help_text='The answers that count as occupied, e.g. ["Occupied house"]. Blank expects every structure to be filled.',
    )

    class Meta:
        unique_together = ("name", "version")
        ordering = ("name", "-version")
        verbose_name = "Map filter preset"

    def __str__(self):
        return "{} v{}".format(self.name, self.version)


class AvniFilterPresetItem(models.Model):
    """One form of a preset: offered as a filled/absent filter, counted for completeness, or both."""

    preset = models.ForeignKey(AvniFilterPreset, on_delete=models.CASCADE, related_name="items")
    mapping = models.ForeignKey(
        AvniFormMapping, on_delete=models.PROTECT, related_name="preset_items",
        limit_choices_to={"is_active": True}, verbose_name="form",
    )
    label = models.CharField(max_length=200, blank=True, help_text="Blank uses the encounter, program or subject type name.")
    show_as_filter = models.BooleanField(default=True, verbose_name="offer as a filter")
    is_required = models.BooleanField(default=False, verbose_name="required for completeness")
    anchor_question = models.ForeignKey(
        AvniFormQuestion, on_delete=models.PROTECT, null=True, blank=True, related_name="anchored_items",
        limit_choices_to=DATE_QUESTION, verbose_name="date question",
        help_text="The date a date filter compares against. Blank uses the encounter's own date.",
    )
    rollup = models.CharField(max_length=20, choices=ROLLUP_CHOICES, default="household")
    pairs_with = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="paired_from",
        help_text="The follow-up form, e.g. the post-impact form of a pre-impact form.",
    )
    default_window = models.CharField(max_length=20, choices=WINDOW_CHOICES, default="overall")
    filled_color = ColorField(default="#1F8A4C")
    absent_color = ColorField(default="#C0392B")
    order = models.FloatField(default=0)

    class Meta:
        unique_together = ("preset", "mapping")
        ordering = ("preset", "order", "id")
        verbose_name = "Preset form"

    @property
    def filter_id(self):
        mapping = self.mapping
        parts = [FILTER_KIND.get(mapping.form.form_type, "form"), mapping.subject_type, mapping.program, mapping.encounter_type]
        return ":".join(part for part in parts if part)

    @property
    def display_label(self):
        mapping = self.mapping
        return self.label or mapping.encounter_type or mapping.program or mapping.subject_type

    def __str__(self):
        return self.display_label


class AvniStageFilter(models.Model):
    """A stage of a form's progress, read from one of its date questions (the toilet construction phases)."""

    item = models.ForeignKey(AvniFilterPresetItem, on_delete=models.CASCADE, related_name="stages")
    label = models.CharField(max_length=200)
    question = models.ForeignKey(
        AvniFormQuestion, on_delete=models.PROTECT, related_name="stage_filters",
        limit_choices_to=DATE_QUESTION, verbose_name="date question",
    )
    kind = models.CharField(max_length=20, choices=STAGE_KINDS, default="progress")
    color = ColorField(default="#F0A30A")
    order = models.FloatField(default=0)

    class Meta:
        ordering = ("item", "order", "id")
        verbose_name = "Preset stage"

    def __str__(self):
        return self.label


class AvniFilterPresetScope(models.Model):
    """Where a preset applies: one slum, every slum of a city, or everywhere."""

    preset = models.ForeignKey(AvniFilterPreset, on_delete=models.CASCADE, related_name="scopes")
    city = models.ForeignKey(
        "master.City", on_delete=models.CASCADE, null=True, blank=True,
        help_text="Blank, with no slum, means every city.",
    )
    slum = models.ForeignKey(
        "master.Slum", on_delete=models.CASCADE, null=True, blank=True,
        help_text="Blank means every slum of the city.",
    )

    class Meta:
        unique_together = ("preset", "city", "slum")
        ordering = ("preset", "city", "slum")
        verbose_name = "Preset scope"

    def save(self, *args, **kwargs):
        # A slum row carries its city so city-wide and slum-specific rows can be fetched in one query.
        if self.slum_id and not self.city_id:
            self.city_id = city_id_of(self.slum)
        super(AvniFilterPresetScope, self).save(*args, **kwargs)

    def __str__(self):
        if self.slum_id:
            return "{} -> {}".format(self.preset, self.slum.name)
        return "{} -> {}".format(self.preset, self.city.name.city_name if self.city_id else "every city")


def city_id_of(slum):
    """The city a slum belongs to, through its electoral and administrative ward."""
    ward = slum.electoral_ward
    if ward is None or ward.administrative_ward is None:
        return None
    return ward.administrative_ward.city_id
