"""AVNI as a survey provider: the one module that knows AVNI's shapes.

It reads the form catalog out of the cached definitions (avni.models), lists
and fetches records through avni.client, turns AVNI JSON into the connector's
flat Observations, and hands each record to the legacy writers in avni.sync,
which are untouched.
"""

import logging
import re
import time

import requests

from avni import mappings, metadata, paths
from avni.client import AvniError, client, page_path
from avni.models import AvniForm, AvniFormMapping
from avni.sync import encounters, households, members, mobilization, program_encounters, structures
from notification.services import reporting
from survey import contracts, identity

logger = logging.getLogger(__name__)

SUBJECT_PATH_PREFIX = "api/subject/"

# A read that fails with one of these is tried again, pausing longer each time.
RETRY_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 5
RETRYABLE_STATUSES = (408, 429, 500, 502, 503, 504)


sleep = time.sleep  # module attribute so tests can stub the pauses


def retrying(call, label="", attempts=RETRY_ATTEMPTS):
    """call() with automatic retries on timeouts, connection errors and 5xx answers."""
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except AvniError as exc:
            if exc.status_code not in RETRYABLE_STATUSES or attempt == attempts:
                raise
            reason = "AVNI {}".format(exc.status_code)
        except requests.RequestException as exc:
            if attempt == attempts:
                raise
            reason = type(exc).__name__
        pause = RETRY_PAUSE_SECONDS * attempt
        logger.warning("%s failed (%s); retry %s/%s in %ss", label or "AVNI read", reason, attempt, attempts - 1, pause)
        sleep(pause)
UUID_SHAPE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
LOCATION_KEYS = {"x", "y", "X", "Y", "latitude", "longitude", "accuracy", "altitude"}

FORM_TYPE_KINDS = {
    "IndividualProfile": "subject",
    "ProgramEnrolment": "enrolment",
    "Encounter": "encounter",
    "ProgramEncounter": "program_encounter",
}

# AVNI dataType -> the core vocabulary in survey.contracts.DATA_TYPES
CORE_DATA_TYPES = {
    "Coded": "coded", "Numeric": "numeric",
    "Text": "text", "Notes": "text", "Id": "text", "PhoneNumber": "text",
    "Date": "date", "DateTime": "datetime", "Time": "time", "Duration": "time",
    "Image": "media", "Video": "media", "Audio": "media", "File": "media",
    "Location": "location", "QuestionGroup": "group",
    "Subject": "reference", "Encounter": "reference", "GroupAffiliation": "reference",
}

# Subject types whose registration and encounters feed the legacy rhs tables.
LEGACY_HOUSEHOLD_TYPES = ("Household", "Structure", "Detailed Socio Economic Survey")
MOBILIZATION_ENCOUNTER = "Daily Mobilization Activity"
MEMBER_SUBJECT_TYPE = "Family Member"
LEGACY_PROGRAM_ENCOUNTER_TYPES = (
    program_encounters.FAMILY_FACTSHEET,
) + program_encounters.DAILY_REPORTING_TYPES

DATE_KEYS = {
    "subject": ("Registration date",),
    "enrolment": ("Enrolment datetime", "Enrolment date time"),
    "encounter": ("Encounter date time",),
    "program_encounter": ("Encounter date time",),
}


def first_of(raw, keys):
    for key in keys:
        value = raw.get(key)
        if value:
            return value
    return None


def core_data_type(avni_type):
    return CORE_DATA_TYPES.get(avni_type or "", "unknown")


def looks_like_uuid(key):
    return bool(UUID_SHAPE.match(str(key)))


def is_location(value):
    return isinstance(value, dict) and bool(value) and set(value) <= LOCATION_KEYS


def is_group_value(value):
    """A question group answer: one dict, or a list of dicts for a repeat group."""
    if isinstance(value, dict):
        return not is_location(value)
    return bool(value) and isinstance(value, list) and all(isinstance(item, dict) for item in value)


class CachingApi(object):
    """An api whose api/subject/<uuid> answers come from the run's subject memo."""

    def __init__(self, api, subjects):
        self.api = api
        self.subjects = subjects

    def get_json(self, path, timeout=None):
        if path.startswith(SUBJECT_PATH_PREFIX):
            uuid = path[len(SUBJECT_PATH_PREFIX):]
            if uuid not in self.subjects:
                self.subjects[uuid] = self.api.get_json(path, timeout=timeout)
            return self.subjects[uuid]
        return self.api.get_json(path, timeout=timeout)

    def __getattr__(self, name):
        return getattr(self.api, name)


