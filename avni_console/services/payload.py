"""Build the AVNI write for one record.

Subjects and encounters have PATCH: observations are merged, a null removes
one, "Voided" is honoured, so only the changed keys are sent. Program
encounters and enrolments have PUT only: observations are replaced, so the
fetched body is re-sent with the edits applied.

Question groups come back from GET keyed by child concept *uuid* but must be
written keyed by child concept *name* (the server resolves names), so every
group is remapped before a write.
"""

from collections import namedtuple

from avni import paths
from avni_console.services import values

Write = namedtuple("Write", "method path body")

PATCH_FORM_TYPES = {"IndividualProfile", "Encounter"}
PATH_BUILDERS = {
    "IndividualProfile": paths.subject,
    "Encounter": paths.encounter,
    "ProgramEncounter": paths.program_encounter,
    "ProgramEnrolment": paths.program_enrolment,
}
# GET-only keys the request DTOs do not know; dropped from PUT bodies for clarity.
READ_ONLY_KEYS = {"ID", "audit", "Subject ID", "Subject external ID", "Subject type", "Enrolment ID",
                  "Enrolment external ID", "location", "Location ID", "Groups", "enrolments", "encounters"}


class QuestionMap(object):
    """Concept-name and uuid lookups for one form, including group parents."""

    def __init__(self, form):
        self.questions = {q.concept_name: q for q in form.questions.filter(is_active=True)}
        by_uuid = {q.uuid: q for q in self.questions.values()}
        self.parent_of = {
            q.concept_name: by_uuid[q.parent_uuid].concept_name
            for q in self.questions.values() if q.parent_uuid and q.parent_uuid in by_uuid
        }
        self.name_by_concept_uuid = {q.concept_uuid: q.concept_name for q in self.questions.values() if q.concept_uuid}

    def group_by_name(self, group_value):
        """{child uuid or name: value} -> {child name: value}; unknown uuids are kept as they are."""
        if not isinstance(group_value, dict):
            return group_value
        return {self.name_by_concept_uuid.get(key, key): value for key, value in group_value.items()}


def build_write(form, subject_type, record_uuid, fetched, changes, top_level):
    """`changes`: {concept name: value | CLEAR}; `top_level`: {"Voided": bool, "Registration date": ...}."""
    questions = QuestionMap(form)
    path = PATH_BUILDERS[form.form_type](record_uuid)
    if form.form_type in PATCH_FORM_TYPES:
        return Write("PATCH", path, patch_body(form, subject_type, fetched, changes, top_level, questions))
    return Write("PUT", path, put_body(fetched, changes, top_level, questions))


def patch_body(form, subject_type, fetched, changes, top_level, questions):
    body = {"Subject type": subject_type} if form.form_type == "IndividualProfile" else {"Encounter type": fetched.get("Encounter type")}
    observations = apply_changes({}, fetched.get("observations") or {}, changes, questions, clear_as_null=True)
    if observations:
        body["observations"] = observations
    body.update(top_level)
    return body


def put_body(fetched, changes, top_level, questions):
    body = {key: value for key, value in fetched.items() if key not in READ_ONLY_KEYS}
    current = {name: questions.group_by_name(value) for name, value in (fetched.get("observations") or {}).items()}
    body["observations"] = apply_changes(current, fetched.get("observations") or {}, changes, questions, clear_as_null=False)
    body.update(top_level)
    return body


def apply_changes(target, fetched_observations, changes, questions, clear_as_null):
    """Write `changes` into `target`; group children are written inside their (full) group."""
    for concept, value in changes.items():
        parent = questions.parent_of.get(concept)
        if parent is None:
            set_value(target, concept, value, clear_as_null)
            continue
        if parent not in target or not isinstance(target.get(parent), dict):
            target[parent] = questions.group_by_name(fetched_observations.get(parent) or {})
        set_value(target[parent], concept, value, clear_as_null)
    return target


def set_value(container, key, value, clear_as_null):
    if value is values.CLEAR:
        if clear_as_null:
            container[key] = None
        else:
            container.pop(key, None)
    else:
        container[key] = value


def current_values(form, fetched, concepts, top_level_fields=()):
    """What the record holds today for these concepts / top-level fields (None when absent)."""
    questions = QuestionMap(form)
    observations = fetched.get("observations") or {}
    current = {}
    for concept in concepts:
        parent = questions.parent_of.get(concept)
        if parent is None:
            current[concept] = observations.get(concept)
        else:
            current[concept] = questions.group_by_name(observations.get(parent) or {}).get(concept)
    for field in top_level_fields:
        current[field] = fetched.get(field)
    return current


def real_changes(form, fetched, changes):
    """Drop changes that would leave the value as it is (lists compare order-free)."""
    current = current_values(form, fetched, list(changes))
    kept = {}
    for concept, value in changes.items():
        old = current.get(concept)
        if value is values.CLEAR:
            if old is not None:
                kept[concept] = value
        elif not same(old, value):
            kept[concept] = value
    return kept


def same(old, new):
    if isinstance(old, list) and isinstance(new, list):
        return sorted(map(str, old)) == sorted(map(str, new))
    if old is None or new is None:
        return old is new
    return str(old) == str(new)
