"""Build a throwaway slum with three RIM surveys, to see the version comparison.

Local only, and it refuses to run anywhere else. It copies a real slum's RIM so
the factsheet looks realistic, then changes a scattering of answers between
surveys so the comparison has something to show.

    python manage.py make_local_test_slum
    python manage.py make_local_test_slum --remove
"""

import copy
import random
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.geos import Polygon
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from graphs.models import SlumData
from master.models import (
    AdministrativeWard, City, CityReference, ElectoralWard, Rapid_Slum_Appraisal, Slum,
)
from reports.services.rim_factsheet import RIM_FIELD_DISPLAY_NAMES
from survey import versioning
from survey.models import SlumDataVersion, SlumVersionBackup

# Obvious on sight in a slum list, and what --remove looks for.
TEST_NAME = "ZZ LOCAL TEST SLUM (delete me)"
TEST_CODE = "ZZTEST1"
TEST_WARD = "ZZ TEST ADMIN WARD (delete me)"
TEST_ELECTORAL = "ZZ TEST ELECTORAL WARD (delete me)"
LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}
CONFIRM_WORD = "ZZTEST"

# A ~100m square in open ground east of Pune, so it sits in the right city
# without overlapping a real settlement.
SHAPE = Polygon((
    (73.9600, 18.5200), (73.9600, 18.5210),
    (73.9610, 18.5210), (73.9610, 18.5200), (73.9600, 18.5200),
))

SAMPLE_TEXT = [
    "Yes", "No", "Partially", "Good", "Poor", "Average",
    "Municipal supply", "Borewell", "Tanker", "Open drain", "Closed drain",
]


