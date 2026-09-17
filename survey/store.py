"""Writes a NormalizedRecord into Record + Answer.

Provider JSON never reaches this module: the provider has already walked its
own shapes and handed over flat Observations. What is left here is resolving
identity (slum, household, version), coercing values by their core data type
and replacing a record's answers in one transaction.
"""

import json
import logging
from collections import OrderedDict
from datetime import date, datetime

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from notification.services import reporting
from survey import concepts as dictionary
from survey import identity, locations, versions
from survey.models import Answer, Concept, Record

logger = logging.getLogger(__name__)

ACTIVE_HOUSEHOLD_CONSTRAINT = "survey_record_one_active_household"
ISO_DAY_LENGTH = 10

COUNTERS = (
    "created", "updated", "unchanged", "voided", "scheduled_only",
    "unlinked", "duplicate_household", "failed", "legacy_saved",
)
ALWAYS_NOTED = ("created", "updated")


class SyncContext(object):
    """One run's memos and counters, shared by every entry point."""

    def __init__(self, provider, api=None):
        self.provider = provider
        self.api = api
        self.concepts = dictionary.ConceptCache()
        self.answer_concepts = {}
        self.versions = {}
        self.slum_ids = {}
        self.subjects = {}
        self.enrolments = set()
        self.household_rows = {}
        self.counts = OrderedDict((name, 0) for name in COUNTERS)

    def subject(self, subject_external_id):
        """The provider's subject record, fetched once per run."""
        if subject_external_id not in self.subjects:
            self.subjects[subject_external_id] = self.provider.get_subject(subject_external_id)
        return self.subjects[subject_external_id]

    def bump(self, name, by=1):
        self.counts[name] = self.counts.get(name, 0) + by

    def summary(self):
        return OrderedDict((name, count) for name, count in self.counts.items() if count)

    def snapshot(self):
        return dict(self.counts)

    def moved_since(self, snapshot):
        """Counts moved since `snapshot()`; created and updated are always present."""
        moved = OrderedDict()
        for name, count in self.counts.items():
            delta = count - snapshot.get(name, 0)
            if delta or name in ALWAYS_NOTED:
                moved[name] = delta
        return moved

    def note(self, since=None):
        """Put the counts (or the ones moved since a snapshot) on the active step."""
        summary = self.moved_since(since) if since is not None else self.summary()
        if summary:
            reporting.note(**summary)
        return summary


# -- moments ------------------------------------------------------------------

def parse_moment(value):
    """Anything a provider calls a date -> aware datetime, or None."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return timezone.make_aware(value) if timezone.is_naive(value) else value
    if isinstance(value, date):
        return timezone.make_aware(datetime(value.year, value.month, value.day))
    text = str(value).strip()
    moment = parse_datetime(text)
    if moment is None:
        day = parse_date(text[:ISO_DAY_LENGTH])
        moment = datetime(day.year, day.month, day.day) if day else None
    if moment is None:
        moment = fuzzy_moment(text)
    if moment is None:
        return None
    return timezone.make_aware(moment) if timezone.is_naive(moment) else moment


def fuzzy_moment(text):
    try:
        import dateparser

        return dateparser.parse(text)
    except Exception:
        return None


# -- identity -----------------------------------------------------------------

def resolve_slum(slum_name, context):
    if not slum_name:
        return None, None
    if slum_name not in context.slum_ids:
        try:
            context.slum_ids[slum_name] = locations.slum_and_city_ids(slum_name)
        except LookupError:
            context.slum_ids[slum_name] = (None, None)
    return context.slum_ids[slum_name]


def household_id_for(normalized, slum_id, context):
    """The legacy HouseholdData row, via the subject's own Record when there is one."""
    subject_id = normalized.subject_external_id or normalized.external_id
    if subject_id and subject_id in context.household_rows:
        return context.household_rows[subject_id]
    household_id = None
    if subject_id and normalized.kind != "subject":
        household_id = (
            Record.objects.filter(provider=context.provider.key, kind="subject", external_id=subject_id)
            .exclude(household__isnull=True)
            .values_list("household_id", flat=True)
            .first()
        )
    if household_id is None:
        household_id = household_id_by_number(slum_id, normalized.household_number)
    if subject_id:
        context.household_rows[subject_id] = household_id
    return household_id


