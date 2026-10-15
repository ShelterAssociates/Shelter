"""Fill a map filter preset with the active forms of one or more subject types."""

from django.core.management.base import BaseCommand, CommandError

from avni.metadata import active_mappings
from avni.models import AvniFilterPreset, AvniFilterPresetItem, AvniFilterPresetScope
from master.models import City, Slum


class Command(BaseCommand):
    """Safe to re-run: an existing item keeps the flags it was given in the admin."""

    help = "Add every active form of the given subject types to a map filter preset."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Preset name; created at version 1 when new.")
        parser.add_argument("--preset-version", type=int, default=None, dest="preset_version",
                            help="Defaults to the newest version of that name. (--version is Django's own option.)")
        parser.add_argument("--subject-type", action="append", required=True, dest="subject_types")
        parser.add_argument("--encounters-only", action="store_true", help="Skip registration and enrolment forms.")
        parser.add_argument("--required", action="append", default=[], dest="required",
                            help="Encounter type to mark required for completeness. Repeatable.")
        parser.add_argument("--city", type=int, default=None, help="Scope the preset to every slum of this city id.")
        parser.add_argument("--slum", type=int, default=None, help="Scope the preset to this slum id.")

    def handle(self, *args, **options):
        # Resolved before the preset is created, so a mistyped subject type leaves nothing behind.
        mappings = active_mappings().filter(subject_type__in=options["subject_types"])
        if options["encounters_only"]:
            mappings = mappings.filter(form__form_type__in=("Encounter", "ProgramEncounter"))
        if not mappings.exists():
            raise CommandError("No active forms for {}".format(", ".join(options["subject_types"])))
        preset = self.preset_for(options["name"], options["preset_version"])
        required = {name.strip().lower() for name in options["required"]}
        created = seen = 0
        for order, mapping in enumerate(mappings.order_by("subject_type", "program", "encounter_type")):
            _, was_created = AvniFilterPresetItem.objects.get_or_create(
                preset=preset, mapping=mapping,
                defaults={"order": order, "is_required": mapping.encounter_type.lower() in required},
            )
            created += was_created
            seen += 1
        self.scope(preset, options["city"], options["slum"])
        self.stdout.write("{} v{}: {} form(s) added, {} already present".format(
            preset.name, preset.version, created, seen - created))

    def preset_for(self, name, version):
        if version is not None:
            preset = AvniFilterPreset.objects.filter(name=name, version=version).first()
            if preset is None:
                raise CommandError("No preset {} v{}".format(name, version))
            return preset
        newest = AvniFilterPreset.objects.filter(name=name).order_by("-version").first()
        return newest or AvniFilterPreset.objects.create(name=name)

    def scope(self, preset, city_id, slum_id):
        if slum_id is not None:
            slum = Slum.objects.filter(id=slum_id).first()
            if slum is None:
                raise CommandError("No slum {}".format(slum_id))
            AvniFilterPresetScope.objects.get_or_create(preset=preset, slum=slum)
            self.stdout.write("scoped to slum {}".format(slum.name))
        if city_id is not None:
            city = City.objects.filter(id=city_id).first()
            if city is None:
                raise CommandError("No city {}".format(city_id))
            AvniFilterPresetScope.objects.get_or_create(preset=preset, city=city, slum=None)
            self.stdout.write("scoped to every slum of city {}".format(city_id))
