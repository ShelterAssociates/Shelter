"""Per-slum data versions in the live tables.

The live tables carry no version column. Starting a new version copies the
slum's rows into SlumVersionBackup and leaves the live tables alone, so the old
version stays in use. The first record of the new version switches the live
household tables over: the old rows are deleted there and survive only in the
backup. RIM is never switched automatically -- it is chosen explicitly.
"""

import json
import logging
from collections import namedtuple

from django.apps import apps
from django.core import serializers
from django.db import transaction
from django.utils import timezone

from survey.models import SlumAlias, SlumDataVersion, SlumVersionBackup

logger = logging.getLogger(__name__)

# Tables a slum's survey data lands in. `slum_field` is how each one points at
# the slum. Derived tables (dashboard aggregates, QOL, splits) are left out:
# they are rebuilt by the dashboard refresh, not collected per household.
Table = namedtuple("Table", "label app model slum_field generic")
Table.__new__.__defaults__ = (False,)

HOUSEHOLD_TABLES = [
    Table("Households", "graphs", "HouseholdData", "slum"),
    Table("Follow-ups", "graphs", "FollowupData", "slum"),
    Table("Family members", "graphs", "MemberData", "slum"),
    Table("Member programs", "graphs", "MemberProgramData", "slum"),
    Table("Member encounters", "graphs", "MemberEncounterData", "slum"),
    Table("Toilet construction", "mastersheet", "ToiletConstruction", "slum"),
    Table("Community mobilization", "mastersheet", "CommunityMobilization", "slum"),
    Table("Mobilization attendance", "mastersheet", "CommunityMobilizationActivityAttendance", "slum"),
]

RIM_TABLES = [
    Table("RIM slum data", "graphs", "SlumData", "slum"),
    Table("RIM additional info", "master", "Rapid_Slum_Appraisal", "slum_name"),
]

# Mapped components (the KML layers) and their manual metrics. Archived with the
# version but never cleared automatically: re-uploading a KML replaces one layer
# at a time, so the team removes and re-draws them by hand. The archive copy is
# then the only record of what the previous survey mapped.
COMPONENT_TABLES = [
    Table("Components (KML)", "component", "Component", "object_id", generic=True),
    Table("Component metrics", "component", "ComponentMetric", "slum"),
]

ALL_TABLES = HOUSEHOLD_TABLES + RIM_TABLES + COMPONENT_TABLES

RIM_KEEP, RIM_RESYNC, RIM_CLEAR = "keep", "resync", "clear"
RIM_CHOICES = (
    (RIM_KEEP, "Keep the current RIM data as it is"),
    (RIM_RESYNC, "Clear RIM and make a chosen location the RIM source"),
    (RIM_CLEAR, "Clear RIM and wait for a new sync"),
)

# Slums whose latest version is known for this process. A version started
# mid-run applies from the next run, as survey.versions already behaves.
_latest = {}


def reset_cache():
    _latest.clear()


def label_for(table):
    return "{}.{}".format(table.app, table.model)


def model_for(table):
    return apps.get_model(table.app, table.model)


def rows_for(table, slum_id):
    """The table's rows for one slum, whether it points at it by key or generically."""
    model = model_for(table)
    if table.generic:
        from django.contrib.contenttypes.models import ContentType

        from master.models import Slum

        return model.objects.filter(
            content_type=ContentType.objects.get_for_model(Slum), object_id=slum_id,
        )
    return model.objects.filter(**{table.slum_field + "_id": slum_id})


def counts(slum_id, tables=None):
    """{table label: live row count} for one slum."""
    return {table.label: rows_for(table, slum_id).count() for table in (tables or ALL_TABLES)}


def latest_version(slum_id):
    return SlumDataVersion.objects.filter(slum_id=slum_id).order_by("-version").first()


def current_number(slum_id):
    latest = latest_version(slum_id)
    return latest.version if latest else 1


def pending_version(slum_id):
    """The version whose data has not arrived yet, or None."""
    latest = latest_version(slum_id)
    return latest if latest and latest.switched_on is None else None


def backup_counts(slum_id, version):
    rows = (
        SlumVersionBackup.objects.filter(slum_id=slum_id, version=version)
        .values_list("source_model", flat=True)
    )
    tallied = {}
    for label in rows:
        tallied[label] = tallied.get(label, 0) + 1
    return tallied


def as_json(instances):
    """Serialised rows, JSON-safe, in the standard Django dump shape."""
    return json.loads(serializers.serialize("json", instances))


