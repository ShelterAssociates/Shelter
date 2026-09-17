"""What a survey provider hands the connector, and what the connector expects of it.

A provider translates its own API into these namedtuples; nothing below this
line ever sees provider JSON.
"""

from collections import namedtuple

DATA_TYPES = (
    "coded", "numeric", "text", "date", "datetime", "time",
    "media", "location", "group", "reference", "unknown",
)
KINDS = ("subject", "enrolment", "encounter", "program_encounter")
STATUSES = ("done", "scheduled", "cancelled", "voided")

# A question, answer or group as the provider names it. Any field may be blank.
ConceptRef = namedtuple("ConceptRef", "external_id name data_type")
ConceptRef.__new__.__defaults__ = ("", "", "unknown")

# One answer to one question. `value` is already a python scalar; coded answers
# carry `answer_name` and appear once per selected option.
Observation = namedtuple("Observation", "question value group repeat_index position answer_name")
Observation.__new__.__defaults__ = (None, 0, 0, "")

NormalizedRecord = namedtuple(
    "NormalizedRecord",
    "kind external_id subject_external_id subject_type program encounter_type "
    "form_external_id form_name slum_name city_name household_number record_datetime "
    "earliest_scheduled max_scheduled cancel_datetime exit_datetime is_voided "
    "created_at last_modified_at observations",
)
NormalizedRecord.__new__.__defaults__ = (
    "", "", "", "", "", "", "", "", "", None, None, None, None, None, False, None, None, (),
)

# One form in the provider's catalog. `concepts` is [(ConceptRef, [answer ConceptRef, ...]), ...]
CatalogEntry = namedtuple(
    "CatalogEntry", "subject_type kind program encounter_type label form_external_id concepts"
)
CatalogEntry.__new__.__defaults__ = ("", "", "", "", ())

# Everything under one subject, as the explorer needs it.
SubjectTree = namedtuple("SubjectTree", "subject enrolments encounters")
SubjectTree.__new__.__defaults__ = ((), ())

# What the connector can read off a raw record without fetching its subject.
RecordFacts = namedtuple(
    "RecordFacts",
    "external_id subject_external_id subject_type program encounter_type form_name "
    "record_datetime last_modified slum_name household_number enrolment_external_id",
)
RecordFacts.__new__.__defaults__ = ("", "", "", "", "", None, None, "", "", "")


class Provider(object):
    """Base class; `key` names the provider in Record.provider and ConceptAlias."""

    key = ""

    def catalog(self):
        """[CatalogEntry] from the provider's own form metadata."""
        raise NotImplementedError

    def facts(self, kind, raw):
        """RecordFacts read straight off the raw record; must not call the API."""
        raise NotImplementedError

    def lists(self, kind):
        """False when the provider cannot list this kind by type (AVNI: enrolments)."""
        return True

    def iter_records(self, kind, subject_type, program="", encounter_type="", since=None):
        """Yield raw records of one kind modified since `since`, page by page."""
        raise NotImplementedError

    def get_subject(self, subject_external_id):
        """The raw subject record; the connector memoises this per run."""
        raise NotImplementedError

    def get_enrolment(self, enrolment_external_id):
        """The raw enrolment a program encounter hangs off (fetched once per run)."""
        raise NotImplementedError

    def get_subject_tree(self, subject_external_id):
        """SubjectTree(subject, [(enrolment, [program encounter, ...])], [encounter, ...])."""
        raise NotImplementedError

    def normalize(self, kind, raw, subject_raw=None):
        """-> NormalizedRecord."""
        raise NotImplementedError

    def visit_status(self, kind, raw):
        """One of STATUSES. Subjects and enrolments are only done or voided."""
        raise NotImplementedError

    def is_skipped_by_legacy(self, kind, raw):
        """True when today's legacy writers would ignore this record."""
        raise NotImplementedError

    def legacy_save(self, kind, raw, context):
        """Run the existing writers for this record. Returns True when something was written."""
        raise NotImplementedError

    def legacy_void(self, kind, raw, context):
        """Let the legacy tables forget a voided record. Returns the number of rows removed."""
        return 0

    def legacy_handles(self, kind, subject_type, encounter_type=""):
        """True when a legacy writer exists for this kind/type (used by the explorer)."""
        return False