class FormInfo(object):
    """One cached form: its identity and how to read a key out of its observations."""

    def __init__(self, uuid, name, questions):
        self.uuid = uuid
        self.name = name
        self.by_name = {}
        self.by_concept_uuid = {}
        for question in questions:
            ref = contracts.ConceptRef(
                external_id=question.concept_uuid or "",
                name=question.concept_name or "",
                data_type=core_data_type(question.data_type),
            )
            if ref.name:
                self.by_name[ref.name] = ref
            if ref.external_id:
                self.by_concept_uuid[ref.external_id] = ref

    def ref_for(self, key):
        """Top-level keys are concept names; question-group children are concept uuids."""
        ref = self.by_concept_uuid.get(key) or self.by_name.get(key)
        if ref is not None:
            return ref
        if looks_like_uuid(key):
            return contracts.ConceptRef(external_id=key, name="", data_type="unknown")
        return contracts.ConceptRef(external_id="", name=str(key), data_type="unknown")


EMPTY_FORM = FormInfo("", "", [])


def sync_context(api=None):
    """A SyncContext for the legacy entry points; an explicit api gets its own provider."""
    from survey import connector
    from survey.store import SyncContext

    source = AvniProvider(api=api) if api is not None else connector.provider()
    if hasattr(source, "refresh_forms_if_stale"):
        source.refresh_forms_if_stale()
    return SyncContext(source)