def archive(table, slum_id, version):
    """Copy a table's rows for one slum into the backup. Returns the row count."""
    instances = list(rows_for(table, slum_id))
    if not instances:
        return 0
    dumped = as_json(instances)
    SlumVersionBackup.objects.bulk_create([
        SlumVersionBackup(
            slum_id=slum_id,
            version=version,
            source_model=label_for(table),
            source_pk=str(row["pk"]),
            data=row,
        )
        for row in dumped
    ])
    return len(dumped)


@transaction.atomic
def start_new_version(slum_id, user=None, rim_choice=RIM_KEEP, rim_location=None, note=""):
    """Freeze the slum's current data as the old version and open the next one.

    The live tables are not touched for household data: the old version stays in
    use until its first new record arrives. RIM follows `rim_choice` only.
    """
    version = current_number(slum_id)
    archived = {table.label: archive(table, slum_id, version) for table in ALL_TABLES}
    new_version = SlumDataVersion.objects.create(
        slum_id=slum_id,
        version=version + 1,
        started_on=timezone.now(),
        switched_on=None,
        note=note,
        created_by=user if getattr(user, "pk", None) else None,
    )
    cleared = apply_rim_choice(slum_id, rim_choice, rim_location)
    reset_cache()
    logger.info("Slum %s: version %s started, archived %s", slum_id, new_version.version, archived)
    return {"version": new_version, "archived": archived, "rim_cleared": cleared}


def apply_rim_choice(slum_id, rim_choice, rim_location=None):
    """Act on the explicit RIM decision. Returns the rows cleared per table."""
    if rim_choice == RIM_KEEP:
        return {}
    if rim_choice == RIM_RESYNC:
        if not rim_location:
            raise ValueError("Choose which location RIM should sync from")
        set_rim_source(slum_id, rim_location)
    cleared = {}
    for table in RIM_TABLES:
        cleared[table.label] = rows_for(table, slum_id).count()
        rows_for(table, slum_id).delete()
    return cleared


def set_rim_source(slum_id, external_id, provider="avni"):
    """Make one mapped location the primary (RIM) one for a slum."""
    with transaction.atomic():
        aliases = SlumAlias.objects.select_for_update().filter(provider=provider, slum_id=slum_id)
        if not aliases.filter(external_id=external_id).exists():
            raise ValueError("Location {} is not mapped to this slum".format(external_id))
        aliases.update(is_primary=False)
        aliases.filter(external_id=external_id).update(is_primary=True)


def cached_latest(slum_id):
    if slum_id not in _latest:
        _latest[slum_id] = latest_version(slum_id)
    return _latest[slum_id]


def allows_write(slum_id, moment):
    """Whether a record may go into the live household tables, switching if due.

    A slum that was never versioned always writes, which is every slum today.
    Once a version is started, a record modified from `started_on` on is the new
    version's data: the first one switches the live tables over. A record older
    than that belongs to the frozen version and is kept out of the live tables,
    whatever order the provider sends records in. It still reaches the survey
    mirror, where it is stored against its own version.
    """
    if not slum_id:
        return True
    latest = cached_latest(slum_id)
    if latest is None or latest.version <= 1:
        return True
    is_new_data = moment is not None and moment >= latest.started_on
    if latest.switched_on is None:
        if is_new_data:
            go_live(slum_id, latest)
        return True
    return is_new_data


def missing_backup_tables(slum_id, version):
    """Registered tables holding live rows that this version has not archived.

    Covers a version added straight through the admin, which archived nothing,
    and a version started before the registry knew about a table.
    """
    archived = set(
        SlumVersionBackup.objects.filter(slum_id=slum_id, version=version)
        .values_list("source_model", flat=True)
    )
    return [
        table for table in ALL_TABLES
        if label_for(table) not in archived and rows_for(table, slum_id).exists()
    ]


def ensure_backup(slum_id, version):
    """Archive whatever this version is still missing. Returns what was added.

    Called before anything is deleted, so no row is ever removed while it exists
    nowhere else. The live rows at this moment still are the outgoing version's.
    """
    added = {}
    for table in missing_backup_tables(slum_id, version):
        added[table.label] = archive(table, slum_id, version)
    if added:
        logger.warning("Slum %s version %s was missing a backup of %s; archived it", slum_id, version, added)
    return added


