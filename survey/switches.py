"""Admin on/off for each form of each subject type, with a subject-level parent.

Rows are upserted from the provider's form catalog. A kind with no row follows
DEFAULT_ON_SUBJECT_TYPES: the household steps keep running before the first
catalog refresh, anything else waits for its switch.
"""

import logging

from survey.models import SyncSwitch

logger = logging.getLogger(__name__)

# Subject types whose switches are created ON. Everything else the provider
# offers (Toilet, Slum-RIM, Family Member, ...) arrives switched off, so a new
# subject type appearing in the catalog never starts syncing by itself.
DEFAULT_ON_SUBJECT_TYPES = (
    "Household", "Structure", "Detailed Socio Economic Survey", "New_Mobilization_Form",
)


def provider_key(value=None):
    if value:
        return value
    from survey import connector

    return connector.provider().key


def rows_for(subject_type, provider=None):
    return SyncSwitch.objects.filter(provider=provider_key(provider), subject_type=subject_type)


def parent_of(row):
    """The subject-level switch of the same subject type, or None."""
    if row.kind == "subject":
        return None
    return SyncSwitch.objects.filter(
        provider=row.provider, subject_type=row.subject_type, kind="subject"
    ).first()


def effective_enabled(row, parent=None):
    """Own flag AND the subject switch; a missing parent leaves the own flag alone."""
    if not row.is_enabled:
        return False
    parent = parent if parent is not None else parent_of(row)
    return True if parent is None else parent.is_enabled


def is_enabled(subject_type, kind, program="", encounter_type="", provider=None):
    """No row for this kind -> enabled, unless its subject switch exists and is off.

    A blank program matches any program, so callers that only know the
    encounter type (the legacy steps) still find their switch.
    """
    key = provider_key(provider)
    rows = SyncSwitch.objects.filter(
        provider=key, subject_type=subject_type, kind=kind, encounter_type=encounter_type or ""
    )
    if program:
        rows = rows.filter(program=program)
    row = rows.order_by("program").first()
    if row is not None:
        return effective_enabled(row)
    parent = None
    if kind != "subject":
        parent = SyncSwitch.objects.filter(provider=key, subject_type=subject_type, kind="subject").first()
    if parent is not None:
        return parent.is_enabled
    return subject_type in DEFAULT_ON_SUBJECT_TYPES


def enabled_kinds(subject_type, kinds=None, provider=None):
    """Every enabled switch row of a subject type, optionally limited to some kinds."""
    rows = rows_for(subject_type, provider).filter(is_available=True)
    if kinds:
        rows = rows.filter(kind__in=list(kinds))
    parent = SyncSwitch.objects.filter(
        provider=provider_key(provider), subject_type=subject_type, kind="subject"
    ).first()
    return [row for row in rows.order_by("kind", "program", "encounter_type") if effective_enabled(row, parent)]


def enabled_encounter_types(subject_type, provider=None):
    return sorted(
        {row.encounter_type for row in enabled_kinds(subject_type, ["encounter"], provider) if row.encounter_type}
    )


def enabled_subject_types(kinds=None, provider=None):
    rows = SyncSwitch.objects.filter(provider=provider_key(provider), is_available=True)
    if kinds:
        rows = rows.filter(kind__in=list(kinds))
    return sorted({row.subject_type for row in rows if effective_enabled(row)})


def disabled_step_names(steps, provider=None):
    """{step name} for the (name, switch spec) pairs whose switch is off."""
    disabled = set()
    for name, spec in steps:
        if spec and not is_enabled(*spec, provider=provider):
            disabled.add(name)
    return disabled


def sync_catalog(provider):
    """Upsert a switch per catalog entry; entries that vanished go unavailable."""
    counts = {"created": 0, "seen": 0, "deactivated": 0}
    seen_ids = []
    for entry in provider.catalog():
        row, created = SyncSwitch.objects.get_or_create(
            provider=provider.key,
            subject_type=entry.subject_type,
            kind=entry.kind,
            program=entry.program or "",
            encounter_type=entry.encounter_type or "",
            defaults={
                "label": entry.label or "",
                "form_external_id": entry.form_external_id or "",
                "is_enabled": entry.subject_type in DEFAULT_ON_SUBJECT_TYPES,
            },
        )
        fields = []
        if entry.label and row.label != entry.label:
            row.label = entry.label
            fields.append("label")
        if entry.form_external_id and row.form_external_id != entry.form_external_id:
            row.form_external_id = entry.form_external_id
            fields.append("form_external_id")
        if not row.is_available:
            row.is_available = True
            fields.append("is_available")
        if fields:
            row.save(update_fields=fields)
        counts["created"] += int(created)
        counts["seen"] += 1
        seen_ids.append(row.pk)
    counts["deactivated"] = (
        SyncSwitch.objects.filter(provider=provider.key, is_available=True)
        .exclude(pk__in=seen_ids)
        .update(is_available=False)
    )
    return counts