class AvniProvider(contracts.Provider):
    key = "avni"

    def __init__(self, api=None):
        self._api = api
        self._forms = None

    def api(self):
        return self._api or client()

    def read(self, path):
        """One GET with transient-error retries."""
        return retrying(lambda: self.api().get_json(path), label=path)

    def reset_forms(self):
        """Drop the form index after a form cache refresh."""
        self._forms = None
        self._forms_stamp = None

    def refresh_forms_if_stale(self):
        """One query: rebuild the index when the cache was refreshed since it was built."""
        stamp = AvniForm.objects.filter(is_active=True).order_by("-fetched_on").values_list("fetched_on", flat=True).first()
        if self._forms is not None and stamp != getattr(self, "_forms_stamp", None):
            self._forms = None
        self._forms_stamp = stamp

    # -- catalog --------------------------------------------------------------

    def catalog(self):
        entries = []
        for mapping in metadata.active_mappings():
            kind = FORM_TYPE_KINDS.get(mapping.form.form_type)
            if kind is None:
                continue
            entries.append(contracts.CatalogEntry(
                subject_type=mapping.subject_type,
                kind=kind,
                program=mapping.program or "",
                encounter_type=mapping.encounter_type or "",
                label=mapping.form.name,
                form_external_id=mapping.form.uuid,
                concepts=form_concepts(mapping.form),
            ))
        return entries

    # -- form index -----------------------------------------------------------

    def forms(self):
        if self._forms is None:
            self._forms = build_form_index()
        return self._forms

    def form_for(self, kind, subject_type, program="", encounter_type=""):
        index = self.forms()
        exact = index["by_key"].get((subject_type or "", kind, program or "", encounter_type or ""))
        if exact is not None:
            return exact
        return index["by_type"].get((kind, encounter_type or "", program or ""), EMPTY_FORM)

    # -- listing and fetching -------------------------------------------------

    def lists(self, kind):
        """api/programEnrolments needs subject AND program, so enrolments cannot be
        listed by type; the connector fetches them on demand (get_enrolment)."""
        return kind != "enrolment"

    def list_path(self, kind, subject_type, program, encounter_type, since):
        if kind == "subject":
            return paths.subjects(subject_type, since)
        if kind == "encounter":
            return paths.encounters(encounter_type, since)
        if kind == "program_encounter":
            return paths.program_encounters(encounter_type, since)
        raise ValueError("AVNI cannot list {} records by type".format(kind))

    def iter_records(self, kind, subject_type, program="", encounter_type="", since=None):
        path = self.list_path(kind, subject_type, program, encounter_type, since)
        first = self.read(path)
        pages = [first.get("content", [])]
        for number in range(1, first.get("totalPages", 0)):
            pages.append(None)
        for number, page in enumerate(pages):
            if page is None:
                page = self.read(page_path(path, number)).get("content", [])
            for record in page:
                if kind == "subject" and subject_type and not record.get("Subject type"):
                    record["Subject type"] = subject_type
                yield record

    def get_subject(self, subject_external_id):
        return self.read(paths.subject(subject_external_id))

    def get_enrolment(self, enrolment_external_id):
        return self.read(paths.program_enrolment(enrolment_external_id))

    def get_subject_tree(self, subject_external_id):
        self.refresh_forms_if_stale()
        subject = self.get_subject(subject_external_id)
        enrolments = []
        for item in subject.get("enrolments") or ():
            enrolment = self.fetch_child(item, paths.program_enrolment)
            if enrolment is None:
                continue
            children = [
                child for child in (
                    self.fetch_child(entry, paths.program_encounter)
                    for entry in enrolment.get("encounters") or ()
                ) if child is not None
            ]
            enrolments.append((enrolment, children))
        encounters_under = [
            child for child in (
                self.fetch_child(entry, paths.encounter)
                for entry in subject.get("encounters") or ()
            ) if child is not None
        ]
        return contracts.SubjectTree(subject, enrolments, encounters_under)

    def fetch_child(self, entry, path_builder):
        """A uuid list entry; some AVNI versions inline the record instead."""
        if isinstance(entry, dict):
            return entry
        try:
            return self.read(path_builder(entry))
        except Exception as exc:
            logger.error("Record %s under the subject not fetched: %s", entry, exc)
            return None

    # -- reading a raw record -------------------------------------------------

    def facts(self, kind, raw):
        observations = raw.get("observations") or {}
        location = raw.get("location") or {}
        is_subject = kind == "subject"
        external_id = raw.get("ID") or raw.get("uuid") or ""
        subject_id = external_id if is_subject else (raw.get("Subject ID") or "")
        subject_type = raw.get("Subject type") or ""
        encounter_type = raw.get("Encounter type") or ""
        program = raw.get("Program") or ""
        form = self.form_for(kind, subject_type, program, encounter_type)
        return contracts.RecordFacts(
            external_id=external_id,
            subject_external_id=subject_id,
            subject_type=subject_type,
            program=program,
            encounter_type=encounter_type,
            form_name=form.name,
            record_datetime=first_of(raw, DATE_KEYS.get(kind, ())),
            last_modified=(raw.get("audit") or {}).get("Last modified at"),
            slum_name=(location.get("Slum") or "") if is_subject else "",
            household_number=identity.household_number_from(observations.get("First name")) if is_subject else "",
            enrolment_external_id=raw.get("Enrolment ID") or "",
        )

    def visit_status(self, kind, raw):
        if raw.get("Voided"):
            return "voided"
        if kind in ("subject", "enrolment"):
            return "done"
        if raw.get("Cancel date time"):
            return "cancelled"
        if not raw.get("Encounter date time") and not (raw.get("observations") or {}):
            return "scheduled"
        return "done"

    def is_skipped_by_legacy(self, kind, raw):
        if kind == "subject":
            return bool(raw.get("Voided"))
        return bool(raw.get("Voided")) or not (raw.get("observations") or {})

    def subject_type_of(self, kind, raw, subject_raw=None):
        return raw.get("Subject type") or (subject_raw or {}).get("Subject type") or ""

    def normalize(self, kind, raw, subject_raw=None):
        identity_source = raw if kind == "subject" else (subject_raw or {})
        location = identity_source.get("location") or {}
        subject_observations = identity_source.get("observations") or {}
        subject_type = self.subject_type_of(kind, raw, subject_raw)
        encounter_type = raw.get("Encounter type") or ""
        program = raw.get("Program") or ""
        form = self.form_for(kind, subject_type, program, encounter_type)
        external_id = raw.get("ID") or raw.get("uuid") or ""
        return contracts.NormalizedRecord(
            kind=kind,
            external_id=external_id,
            subject_external_id=external_id if kind == "subject" else (raw.get("Subject ID") or ""),
            subject_type=subject_type,
            program=program,
            encounter_type=encounter_type,
            form_external_id=form.uuid,
            form_name=form.name,
            slum_name=location.get("Slum") or "",
            city_name=location.get("City") or "",
            household_number=identity.household_number_from(subject_observations.get("First name")),
            record_datetime=first_of(raw, DATE_KEYS.get(kind, ())),
            earliest_scheduled=raw.get("Earliest scheduled date"),
            max_scheduled=raw.get("Max scheduled date"),
            cancel_datetime=raw.get("Cancel date time"),
            exit_datetime=first_of(raw, ("Exit date time", "Program exit date time")),
            is_voided=bool(raw.get("Voided")),
            created_at=(raw.get("audit") or {}).get("Created at"),
            last_modified_at=(raw.get("audit") or {}).get("Last modified at"),
            observations=walk_observations(raw.get("observations"), form),
        )

    # -- legacy writers -------------------------------------------------------

    def api_for(self, context):
        if context.api is None:
            context.api = CachingApi(self.api(), context.subjects)
        return context.api

    def legacy_handles(self, kind, subject_type, encounter_type=""):
        if kind == "subject":
            return subject_type in LEGACY_SUBJECT_WRITERS
        if subject_type == MEMBER_SUBJECT_TYPE:
            return kind in ("enrolment", "program_encounter")
        if kind == "encounter":
            return subject_type in LEGACY_HOUSEHOLD_TYPES
        if kind == "program_encounter":
            return (
                subject_type in LEGACY_HOUSEHOLD_TYPES
                and encounter_type in LEGACY_PROGRAM_ENCOUNTER_TYPES
            )
        return False

    def legacy_void(self, kind, raw, context):
        if kind != "subject" or raw.get("Subject type") not in LEGACY_HOUSEHOLD_TYPES:
            return 0
        try:
            return households.remove_voided_household(raw)
        except Exception as exc:
            logger.error("Voided subject %s not removed: %s", raw.get("ID"), exc)
            return 0

    def legacy_save(self, kind, raw, context):
        try:
            return bool(self.dispatch(kind, raw, context))
        except Exception as exc:
            logger.error("%s %s not saved: %s", kind, raw.get("ID"), exc)
            reporting.fail(exc)
            return False

    def dispatch(self, kind, raw, context):
        subject_raw = None
        if kind != "subject":
            subject_id = raw.get("Subject ID")
            if not subject_id:
                return False
            subject_raw = context.subject(subject_id)
        subject_type = self.subject_type_of(kind, raw, subject_raw)

        if kind == "subject":
            writer = LEGACY_SUBJECT_WRITERS.get(subject_type)
            return writer(raw) if writer else False
        if subject_type == MEMBER_SUBJECT_TYPE:
            return self.save_member_child(kind, raw)
        if kind == "enrolment":
            return False
        self.api_for(context)
        household = households.household_from_record(subject_raw)
        if kind == "encounter":
            return self.save_encounter(raw, household, subject_type)
        return self.save_program_encounter(raw, household, subject_type)

    def save_member_child(self, kind, raw):
        if kind == "enrolment":
            return members.save_member_program_from_record(raw)
        if kind == "program_encounter":
            return members.save_member_encounter_from_record(raw)
        return False

    def save_encounter(self, raw, household, subject_type):
        if subject_type not in LEGACY_HOUSEHOLD_TYPES:
            return False
        encounter_type = raw.get("Encounter type")
        if encounter_type == MOBILIZATION_ENCOUNTER:
            mobilization.save_activity_attendance(
                raw.get("observations") or {}, household.slum, household.number
            )
            return True
        encounters.save_encounter_for(household, legacy_encounter(raw))
        return True

    def save_program_encounter(self, raw, household, subject_type):
        if subject_type not in LEGACY_HOUSEHOLD_TYPES:
            return False
        if raw.get("Encounter type") not in LEGACY_PROGRAM_ENCOUNTER_TYPES:
            return False
        return bool(program_encounters.save_program_encounter(raw, household))


