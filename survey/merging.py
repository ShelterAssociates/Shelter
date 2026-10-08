"""Merge one slum into another: move every related row, then delete the empty slum.

Irreversible, so the page always shows the dry run first and writes a JSON dump
before applying.
"""

import json
import logging

from django.db import DatabaseError, transaction
from django.utils import timezone

from survey.models import Record, SlumAlias

logger = logging.getLogger(__name__)

# Rows the generic loop must not touch: the slum's own versions and backups go
# with it (the target keeps its own), while aliases and survey records are moved
# further down, where their version and slum name are set too.
SKIP_MODELS = {
    "survey.slumdataversion", "survey.slumversionbackup", "survey.slumalias",
    "survey.slumsyncsetting", "survey.record",
}


def related_relations():
    """Every reverse relation pointing at master.Slum."""
    from master.models import Slum

    return [
        relation for relation in Slum._meta.related_objects
        if relation.related_model is not None
    ]


def generic_relations():
    """Every GenericRelation on master.Slum.

    Mapped components point at a slum through a content type and an object id,
    so they are absent from `related_objects` and would be left behind -- and
    orphaned once the slum row goes.
    """
    from master.models import Slum

    return [
        field for field in Slum._meta.private_fields
        if hasattr(field, "object_id_field_name") and field.related_model is not None
    ]


def generic_rows(field, slum_id):
    from django.contrib.contenttypes.models import ContentType

    from master.models import Slum

    return field.related_model.objects.filter(**{
        field.content_type_field_name: ContentType.objects.get_for_model(Slum),
        field.object_id_field_name: slum_id,
    })


def label_of(relation):
    return relation.related_model._meta.label_lower


def rows_of(relation, slum_id):
    """Rows pointing at this slum. Works for a foreign key and for many-to-many."""
    return relation.related_model.objects.filter(**{relation.field.name: slum_id})


def move_rows(relation, source_id, target_id):
    """Re-point a relation's rows from one slum to another; returns the row count."""
    field = relation.field.name
    if relation.many_to_many:
        moved = 0
        for row in list(rows_of(relation, source_id)):
            members = getattr(row, field)
            members.remove(source_id)
            members.add(target_id)
            moved += 1
        return moved
    return rows_of(relation, source_id).update(**{field + "_id": target_id})


def unique_keys_with_slum(relation):
    """Field name tuples that are unique together with the slum field."""
    if relation.many_to_many:
        return []
    field = relation.field.name
    meta = relation.related_model._meta
    keys = []
    for together in meta.unique_together or ():
        if field in together:
            keys.append(tuple(name for name in together if name != field))
    return [key for key in keys if key]


def collisions(relation, source_id, target_id):
    """Rows that cannot move because the target already holds that unique key."""
    found = []
    for key in unique_keys_with_slum(relation):
        taken = set(rows_of(relation, target_id).values_list(*key))
        for values in rows_of(relation, source_id).values_list(*key):
            if values in taken:
                found.append({"key": key, "values": values})
    return found


def plan_merge(source_id, target_id):
    """What a merge would move, what blocks it, and what could not be read.

    A table whose columns do not match its model (an unapplied migration) is
    reported rather than raised, and it blocks the merge: a table we cannot read
    is one whose rows we cannot move.
    """
    moving, blocked, unreadable = {}, {}, {}
    for relation in related_relations():
        label = label_of(relation)
        if label in SKIP_MODELS:
            continue
        try:
            count = rows_of(relation, source_id).count()
            if not count:
                continue
            moving[label] = count
            clashes = collisions(relation, source_id, target_id)
        except DatabaseError as exc:
            unreadable[label] = str(exc).strip().splitlines()[0]
            continue
        if clashes:
            blocked[label] = clashes
    for field in generic_relations():
        label = label_of(field)
        try:
            count = generic_rows(field, source_id).count()
        except DatabaseError as exc:
            unreadable[label] = str(exc).strip().splitlines()[0]
            continue
        if count:
            moving[label] = moving.get(label, 0) + count
    return {
        "moving": moving,
        "blocked": blocked,
        "unreadable": unreadable,
        "records": Record.objects.filter(slum_id=source_id).count(),
        "aliases": list(SlumAlias.objects.filter(slum_id=source_id).values("provider", "external_id", "external_name")),
    }


def dump(source_id, target_id, report, path):
    payload = {
        "made_on": timezone.now().isoformat(),
        "source_slum": source_id,
        "target_slum": target_id,
        "report": {"moving": report["moving"], "records": report["records"], "aliases": report["aliases"]},
        "rows": {},
    }
    for relation in related_relations():
        label = label_of(relation)
        if label in SKIP_MODELS or label not in report["moving"]:
            continue
        try:
            payload["rows"][label] = list(rows_of(relation, source_id).values())
        except DatabaseError as exc:
            payload["rows"][label] = {"unreadable": str(exc).strip().splitlines()[0]}
    for field in generic_relations():
        label = label_of(field)
        if label not in report["moving"]:
            continue
        try:
            payload["rows"].setdefault(label, []).extend(generic_rows(field, source_id).values())
        except DatabaseError as exc:
            payload["rows"][label] = {"unreadable": str(exc).strip().splitlines()[0]}
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2, default=str)
    return path


def merge(source_id, target_id, version=None, dump_path=None):
    """Move the source slum's data onto the target, then delete the source slum.

    Refuses while anything is blocked or unreadable, so no row is silently
    dropped. The checks run before the transaction opens, because a failed query
    inside one would abort it.
    """
    from master.models import Slum

    if source_id == target_id:
        raise ValueError("A slum cannot be merged into itself")
    report = plan_merge(source_id, target_id)
    if report["unreadable"]:
        raise ValueError(
            "Merge stopped: these tables do not match their models, so run the migrations first - {}".format(
                ", ".join(sorted(report["unreadable"]))
            )
        )
    if report["blocked"]:
        raise ValueError(
            "Merge blocked: {} already holds these keys. Start the new version and let it go live first.".format(
                ", ".join(sorted(report["blocked"]))
            )
        )
    if dump_path:
        dump(source_id, target_id, report, dump_path)

    with transaction.atomic():
        target = Slum.objects.get(id=target_id)
        moved = {}
        for relation in related_relations():
            label = label_of(relation)
            if label in SKIP_MODELS or label not in report["moving"]:
                continue
            moved[label] = move_rows(relation, source_id, target_id)

        for field in generic_relations():
            label = label_of(field)
            if label not in report["moving"]:
                continue
            moved[label] = moved.get(label, 0) + generic_rows(field, source_id).update(
                **{field.object_id_field_name: target_id}
            )

        record_update = {"slum_id": target_id, "slum_name": target.name}
        if version:
            record_update["version"] = version
        moved["survey.record"] = Record.objects.filter(slum_id=source_id).update(**record_update)

        SlumAlias.objects.filter(slum_id=source_id).update(slum_id=target_id, is_primary=False)
        Slum.objects.filter(id=source_id).delete()
    logger.info("Slum %s merged into %s: %s", source_id, target_id, moved)
    return moved