def household_id_by_number(slum_id, household_number):
    if not slum_id or not household_number:
        return None
    from graphs.models import HouseholdData

    return (
        HouseholdData.objects.filter(slum_id=slum_id, household_number=household_number)
        .values_list("id", flat=True)
        .first()
    )


def link_household(normalized, context):
    """Re-check the household link after the legacy writer may have created the row."""
    slum_id, _ = resolve_slum(normalized.slum_name, context)
    household_id = household_id_by_number(slum_id, normalized.household_number)
    if household_id is None:
        return False
    subject_id = normalized.subject_external_id or normalized.external_id
    if subject_id:
        context.household_rows[subject_id] = household_id
    updated = Record.objects.filter(
        provider=context.provider.key, external_id=normalized.external_id, household__isnull=True
    ).update(household_id=household_id)
    if updated:
        context.bump("unlinked", -1)
    return bool(updated)


# -- writing ------------------------------------------------------------------

def record_fields(normalized, context):
    slum_id, city_id = resolve_slum(normalized.slum_name, context)
    last_modified = parse_moment(normalized.last_modified_at)
    return {
        "version": versions.version_for(slum_id, last_modified or timezone.now(), context.versions),
        "kind": normalized.kind,
        "subject_external_id": normalized.subject_external_id or "",
        "subject_type": normalized.subject_type or "",
        "program": normalized.program or "",
        "encounter_type": normalized.encounter_type or "",
        "form_external_id": normalized.form_external_id or "",
        "form_name": normalized.form_name or "",
        "slum_id": slum_id,
        "city_id": city_id,
        "slum_name": normalized.slum_name or "",
        "household_id": household_id_for(normalized, slum_id, context),
        "household_number": identity.household_number_from(normalized.household_number)[:20],
        "record_datetime": parse_moment(normalized.record_datetime),
        "earliest_scheduled": parse_moment(normalized.earliest_scheduled),
        "max_scheduled": parse_moment(normalized.max_scheduled),
        "cancel_datetime": parse_moment(normalized.cancel_datetime),
        "exit_datetime": parse_moment(normalized.exit_datetime),
        "is_voided": bool(normalized.is_voided),
        "created_at": parse_moment(normalized.created_at),
        "last_modified_at": last_modified,
        "synced_on": timezone.now(),
    }


def unchanged(provider_key, external_id, last_modified_at):
    """True when this exact record version is already stored; needs no subject fetch."""
    moment = parse_moment(last_modified_at)
    if moment is None or not external_id:
        return False
    return Record.objects.filter(
        provider=provider_key, external_id=external_id, last_modified_at=moment
    ).exists()


def upsert(normalized, context, quiet=False):
    """created | updated | failed. quiet=True never raises and never reports."""
    try:
        return write(normalized, context)
    except IntegrityError as exc:
        return on_integrity_error(normalized, context, exc, quiet)
    except Exception as exc:
        if not quiet:
            raise
        logger.warning("Record %s not stored: %s", normalized.external_id, exc)
        context.bump("failed")
        return "failed"


def write(normalized, context):
    fields = record_fields(normalized, context)
    version = fields.pop("version")
    with transaction.atomic():
        record, created = Record.objects.update_or_create(
            provider=context.provider.key,
            external_id=normalized.external_id,
            version=version,
            defaults=fields,
        )
        record.answers.all().delete()
        rows = answer_rows(record, normalized.observations, context)
        if rows:
            Answer.objects.bulk_create(rows)
    context.bump("created" if created else "updated")
    if fields["is_voided"]:
        context.bump("voided")
    if fields["household_id"] is None and fields["household_number"]:
        context.bump("unlinked")
    return "created" if created else "updated"