def legacy_encounter(raw):
    """A DSES '... INP' encounter re-stamped with its Household twin type."""
    twin = mappings.LEGACY_TWIN_TYPES.get(raw.get("Encounter type"))
    if not twin:
        return raw
    copy = dict(raw)
    copy["Encounter type"] = twin
    return copy


LEGACY_SUBJECT_WRITERS = {
    "Household": households.save_household,
    "Structure": households.save_household,
    "Detailed Socio Economic Survey": structures.save_structure_record,
    mobilization.SUBJECT_TYPE: mobilization.save_mobilization,
    MEMBER_SUBJECT_TYPE: members.save_member_from_record,
}


# -- catalog helpers ----------------------------------------------------------

def form_concepts(form):
    """[(question ref, [answer refs])] for a form, from its cached export."""
    groups = (form.definition or {}).get("formElementGroups")
    if groups:
        return concepts_from_definition(groups)
    return concepts_from_questions(form)


def concepts_from_definition(groups):
    found = []
    for group in groups:
        if group.get("voided"):
            continue
        for element in group.get("formElements") or ():
            if element.get("voided") or not element.get("concept"):
                continue
            concept = element["concept"]
            question = contracts.ConceptRef(
                external_id=concept.get("uuid") or "",
                name=concept.get("name") or "",
                data_type=core_data_type(concept.get("dataType")),
            )
            answers = [
                contracts.ConceptRef(external_id=answer.get("uuid") or "", name=answer["name"], data_type="answer")
                for answer in concept.get("answers") or ()
                if answer.get("name") and not answer.get("voided")
            ]
            found.append((question, answers))
    return found


