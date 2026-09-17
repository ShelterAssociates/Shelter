"""The generic sync loop: discover enabled kinds, list, normalize, store, then
hand the record to the provider's legacy writers.

Every entry point - the nightly job, a manual backfill, the subject explorer -
goes through sync_record, so one API pass feeds both the core store and the
legacy tables and the counts mean the same thing everywhere.
"""

import importlib
import logging
import threading
from collections import OrderedDict

from django.conf import settings

from notification.services import reporting
from survey import store, switches, window
from survey.models import Record
from survey.store import SyncContext  # noqa: F401 (re-exported: callers build one from here)

logger = logging.getLogger(__name__)

SCHEDULED_REASON = "scheduled, not yet done"
VOIDED_REASON = "voided"
EMPTY_REASON = "voided or empty observations"

# Program encounter types with their own nightly step; sync_kinds leaves them out.
NIGHTLY_EXCLUDED = ("Daily Reporting", "Household Level Daily Reporting", "Family factsheet")

HOUSEHOLD_SUBJECT_TYPES = ("Household", "Structure", "Detailed Socio Economic Survey")
DOWN_KINDS = ("enrolment", "encounter", "program_encounter")

_provider = None
_provider_lock = threading.Lock()


# -- provider loading ---------------------------------------------------------

def load_provider(dotted_path):
    module_path, _, attribute = dotted_path.rpartition(".")
    if not module_path:
        raise ImportError("SURVEY_PROVIDER must be a dotted path, got '{}'".format(dotted_path))
    return getattr(importlib.import_module(module_path), attribute)()


def provider():
    """The process-wide provider named by settings.SURVEY_PROVIDER."""
    global _provider
    with _provider_lock:
        if _provider is None:
            _provider = load_provider(settings.SURVEY_PROVIDER)
        return _provider


def use_provider(instance):
    """Make provider() return this instance (tests inject a fake here)."""
    global _provider
    with _provider_lock:
        _provider = instance


def reset_provider():
    use_provider(None)


def context_for(context=None):
    return context if context is not None else SyncContext(provider())


# -- one record ---------------------------------------------------------------

def sync_record(kind, raw, context):
    """Store one raw record and run its legacy writer. Returns True when legacy saved."""
    source = context.provider
    facts = source.facts(kind, raw)
    status = source.visit_status(kind, raw)

    if status == "scheduled":
        reporting.skip(slum=facts.slum_name or None, reason=SCHEDULED_REASON)
        context.bump("scheduled_only")
        return False

    if status == "voided" or source.is_skipped_by_legacy(kind, raw):
        reporting.skip(slum=facts.slum_name or None, reason=skip_reason(kind, status))
        if not store.unchanged(source.key, facts.external_id, facts.last_modified):
            store_quietly(kind, raw, context)
        return False

    if store.unchanged(source.key, facts.external_id, facts.last_modified):
        context.bump("unchanged")
        return False

    try:
        subject_raw = subject_for(kind, facts, context)
        normalized = source.normalize(kind, raw, subject_raw)
    except Exception as exc:
        logger.error("Record %s not read: %s", facts.external_id, exc)
        with reporting.record(key=facts.external_id):
            reporting.fail(exc)
        context.bump("failed")
        return False

    if kind == "program_encounter":
        ensure_enrolment(facts, subject_raw, context)

    with reporting.record(
        slum=normalized.slum_name or None,
        household=normalized.household_number or None,
        key=facts.external_id,
    ):
        store.upsert(normalized, context)
        saved = bool(source.legacy_save(kind, raw, context))
        if saved:
            context.bump("legacy_saved")
            store.link_household(normalized, context)
        return saved


def skip_reason(kind, status):
    """Today's reason strings, so job reports read exactly as they do now."""
    if kind == "subject":
        return VOIDED_REASON
    return EMPTY_REASON


def subject_for(kind, facts, context):
    """The subject a record hangs off, fetched once per run. Subjects need none."""
    if kind == "subject" or not facts.subject_external_id:
        return None
    return context.subject(facts.subject_external_id)


def ensure_enrolment(facts, subject_raw, context):
    """Enrolments cannot be listed on their own, so the first program encounter
    under one fetches it and stores it (quietly: no step record of its own)."""
    enrolment_id = facts.enrolment_external_id
    if not enrolment_id or enrolment_id in context.enrolments:
        return
    context.enrolments.add(enrolment_id)
    source = context.provider
    if Record.objects.filter(provider=source.key, kind="enrolment", external_id=enrolment_id).exists():
        return
    try:
        raw = source.get_enrolment(enrolment_id)
        normalized = source.normalize("enrolment", raw, subject_raw)
    except Exception as exc:
        logger.warning("Enrolment %s of %s not read: %s", enrolment_id, facts.external_id, exc)
        return
    store.upsert(normalized, context, quiet=True)
    if source.legacy_handles("enrolment", normalized.subject_type) and not source.is_skipped_by_legacy("enrolment", raw):
        source.legacy_save("enrolment", raw, context)


def store_quietly(kind, raw, context):
    """Keep a voided or empty record in the core store without failing the run."""
    source = context.provider
    facts = source.facts(kind, raw)
    try:
        subject_raw = subject_for(kind, facts, context)
    except Exception as exc:
        logger.warning("Subject of %s not read: %s", facts.external_id, exc)
        subject_raw = None
    try:
        normalized = source.normalize(kind, raw, subject_raw)
    except Exception as exc:
        logger.warning("Record %s not normalized: %s", facts.external_id, exc)
        context.bump("failed")
        return
    store.upsert(normalized, context, quiet=True)


