"""Move one slum's collected data onto another, for a re-survey registered
under a second AVNI location.

The target's current household data is cleared first (it is archived by the
version machinery before anything goes), then the source's rows are re-pointed
at the target. Components move per layer: a layer the source has replaces the
target's copy of that layer, and a layer only the target has is left alone.

RIM is never moved. The target's factsheet is the one the public sees, and a
second Rapid_Slum_Appraisal row on one slum makes it ambiguous.

Dry run unless --apply is given.
"""

import json
from collections import Counter, OrderedDict

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils import timezone

from survey import merging, versioning
from survey.models import Record

# Left to the version machinery, handled explicitly below, or deliberately kept.
SKIP = {
    "survey.slumdataversion", "survey.slumversionbackup", "survey.slumalias",
    "survey.slumsyncsetting", "survey.record",
    "graphs.slumdata", "master.rapid_slum_appraisal",
    "component.component", "component.componentmetric",
}

COMPONENT_MODES = ("per-layer", "missing-only", "all")


class Command(BaseCommand):
    help = "Move a slum's data onto another slum (re-survey under a second AVNI location)."

    def add_arguments(self, parser):
        parser.add_argument("--from", dest="source", type=int, required=True, help="Slum id to take data from.")
        parser.add_argument("--into", dest="target", type=int, required=True, help="Slum id to move it onto.")
        parser.add_argument("--apply", action="store_true", help="Actually do it. Without this it only reports.")
        parser.add_argument(
            "--components", default="per-layer", choices=COMPONENT_MODES,
            help="per-layer: a layer the source has replaces the target's copy (default). "
                 "missing-only: only layers the target lacks. all: replace every component.",
        )
        parser.add_argument("--dump", default="", help="Write a JSON copy of every row that moves to this path.")
        parser.add_argument(
            "--skip-household-clear", action="store_true",
            help="Leave the target's household rows in place (they would then collide).",
        )

    # -- reporting ------------------------------------------------------------

    def line(self, text=""):
        self.stdout.write(text)

    def table(self, title, rows):
        self.line(title)
        for name, value in rows:
            self.line("   {:<38} {}".format(name, value))

    def component_plan(self, source, target, mode):
        """({layer: count to bring}, {layer: count to drop from the target})."""
        bring = Counter(
            versioning.rows_for(versioning.COMPONENT_TABLES[0], source)
            .values_list("metadata__name", flat=True)
        )
        held = Counter(
            versioning.rows_for(versioning.COMPONENT_TABLES[0], target)
            .values_list("metadata__name", flat=True)
        )
        if mode == "missing-only":
            bring = Counter({name: n for name, n in bring.items() if name not in held})
            drop = Counter()
        elif mode == "all":
            drop = held
        else:
            drop = Counter({name: n for name, n in held.items() if name in bring})
        return bring, drop

    def movable_relations(self, source, target):
        """([(relation, count)], {label: why it was left}) for the plain relations."""
        moving, left = [], OrderedDict()
        for relation in merging.related_relations():
            label = merging.label_of(relation)
            if label in SKIP:
                continue
            try:
                count = merging.rows_of(relation, source).count()
            except DatabaseError as exc:
                # The model declares the link but the column is missing, so no
                # row can point at either slum and nothing can be orphaned.
                left[label] = "no column in the database ({})".format(
                    str(exc).strip().splitlines()[0]
                )
                continue
            if count:
                moving.append((relation, count))
        return moving, left

    # -- the work -------------------------------------------------------------

    def handle(self, *args, **options):
        source, target = options["source"], options["target"]
        mode = options["components"]
        if source == target:
            raise CommandError("--from and --into must be different slums.")

        from master.models import Slum

        names = dict(Slum.objects.filter(id__in=[source, target]).values_list("id", "name"))
        for slum_id in (source, target):
            if slum_id not in names:
                raise CommandError("Slum {} does not exist.".format(slum_id))
        self.line("source  {} {}".format(source, names[source]))
        self.line("target  {} {}".format(target, names[target]))

        pending = versioning.pending_version(target)
        outgoing = (pending.version - 1) if pending else versioning.current_number(target)
        missing = [t.label for t in versioning.missing_backup_tables(target, outgoing)]
        self.line("")
        self.line("target version {} waiting: {}".format(
            pending.version if pending else "-", "yes" if pending else "no",
        ))
        self.line("backup of version {} missing: {}".format(outgoing, missing or "nothing"))
        if options["apply"] and pending is None:
            raise CommandError(
                "Slum {} has no version waiting, so there is nothing to clear safely. "
                "Start a new version on the Slum data versions page first.".format(target)
            )
        if missing:
            self.line("   (anything missing is archived before a single row is removed)")

        clearing = []
        if not options["skip_household_clear"]:
            clearing = [
                (table.label, versioning.rows_for(table, target).count())
                for table in versioning.HOUSEHOLD_TABLES
            ]
            self.line("")
            self.table("would clear from the target (already archived):",
                       [(n, c) for n, c in clearing if c])

        moving, left = self.movable_relations(source, target)
        self.line("")
        self.table("would move from the source:",
                   [(merging.label_of(r), c) for r, c in moving] or [("nothing", 0)])
        records = Record.objects.filter(slum_id=source).count()
        self.line("   {:<38} {}".format("survey.record", records))
        if left:
            self.line("")
            self.table("left alone:", list(left.items()))

        bring, drop = self.component_plan(source, target, mode)
        self.line("")
        self.line("components, mode {}:".format(mode))
        self.line("   {:<30} {:>8} {:>8}".format("layer", "drop", "bring"))
        for name in sorted(set(bring) | set(drop)):
            self.line("   {:<30} {:>8} {:>8}".format(name, drop.get(name, 0), bring.get(name, 0)))
        kept = versioning.rows_for(versioning.COMPONENT_TABLES[0], target).count() - sum(drop.values())
        self.line("   target would end with {} ({} kept + {} brought)".format(
            kept + sum(bring.values()), kept, sum(bring.values()),
        ))
        self.line("")
        self.line("RIM is not moved: the target keeps its own factsheet data.")

        if not options["apply"]:
            self.line("")
            self.line("DRY RUN. Re-run with --apply to carry this out.")
            return

        if options["dump"]:
            self.write_dump(options["dump"], source, target, moving, bring, drop, mode)
            self.line("dump written to {}".format(options["dump"]))

        done = self.apply(source, target, moving, mode, options["skip_household_clear"])
        self.line("")
        self.table("done:", sorted(done.items()))

    def write_dump(self, path, source, target, moving, bring, drop, mode):
        payload = {
            "made_on": timezone.now().isoformat(),
            "source_slum": source,
            "target_slum": target,
            "components_mode": mode,
            "components_bring": dict(bring),
            "components_drop": dict(drop),
            "rows": {},
        }
        for relation, _ in moving:
            payload["rows"][merging.label_of(relation)] = list(
                merging.rows_of(relation, source).values()
            )
        components = versioning.COMPONENT_TABLES[0]
        payload["rows"]["component.component.source"] = list(
            versioning.rows_for(components, source).values()
        )
        payload["rows"]["component.component.target"] = list(
            versioning.rows_for(components, target).values()
        )
        with open(path, "w") as handle:
            json.dump(payload, handle, indent=2, default=str)

    @transaction.atomic
    def apply(self, source, target, moving, mode, skip_clear):
        from master.models import Slum

        done = {}
        pending = versioning.pending_version(target)
        if pending is not None:
            # Nothing may be deleted while it exists nowhere else, and the live
            # rows right now still are the outgoing version's data.
            for label, count in versioning.ensure_backup(target, pending.version - 1).items():
                done["archived " + label] = count
        if not skip_clear:
            cleared = versioning.go_live(target)
            for label, count in cleared.items():
                if count:
                    done["cleared " + label] = count

        for relation, _ in moving:
            done["moved " + merging.label_of(relation)] = merging.move_rows(relation, source, target)

        target_name = Slum.objects.values_list("name", flat=True).get(id=target)
        version = versioning.current_number(target)
        done["moved survey.record"] = Record.objects.filter(slum_id=source).update(
            slum_id=target, slum_name=target_name, version=version,
        )

        done.update(self.move_components(source, target, mode))
        return done

    def move_components(self, source, target, mode):
        """Per layer unless told otherwise; the target's other layers are untouched."""
        components, metrics = versioning.COMPONENT_TABLES
        bring, drop = self.component_plan(source, target, mode)
        done = {}
        if drop:
            done["dropped component.Component"] = versioning.rows_for(components, target).filter(
                metadata__name__in=list(drop)
            ).delete()[0]
            done["dropped component.ComponentMetric"] = versioning.rows_for(metrics, target).filter(
                metadata__name__in=list(drop)
            ).delete()[0]
        if bring:
            done["moved component.Component"] = versioning.rows_for(components, source).filter(
                metadata__name__in=list(bring)
            ).update(object_id=target)
            done["moved component.ComponentMetric"] = versioning.rows_for(metrics, source).filter(
                metadata__name__in=list(bring)
            ).update(slum_id=target)
        return done