def on_integrity_error(normalized, context, exc, quiet):
    if ACTIVE_HOUSEHOLD_CONSTRAINT not in str(exc):
        if quiet:
            logger.warning("Record %s not stored: %s", normalized.external_id, exc)
            context.bump("failed")
            return "failed"
        raise
    context.bump("duplicate_household")
    context.bump("failed")
    if not quiet:
        reporting.fail(ValueError(duplicate_message(normalized, context)))
    logger.error("Record %s not stored: %s", normalized.external_id, duplicate_message(normalized, context))
    return "failed"


def duplicate_message(normalized, context):
    slum_id, _ = resolve_slum(normalized.slum_name, context)
    holder = (
        Record.objects.filter(
            provider=context.provider.key, kind="subject", is_voided=False,
            slum_id=slum_id, household_number=normalized.household_number,
        )
        .exclude(external_id=normalized.external_id)
        .values_list("external_id", flat=True)
        .first()
    )
    return "household number {} already active in {} (id {})".format(
        normalized.household_number, normalized.slum_name or "-", holder or "-"
    )


# -- answers ------------------------------------------------------------------

def answer_rows(record, observations, context):
    """One Answer per Observation, typed by the question's core data type."""
    rows = []
    provider_key = context.provider.key
    for observation in observations or ():
        question = dictionary.resolve(
            observation.question, provider_key, role="question", cache=context.concepts
        )
        if question is None:
            continue
        group = None
        if observation.group:
            group = dictionary.resolve(
                observation.group, provider_key, role="question", cache=context.concepts
            )
        row = Answer(
            record=record, question=question, group=group,
            repeat_index=observation.repeat_index or 0, position=observation.position or 0,
        )
        apply_value(row, question.data_type, observation, context)
        rows.append(row)
    return rows


def apply_value(row, data_type, observation, context):
    value = observation.value
    if data_type == "coded" or observation.answer_name:
        set_coded(row, observation, context)
    elif data_type == "numeric":
        set_number(row, value)
    elif data_type in ("date", "datetime", "time"):
        set_moment(row, value)
    elif data_type == "location":
        row.value_text = as_json(value)
    elif data_type in ("media", "text", "reference", "group"):
        row.value_text = as_text(value)
    else:
        infer_value(row, value, context)


def set_coded(row, observation, context):
    name = observation.answer_name or as_text(observation.value)
    row.value_text = name
    if not name:
        return
    reference = observation.question._replace(external_id="", name=name, data_type="answer")
    row.answer = dictionary.resolve(reference, row.record.provider, role="answer", cache=context.concepts)


def set_number(row, value):
    row.value_text = number_text(value)
    try:
        row.value_number = float(value)
    except (TypeError, ValueError):
        row.value_number = None


def set_moment(row, value):
    moment = parse_moment(value)
    if moment is None:
        row.value_text = as_text(value)
        return
    row.value_date = moment
    row.value_text = moment.isoformat()


def infer_value(row, value, context):
    """No declared type: read it off the value itself."""
    if isinstance(value, bool):
        row.value_text = "Yes" if value else "No"
    elif isinstance(value, (int, float)):
        set_number(row, value)
    elif isinstance(value, (dict, list, tuple)):
        row.value_text = as_json(value)
    else:
        row.value_text = as_text(value)
        row.answer = known_answer(row.value_text, context)


def known_answer(name, context):
    """A coded answer already in the dictionary, so free text still joins up."""
    if not name or len(name) > 500:
        return None
    if name not in context.answer_concepts:
        context.answer_concepts[name] = Concept.objects.filter(name=name, is_answer=True).first()
    return context.answer_concepts[name]


def number_text(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return as_text(value)


def as_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return as_json(value)
    return str(value)


def as_json(value):
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except Exception:
        return str(value)