@transaction.atomic
def go_live(slum_id, pending=None):
    """Delete the slum's old household rows, backing them up first if need be.

    RIM tables are never touched here.
    """
    pending = pending or pending_version(slum_id)
    if pending is None:
        return {}
    locked = SlumDataVersion.objects.select_for_update().filter(pk=pending.pk, switched_on__isnull=True)
    if not locked.exists():
        return {}
    ensure_backup(slum_id, pending.version - 1)
    removed = {}
    for table in HOUSEHOLD_TABLES:
        rows = rows_for(table, slum_id)
        removed[table.label] = rows.count()
        rows.delete()
    locked.update(switched_on=timezone.now())
    _latest.pop(slum_id, None)
    logger.info("Slum %s: version %s live, cleared %s", slum_id, pending.version, removed)
    return removed


RIM_MODEL_LABELS = ["{}.{}".format(table.app, table.model) for table in RIM_TABLES]
SLUM_DATA_LABEL, APPRAISAL_LABEL = RIM_MODEL_LABELS


def backup_fields(slum_id, version, source_model):
    """The serialised `fields` of one backed-up row, or None.

    A JSONField is dumped as a JSON string, so values are parsed back here.
    """
    row = (
        SlumVersionBackup.objects
        .filter(slum_id=slum_id, version=version, source_model=source_model)
        .values_list("data", flat=True)
        .first()
    )
    if not row:
        return None
    fields = dict((row or {}).get("fields") or {})
    for key, value in list(fields.items()):
        if isinstance(value, str) and value[:1] in ("{", "["):
            try:
                fields[key] = json.loads(value)
            except ValueError:
                pass
    return fields


def rim_backup_versions(slum_id):
    """Versions whose RIM sits in the backup, newest first."""
    rows = (
        SlumVersionBackup.objects
        .filter(slum_id=slum_id, source_model=SLUM_DATA_LABEL)
        .values_list("version", flat=True)
    )
    return sorted(set(rows), reverse=True)


def values_shaped(model, fields):
    """A backed-up row reshaped to match QuerySet.values().

    The serialiser writes a foreign key under the field's own name, while
    `.values()` yields `<name>_id`. Callers merge these dicts into their own
    context, so a key like `slum_name` holding an id would shadow the real one.
    """
    if not fields:
        return fields
    shaped = dict(fields)
    for field in model._meta.fields:
        if field.many_to_one and field.name in shaped:
            shaped[field.attname] = shaped.pop(field.name)
    return shaped


def rim_at(slum_id, version=None):
    """(rim_data, appraisal fields) for one version; `None` reads the live tables.

    The appraisal comes back shaped like `.values()` either way.
    """
    slum_data = apps.get_model("graphs", "SlumData")
    appraisal_model = apps.get_model("master", "Rapid_Slum_Appraisal")
    if version is None:
        rim_data = slum_data.objects.filter(slum_id=slum_id).values_list("rim_data", flat=True).first()
        appraisal = appraisal_model.objects.filter(slum_name_id=slum_id).values().first()
        return rim_data, appraisal
    fields = backup_fields(slum_id, version, SLUM_DATA_LABEL) or {}
    appraisal = values_shaped(appraisal_model, backup_fields(slum_id, version, APPRAISAL_LABEL))
    return fields.get("rim_data"), appraisal


def rim_choices_for(slum_id):
    """What the factsheet's version picker offers: the live RIM, then the archived ones."""
    choices = []
    live, _ = rim_at(slum_id)
    if live:
        choices.append({"version": None, "label": "Current", "live": True})
    for version in rim_backup_versions(slum_id):
        choices.append({"version": version, "label": "Version {}".format(version), "live": False})
    return choices


def describe(slum_id):
    """What the admin page shows for one slum."""
    versions = list(SlumDataVersion.objects.filter(slum_id=slum_id).order_by("version"))
    return {
        "live_counts": counts(slum_id),
        "household_counts": counts(slum_id, HOUSEHOLD_TABLES),
        "rim_counts": counts(slum_id, RIM_TABLES),
        "current": current_number(slum_id),
        "pending": pending_version(slum_id),
        "versions": [
            {
                "row": version,
                "backup": backup_counts(slum_id, version.version - 1),
                "has_backup": SlumVersionBackup.objects.filter(
                    slum_id=slum_id, version=version.version - 1,
                ).exists(),
            }
            for version in versions
        ],
        "aliases": list(SlumAlias.objects.filter(slum_id=slum_id).order_by("-is_primary", "external_id")),
    }