class Command(BaseCommand):
    help = "Create (or remove) a local-only test slum with three RIM survey versions."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true", help="Delete the test slum and everything under it.")
        parser.add_argument(
            "--production", action="store_true",
            help="Allow this to run against a non-local database. Needs --confirm as well.",
        )
        parser.add_argument("--confirm", default="", help="Type {} to confirm --production.".format(CONFIRM_WORD))
        parser.add_argument(
            "--city", default="",
            help="Put the test slum in this real city (e.g. Pune) instead of a test city of its own.",
        )
        parser.add_argument("--source", type=int, default=0, help="Slum id to copy RIM answers from.")
        parser.add_argument("--seed", type=int, default=20261009, help="Random seed, so runs are repeatable.")

    # -- safety ---------------------------------------------------------------

    def check_target(self, options):
        """Local by default; anywhere else needs saying so, twice."""
        host = (settings.DATABASES.get("default", {}).get("HOST") or "").strip()
        name = settings.DATABASES.get("default", {}).get("NAME", "?")
        local = host.lower() in LOCAL_HOSTS and settings.DEBUG

        if not local:
            if not options["production"]:
                raise CommandError(
                    "Refusing to run: database '{}' on host '{}' is not a local development copy. "
                    "Re-run with --production --confirm {} if you really mean to write a test "
                    "slum to this database.".format(name, host or "(socket)", CONFIRM_WORD)
                )
            if options["confirm"] != CONFIRM_WORD:
                raise CommandError("Type --confirm {} to write a test slum to '{}'.".format(CONFIRM_WORD, name))
            self.stdout.write(self.style.WARNING(
                "WRITING A TEST SLUM TO A NON-LOCAL DATABASE: {} on {}".format(name, host)
            ))
        self.stdout.write("database: {} on {}".format(name, host or "localhost socket"))

    # -- data -----------------------------------------------------------------

    def source_rim(self, source_id):
        """A real slum's rim_data to copy, so the factsheet has believable answers."""
        rows = SlumData.objects.exclude(rim_data=None).exclude(rim_data={})
        row = rows.filter(slum_id=source_id).first() if source_id else None
        if row is None:
            if source_id:
                raise CommandError("Slum {} has no RIM data to copy.".format(source_id))
            # The richest one going, so there are plenty of fields to differ.
            row = max(rows[:200], key=lambda r: len(str(r.rim_data)), default=None)
        if row is None:
            raise CommandError("No slum in this database has RIM data to copy from.")
        self.stdout.write("copying RIM answers from slum {}".format(row.slum_id))
        return copy.deepcopy(row.rim_data)

    def vary(self, value, rng):
        """One changed answer: numbers drift, text swaps for another option."""
        text = str(value)
        if re.match(r"^-?\d+$", text):
            return str(max(0, int(text) + rng.choice([-30, -12, -5, 7, 18, 45])))
        if re.match(r"^-?\d*\.\d+$", text):
            return "{:.2f}".format(max(0.0, float(text) + rng.uniform(-5, 9)))
        return rng.choice([option for option in SAMPLE_TEXT if option != text])

    def image_columns(self):
        """Every appraisal column that holds a picture, by section slot."""
        columns = []
        for fields in RIM_FIELD_DISPLAY_NAMES.get("sections", {}).values():
            keys = list(fields)
            if not keys:
                continue
            columns.append(keys[0])
            columns.extend(
                key for key, shown in fields.items()
                if "_bottom1" in shown or "_bottom2" in shown
            )
        return [column for column in columns if hasattr(Rapid_Slum_Appraisal, column)]

    def working_pictures(self, limit=40):
        """Stored picture paths that really do serve an image, newest first.

        Most of the older rows point at ShelterPhotos files that are gone from
        the media server, so borrowing blindly fills the demo with 404s. The
        AVNI S3 ones are presigned and fetched here to confirm each one.
        """
        from reports.services.rim_factsheet import is_image_reachable, resolve_rim_images

        columns = self.image_columns()
        candidates = []
        rows = (
            Rapid_Slum_Appraisal.objects
            .order_by("-id")
            .values("slum_name_id", *columns)[:limit]
        )
        for row in rows:
            held = {c: row[c] for c in columns if row.get(c)}
            if not held:
                continue
            resolved = resolve_rim_images(dict(held))
            for column, stored in held.items():
                shown = resolved.get(column)
                if shown and is_image_reachable(str(shown)):
                    candidates.append((column, stored))

        self.stdout.write("  checked {} rows, {} pictures load".format(len(rows), len(candidates)))
        return candidates, columns

    def donor_pictures(self):
        """Two sets of verified pictures per column, so a swap is a real change."""
        candidates, columns = self.working_pictures()
        by_column = {}
        for column, stored in candidates:
            by_column.setdefault(column, [])
            if stored not in by_column[column]:
                by_column[column].append(stored)

        first = {c: v[0] for c, v in by_column.items() if v}
        second = {c: (v[1] if len(v) > 1 else v[0]) for c, v in by_column.items() if v}
        differing = [c for c in by_column if len(by_column[c]) > 1]
        return [first, second], sorted(by_column), differing or sorted(by_column)

    def set_pictures(self, slum, row, columns, share, rng):
        """Point some of the slum's picture columns at a donor's."""
        if not row:
            return 0
        chosen = rng.sample(columns, int(len(columns) * share))
        update = {column: row.get(column) for column in chosen if row.get(column)}
        if update:
            Rapid_Slum_Appraisal.objects.filter(slum_name=slum).update(**update)
        return len(update)

    def displayed_keys(self):
        """Raw keys the factsheet actually prints, so a change is one you can see.

        Most keys in a slum's rim_data never reach the factsheet, so mutating
        at random barely moves the comparison. The picture slots are left out:
        their signed URLs are not compared.
        """
        keys = set()
        for fields in RIM_FIELD_DISPLAY_NAMES.get("sections", {}).values():
            keys.update(fields)
        return {key for key in keys if "image" not in key and "_map" not in key}

    def numeric_key(self, key):
        hints = ("number", "total", "count", "percentage", "hours", "no_of", "qty")
        return any(hint in key.lower() for hint in hints)

    def fill_blanks(self, fresh, rng, share=0.6):
        """Answer some questions the earlier survey left blank.

        A re-survey often collects a whole topic the last one skipped, which is
        a real change (NA -> an answer) and the only way a section the source
        slum never filled in shows anything at all.
        """
        for section, fields in RIM_FIELD_DISPLAY_NAMES.get("sections", {}).items():
            body = fresh.get(section)
            if body is None:
                fresh[section] = body = {}
            elif not isinstance(body, dict):
                # Toilet is a list of blocks, filled by the loop above instead.
                continue
            missing = [
                key for key in fields
                if key not in body and "image" not in key and "_map" not in key
            ]
            for key in rng.sample(missing, int(len(missing) * share)):
                body[key] = str(rng.randint(2, 400)) if self.numeric_key(key) else rng.choice(SAMPLE_TEXT)

    def next_survey(self, rim_data, rng, share=0.7):
        """The same RIM with most of its visible answers changed.

        A re-survey years later moves a lot, so `share` of the answers the
        factsheet prints are changed, plus a few that it does not.
        """
        fresh = copy.deepcopy(rim_data)
        shown_keys = self.displayed_keys()
        shown, hidden = [], []

        def walk(node, path):
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(value, path + [key])
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, path + [index])
            elif node not in (None, "") and not str(node).startswith("http"):
                (shown if path and path[-1] in shown_keys else hidden).append(path)

        walk(fresh, [])
        if not shown and not hidden:
            raise CommandError("The copied RIM has no answers to change.")

        picked = rng.sample(shown, int(len(shown) * share)) if shown else []
        picked += rng.sample(hidden, min(5, len(hidden))) if hidden else []

        for path in picked:
            node = fresh
            for step in path[:-1]:
                node = node[step]
            node[path[-1]] = self.vary(node[path[-1]], rng)

        self.fill_blanks(fresh, rng)
        return fresh

    # -- the work -------------------------------------------------------------

    def remove(self):
        """Delete the exact rows this command makes, by hand.

        Not slum.delete(): Django's cascade walks every relation pointing at
        Slum, and at least one of those tables does not match its model in a
        local database with migrations outstanding, so the scan fails before
        anything is removed. The test slum only ever has the rows below.
        """
        from django.db import connection

        slums = list(Slum.objects.filter(name=TEST_NAME))
        if not slums:
            self.stdout.write("Nothing to remove.")
            return

        for slum in slums:
            ward = slum.electoral_ward
            admin_ward = ward.administrative_ward if ward else None
            city = admin_ward.city if admin_ward else None
            reference_id = city.name_id if city else None

            by_slum = [
                SlumDataVersion._meta.db_table,
                SlumVersionBackup._meta.db_table,
                SlumData._meta.db_table,
            ]
            with connection.cursor() as cursor:
                for table in by_slum:
                    cursor.execute("DELETE FROM {} WHERE slum_id = %s".format(table), [slum.id])
                cursor.execute(
                    "DELETE FROM {} WHERE slum_name_id = %s".format(
                        Rapid_Slum_Appraisal._meta.db_table), [slum.id],
                )
                cursor.execute("DELETE FROM {} WHERE id = %s".format(Slum._meta.db_table), [slum.id])
                if ward:
                    cursor.execute(
                        "DELETE FROM {} WHERE id = %s".format(ElectoralWard._meta.db_table), [ward.id])
                if admin_ward:
                    cursor.execute(
                        "DELETE FROM {} WHERE id = %s".format(AdministrativeWard._meta.db_table),
                        [admin_ward.id])
                # Only a city this command invented goes; a real one stays.
                own_city = bool(city and str(city.name.city_name).startswith("ZZ"))
                if own_city:
                    cursor.execute("DELETE FROM {} WHERE id = %s".format(City._meta.db_table), [city.id])
                    if reference_id:
                        cursor.execute(
                            "DELETE FROM {} WHERE id = %s".format(CityReference._meta.db_table),
                            [reference_id])
            self.stdout.write("Removed test slum {} and its test wards{}.".format(
                slum.id, " and test city" if own_city else " (the real city was left alone)",
            ))

    def find_city(self, wanted):
        """A real city by name, so the test slum sits where it can be found."""
        city = City.objects.filter(name__city_name__icontains=wanted).first()
        if city is None:
            raise CommandError("No city matching '{}'. Leave --city off to build a test city.".format(wanted))
        self.stdout.write("city: {} (id {})".format(city.name.city_name, city.id))
        return city

    def build_slum(self, wanted_city=""):
        """The slum, under its own clearly-named wards so nothing real is touched.

        `status=False` keeps it off the public map (master.views.slummapdisplay
        is the only query that filters on status) and `associated_with_SA=False`
        keeps it out of the dashboard aggregates.
        """
        if wanted_city:
            city = self.find_city(wanted_city)
        else:
            reference = CityReference.objects.create(
                city_name="ZZ Local Test City", city_code="ZZT", district_name="Test",
                district_code="TST", state_name="MH", state_code="MH",
            )
            owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
            city = City.objects.create(
                name=reference, city_code="ZZT", state_name="MH", state_code="MH",
                district_name="Test", district_code="TST", shape=SHAPE, created_by=owner,
            )

        admin_ward = AdministrativeWard.objects.create(city=city, name=TEST_WARD, shape=SHAPE)
        ward = ElectoralWard.objects.create(
            administrative_ward=admin_ward, name=TEST_ELECTORAL, shape=SHAPE,
        )
        return Slum.objects.create(
            electoral_ward=ward, name=TEST_NAME, shape=SHAPE, shelter_slum_code=TEST_CODE,
            status=False, associated_with_SA=False,
        )

    def write_rim(self, slum, city, rim_data):
        """Overwrite the live RIM in place, the way the AVNI sync does."""
        rows = SlumData.objects.filter(slum_id=slum.id)
        if rows.exists():
            rows.update(rim_data=rim_data, modified_on=timezone.now())
        else:
            SlumData.objects.create(
                slum=slum, city=city, submission_date=timezone.now(),
                rim_data=rim_data, modified_on=timezone.now(),
            )

    @transaction.atomic
    def handle(self, *args, **options):
        self.check_target(options)

        if options["remove"]:
            self.remove()
            return

        if Slum.objects.filter(name=TEST_NAME).exists():
            raise CommandError(
                "The test slum already exists. Run with --remove first if you want a fresh one."
            )

        rng = random.Random(options["seed"])
        survey_a = self.source_rim(options["source"])
        survey_b = self.next_survey(survey_a, rng)
        survey_c = self.next_survey(survey_b, rng)

        slum = self.build_slum(options["city"])
        city = slum.electoral_ward.administrative_ward.city

        donors, columns, differing = self.donor_pictures()
        first = donors[0] if donors else None
        second = donors[1] if len(donors) > 1 else first

        # Survey 1 -> archived as version 1 by the checkpoint
        self.write_rim(slum, city, survey_a)
        Rapid_Slum_Appraisal.objects.create(slum_name=slum, approximate_population="1250")
        swapped = self.set_pictures(slum, first, columns, 1.0, rng)
        versioning.start_new_version(slum.id, note="local test: second survey")

        # Survey 2 -> archived as version 2 by the next checkpoint. Some of the
        # pictures are re-taken, which is a change the comparison highlights.
        self.write_rim(slum, city, survey_b)
        Rapid_Slum_Appraisal.objects.filter(slum_name=slum).update(approximate_population="1480")
        swapped += self.set_pictures(slum, second, differing, 0.8, rng)
        versioning.start_new_version(slum.id, note="local test: third survey")

        # Survey 3 -> the live one
        self.write_rim(slum, city, survey_c)
        Rapid_Slum_Appraisal.objects.filter(slum_name=slum).update(approximate_population="1725")
        swapped += self.set_pictures(slum, first, differing, 0.7, rng)
        self.stdout.write("  picture columns set across the three surveys: {}".format(swapped))

        self.stdout.write("")
        self.stdout.write("Created slum {} - {} (status inactive)".format(slum.id, TEST_NAME))
        self.stdout.write("  archived RIM versions: {}".format(versioning.rim_backup_versions(slum.id)))
        self.stdout.write("  version picker offers: {}".format(
            [choice["label"] for choice in versioning.rim_choices_for(slum.id)]
        ))
        self.stdout.write("")
        self.stdout.write("Open /reports/, search for 'ZZ LOCAL', pick it and press Generate.")
        self.stdout.write("  Current  vs Version 2  -> the changes panel")
        self.stdout.write("  Version 2 vs Version 1 -> pick Version 2 in the Survey Version box")
        self.stdout.write("")
        self.stdout.write("Remove it with: python manage.py make_local_test_slum --remove")