def concepts_from_questions(form):
    """Fallback when a form's export was never stored: names only, no answer uuids."""
    found = []
    for question in form.questions.filter(is_active=True):
        ref = contracts.ConceptRef(
            external_id=question.concept_uuid or "",
            name=question.concept_name,
            data_type=core_data_type(question.data_type),
        )
        answers = [
            contracts.ConceptRef(name=name, data_type="answer") for name in question.answers or ()
        ]
        found.append((ref, answers))
    return found


def build_form_index():
    """(subject type, kind, program, encounter type) -> FormInfo, plus a type-only fallback."""
    by_key, by_type, seen_twice = {}, {}, set()
    mappings_qs = (
        AvniFormMapping.objects.filter(is_active=True, form__is_active=True)
        .select_related("form")
        .prefetch_related("form__questions")
    )
    for mapping in mappings_qs:
        kind = FORM_TYPE_KINDS.get(mapping.form.form_type)
        if kind is None:
            continue
        info = FormInfo(
            mapping.form.uuid,
            mapping.form.name,
            [q for q in mapping.form.questions.all() if q.is_active],
        )
        by_key[(mapping.subject_type, kind, mapping.program or "", mapping.encounter_type or "")] = info
        type_key = (kind, mapping.encounter_type or "", mapping.program or "")
        if type_key in by_type and by_type[type_key].uuid != info.uuid:
            seen_twice.add(type_key)
        by_type[type_key] = info
    for type_key in seen_twice:
        by_type.pop(type_key, None)
    return {"by_key": by_key, "by_type": by_type}


# -- observation walking ------------------------------------------------------

def walk_observations(observations, form, group=None, repeat_index=0, counter=None):
    """AVNI observations -> flat Observations; groups and repeats keep their place."""
    counter = counter if counter is not None else [0]
    found = []
    for key, value in (observations or {}).items():
        if value is None or value == "" or value == []:
            continue
        ref = (form or EMPTY_FORM).ref_for(key)
        if ref.data_type == "group" or (ref.data_type == "unknown" and is_group_value(value)):
            found.extend(walk_group(ref, value, form, counter))
            continue
        for item in as_items(ref.data_type, value):
            found.append(contracts.Observation(
                question=ref,
                value=item,
                group=group,
                repeat_index=repeat_index,
                position=take(counter),
                answer_name=item if ref.data_type == "coded" and isinstance(item, str) else "",
            ))
    return found


def walk_group(ref, value, form, counter):
    if isinstance(value, list):
        found = []
        for index, item in enumerate(value):
            if isinstance(item, dict):
                found.extend(walk_observations(item, form, group=ref, repeat_index=index, counter=counter))
        return found
    if isinstance(value, dict):
        return walk_observations(value, form, group=ref, repeat_index=0, counter=counter)
    return []


def as_items(data_type, value):
    """Multi-selects and media lists become one observation per entry."""
    if isinstance(value, (list, tuple)) and data_type != "location":
        return list(value)
    return [value]


def take(counter):
    position = counter[0]
    counter[0] += 1
    return position