# -- listing loops ------------------------------------------------------------

def sync_kind(kind, subject_type, program="", encounter_type="", from_date=None, context=None):
    """Every record of one kind modified since the window start. Returns the saved count.

    After each record the step notes `checkpoint` (that record's last-modified
    stamp) and `processed`, so a run that stops can be resumed from there.
    """
    context = context_for(context)
    before = context.snapshot()
    since = window.window_start(subject_type, from_date, kind, program, encounter_type)
    saved = 0
    processed = 0
    for raw in context.provider.iter_records(kind, subject_type, program, encounter_type, since):
        saved += int(sync_record(kind, raw, context))
        processed += 1
        stamp = context.provider.facts(kind, raw).last_modified
        if stamp:
            reporting.note(checkpoint=stamp, processed=processed)
    context.note(since=before)
    return saved


def step_name(row):
    """The job step a switch row belongs to; the legacy names are preserved."""
    if row.kind == "subject":
        return "households:{}".format(row.subject_type)
    if row.kind == "enrolment":
        return "enrolments:{}".format(row.program)
    if row.kind == "encounter":
        return "encounters:{}".format(row.encounter_type)
    return "program_encounters:{}/{}".format(row.program, row.encounter_type)


def enabled_rows(subject_types, kinds=DOWN_KINDS, exclude=NIGHTLY_EXCLUDED):
    """Enabled switch rows the provider can list, minus the excluded encounter types."""
    source = provider()
    rows = []
    for subject_type in subject_types:
        for row in switches.enabled_kinds(subject_type, kinds):
            if exclude and row.encounter_type in exclude:
                continue
            if not source.lists(row.kind):
                continue
            rows.append(row)
    return rows


def sync_kinds(subject_types, from_date=None, exclude=NIGHTLY_EXCLUDED, kinds=DOWN_KINDS, context=None):
    """One pass over every enabled kind of these subject types. {step name: saved}."""
    context = context_for(context)
    before = context.snapshot()
    rows = enabled_rows(subject_types, kinds, exclude)
    if not rows:
        logger.warning(
            "No enabled survey kinds for %s. Run avni_form_cache_refresh to build the catalog.",
            ", ".join(subject_types),
        )
        reporting.note(kinds=0)
        return {}
    results = OrderedDict()
    for row in rows:
        results[step_name(row)] = sync_kind(
            row.kind, row.subject_type, row.program, row.encounter_type, from_date, context
        )
    reporting.note(kinds=len(rows))
    context.note(since=before)
    return results


# -- one whole subject --------------------------------------------------------

def sync_subject(subject_external_id, context=None):
    """Registration plus everything under it, in order. {kind: counts}."""
    context = context_for(context)
    source = context.provider
    try:
        tree = source.get_subject_tree(subject_external_id)
    except Exception as exc:
        logger.error("Subject %s not read: %s", subject_external_id, exc)
        with reporting.record(key=subject_external_id):
            reporting.fail(exc)
        context.bump("failed")
        return {}

    subject_type = source.facts("subject", tree.subject).subject_type
    context.subjects[subject_external_id] = tree.subject
    summary = OrderedDict()

    for kind, raw in walk(tree):
        facts = source.facts(kind, raw)
        if not switches.is_enabled(subject_type, kind, facts.program, facts.encounter_type):
            continue
        before = dict(context.counts)
        sync_record(kind, raw, context)
        add_delta(summary.setdefault(kind, OrderedDict()), before, context.counts)
    return summary


def walk(tree):
    """(kind, raw) in the order a subject should be synced."""
    yield "subject", tree.subject
    for enrolment, program_encounters in tree.enrolments or ():
        yield "enrolment", enrolment
        for program_encounter in program_encounters or ():
            yield "program_encounter", program_encounter
    for encounter in tree.encounters or ():
        yield "encounter", encounter


def add_delta(bucket, before, after):
    for name, count in after.items():
        moved = count - before.get(name, 0)
        if moved:
            bucket[name] = bucket.get(name, 0) + moved


def describe_subject(subject_external_id, context=None):
    """Read-only preview for the console: identity plus a row per form."""
    context = context_for(context)
    source = context.provider
    tree = source.get_subject_tree(subject_external_id)
    subject = source.facts("subject", tree.subject)
    forms = []
    for kind, raw in walk(tree):
        facts = source.facts(kind, raw)
        forms.append(
            OrderedDict([
                ("kind", kind),
                ("program", facts.program),
                ("encounter_type", facts.encounter_type),
                ("form_name", facts.form_name),
                ("status", source.visit_status(kind, raw)),
                ("record_datetime", facts.record_datetime),
                ("last_modified", facts.last_modified),
                ("external_id", facts.external_id),
                ("synced", store.unchanged(source.key, facts.external_id, facts.last_modified)),
                ("legacy", source.legacy_handles(kind, subject.subject_type, facts.encounter_type)),
                ("enabled", switches.is_enabled(
                    subject.subject_type, kind, facts.program, facts.encounter_type)),
            ])
        )
    return OrderedDict([
        ("subject_id", subject.external_id),
        ("subject_type", subject.subject_type),
        ("slum", subject.slum_name),
        ("household_number", subject.household_number),
        ("registered_on", subject.record_datetime),
        ("last_modified", subject.last_modified),
        ("is_voided", source.visit_status("subject", tree.subject) == "voided"),
        ("forms", forms),
    ])
