"""Set up the map filter preset the mobile app colours houses by.

Safe to re-run: every row is looked up before it is created, and anything an admin has since
changed by hand is left alone. Run it after the AVNI form cache has been refreshed at least once,
because every item points at a cached form.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from avni.metadata import active_mappings
from avni.models import (AvniFilterPreset, AvniFilterPresetItem, AvniFilterPresetScope,
                         AvniFormQuestion, AvniStageFilter)
from master.models import City, Slum

DEFAULT_NAME = "Shelter default"

# The encounters that must be filled for a household to count as complete, per subject type.
REQUIRED = {
    "Household": ["Water", "Waste", "Electricity", "Sanitation"],
    "Detailed Socio Economic Survey": ["Water INP", "Waste INP", "Sanitation INP",
                                       "Electricity INP", "Housing INP"],
    "Family Member": [],
}
MEMBER_SUBJECT_TYPES = ["Family Member"]

# The date a date window compares against, instead of the visit's own date.
ANCHORS = {
    ("Household", "Sanitation program", "Daily Reporting"): "Date of agreement",
    ("Family Member", "Menstrual hygiene", ""): "Date of menstrual cup giving",
}

# Toilet construction, read from the Daily Reporting form's date questions.
STAGES = [
    ("Agreement done", "Date of agreement", "progress", "#F1C40F"),
    ("Septic tank given", "Date on which septic tank is given", "progress", "#E67E22"),
    ("Phase 1 - cement", "Date on which cement is given", "progress", "#E74C3C"),
    ("Phase 2 - bricks", "Date on which bricks are given", "progress", "#9B59B6"),
    ("Phase 3 - tiles", "Date on which Tiles are given", "progress", "#3498DB"),
    ("Construction started", "Date on which toilet construction has started", "progress", "#1ABC9C"),
    ("Toilet complete", "Date on which toilet construction is complete", "progress", "#1F8A4C"),
    ("Agreement cancelled", "Date on which agreement is cancelled", "cancelled", "#7F8C8D"),
]
STAGE_FORM = ("Household", "Sanitation program", "Daily Reporting")

# A pre-impact form and the post form that should follow it.
PAIRS = [
    ("Household", "Sanitation program", "OHOT Pre Impact Assessment", "OHOT Post Impact Assessment"),
    ("Family Member", "Menstrual hygiene", "MHM Pre Impact Assessment", "MHM Post Impact Assessment"),
]

# Forms are only expected where the structure is occupied.
OCCUPANCY_QUESTION = "Type of structure occupancy_1"
OCCUPIED_ANSWERS = ["Occupied house"]


class Command(BaseCommand):
    help = "Create or top up the map filter preset the Avni app reads. Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--name", default=DEFAULT_NAME)
        parser.add_argument("--subject-type", action="append", dest="subject_types",
                            help="Defaults to Household, Detailed Socio Economic Survey and Family Member.")
        parser.add_argument("--global-scope", action="store_true",
                            help="Apply the preset to every city. Without this, scope it in the admin.")
        parser.add_argument("--city", type=int, action="append", default=[], dest="cities",
                            help="Apply to every slum of this city id. Repeatable.")
        parser.add_argument("--slum", type=int, action="append", default=[], dest="slums",
                            help="Apply to this slum id only. Repeatable.")
        parser.add_argument("--dry-run", action="store_true", help="Say what would change and write nothing.")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        subject_types = options["subject_types"] or list(REQUIRED)
        mappings = list(active_mappings().filter(subject_type__in=subject_types)
                        .order_by("subject_type", "program", "encounter_type"))
        if not mappings:
            raise CommandError(
                "No active forms for {}. Refresh the AVNI form cache first "
                "(manage.py run_job avni_form_cache_refresh).".format(", ".join(subject_types)))

        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - nothing will be written"))
        try:
            with transaction.atomic():
                counts = self.seed(options["name"], mappings, options)
                if self.dry_run:
                    raise _Rollback()
        except _Rollback:
            pass
        self.stdout.write("")
        for line in counts:
            self.stdout.write(line)

    def seed(self, name, mappings, options):
        preset, created = AvniFilterPreset.objects.get_or_create(
            name=name, version=1, defaults={"is_active": True, "notes": "Seeded by seed_map_filters."})
        self.say("preset {} v{} {}".format(preset.name, preset.version, "created" if created else "already present"))

        items, added = {}, 0
        for order, mapping in enumerate(mappings):
            required = mapping.encounter_type in REQUIRED.get(mapping.subject_type, [])
            # Programme work is reported per financial year; "which survey is missing" is asked of all time.
            window = "current_fy" if mapping.form.form_type in ("ProgramEnrolment", "ProgramEncounter") else "overall"
            key = (mapping.subject_type, mapping.program, mapping.encounter_type)
            item, made = AvniFilterPresetItem.objects.get_or_create(
                preset=preset, mapping=mapping,
                defaults={"order": order, "is_required": required, "default_window": window,
                          "anchor_question": self.question(mapping, ANCHORS.get(key)),
                          "rollup": "member" if mapping.subject_type in MEMBER_SUBJECT_TYPES else "household"})
            items[key] = item
            added += made
            if made:
                self.say("  + {:<58} required={}".format(item.filter_id, required))

        stages = self.seed_stages(items.get(STAGE_FORM))
        pairs = self.seed_pairs(items)
        self.seed_occupancy(preset)
        self.seed_scopes(preset, options)
        return [
            "{} form(s) added, {} already present".format(added, len(mappings) - added),
            "{} stage(s) added, {} pair(s) linked".format(stages, pairs),
            "preset now holds {} forms, {} required, {} stages".format(
                preset.items.count(), preset.items.filter(is_required=True).count(),
                AvniStageFilter.objects.filter(item__preset=preset).count()),
        ]

    def question(self, mapping, concept_name):
        if not concept_name:
            return None
        found = AvniFormQuestion.objects.filter(
            form=mapping.form, concept_name=concept_name, is_active=True).first()
        if found is None:
            self.say("  ! no question '{}' on {}".format(concept_name, mapping.form.name), warn=True)
        return found

    def seed_stages(self, item):
        if item is None:
            self.say("  ! Daily Reporting is not in this preset, so no construction stages", warn=True)
            return 0
        added = 0
        for order, (label, concept_name, kind, color) in enumerate(STAGES):
            question = self.question(item.mapping, concept_name)
            if question is None:
                continue
            _, made = AvniStageFilter.objects.get_or_create(
                item=item, question=question,
                defaults={"label": label, "kind": kind, "color": color, "order": order})
            added += made
            if made:
                self.say("  + stage {}".format(label))
        return added

    def seed_pairs(self, items):
        linked = 0
        for subject_type, program, pre_name, post_name in PAIRS:
            pre = items.get((subject_type, program, pre_name))
            post = items.get((subject_type, program, post_name))
            if pre is None or post is None or pre.pairs_with_id == post.id:
                continue
            pre.pairs_with = post
            pre.save(update_fields=["pairs_with"])
            linked += 1
            self.say("  + paired {} -> {}".format(pre_name, post_name))
        return linked

    def seed_occupancy(self, preset):
        if preset.occupancy_question_id and preset.occupied_answers:
            return
        question = AvniFormQuestion.objects.filter(
            concept_name=OCCUPANCY_QUESTION, data_type="Coded", is_active=True).order_by("id").first()
        if question is None:
            self.say("  ! no coded question '{}'; every structure will be expected to be filled".format(
                OCCUPANCY_QUESTION), warn=True)
            return
        preset.occupancy_question = question
        preset.occupied_answers = OCCUPIED_ANSWERS
        preset.save(update_fields=["occupancy_question", "occupied_answers"])
        self.say("  + occupancy rule: {} in {}".format(OCCUPANCY_QUESTION, OCCUPIED_ANSWERS))

    def seed_scopes(self, preset, options):
        if options["global_scope"]:
            _, made = AvniFilterPresetScope.objects.get_or_create(preset=preset, city=None, slum=None)
            self.say("  {} scope: every city".format("+" if made else "="))
        for city_id in options["cities"]:
            if not City.objects.filter(id=city_id).exists():
                raise CommandError("No city {}".format(city_id))
            _, made = AvniFilterPresetScope.objects.get_or_create(preset=preset, city_id=city_id, slum=None)
            self.say("  {} scope: every slum of city {}".format("+" if made else "=", city_id))
        for slum_id in options["slums"]:
            slum = Slum.objects.filter(id=slum_id).first()
            if slum is None:
                raise CommandError("No slum {}".format(slum_id))
            _, made = AvniFilterPresetScope.objects.get_or_create(preset=preset, slum=slum)
            self.say("  {} scope: slum {}".format("+" if made else "=", slum.name))
        if not preset.scopes.exists():
            self.say("  ! no scope yet, so the app will not offer these filters anywhere. "
                     "Add one with --global-scope/--city/--slum or in the admin.", warn=True)

    def say(self, message, warn=False):
        self.stdout.write(self.style.WARNING(message) if warn else message)


class _Rollback(Exception):
    pass
