"""A provider with no network behind it, for the core tests.

A raw record here is just {"normalized": NormalizedRecord, "status": ...}; the
real shape walking belongs to a real provider.
"""

from survey import contracts


class FakeProvider(contracts.Provider):
    key = "fake"

    def __init__(self, catalog_entries=(), subjects=None, listings=None, trees=None):
        self.catalog_entries = list(catalog_entries)
        self.subjects = dict(subjects or {})
        self.listings = dict(listings or {})
        self.windows = {}
        self.trees = dict(trees or {})
        self.enrolments = {}
        self.enrolment_calls = []
        self.unlistable = set()
        self.subject_calls = []
        self.legacy_calls = []
        self.normalize_calls = []
        self.legacy_result = True
        self.legacy_error = None

    def catalog(self):
        return list(self.catalog_entries)

    def facts(self, kind, raw):
        record = raw["normalized"]
        return contracts.RecordFacts(
            external_id=record.external_id,
            subject_external_id=record.subject_external_id,
            subject_type=record.subject_type,
            program=record.program,
            encounter_type=record.encounter_type,
            form_name=record.form_name,
            record_datetime=record.record_datetime,
            last_modified=record.last_modified_at,
            slum_name=record.slum_name if kind == "subject" else "",
            household_number=record.household_number if kind == "subject" else "",
            enrolment_external_id=raw.get("enrolment_id", ""),
        )

    def iter_records(self, kind, subject_type, program="", encounter_type="", since=None):
        key = (kind, subject_type, program or "", encounter_type or "")
        self.windows[key] = since
        for record in self.listings.get(key, []):
            yield record

    def lists(self, kind):
        return kind not in self.unlistable

    def get_enrolment(self, enrolment_external_id):
        self.enrolment_calls.append(enrolment_external_id)
        if enrolment_external_id not in self.enrolments:
            raise LookupError("no enrolment {}".format(enrolment_external_id))
        return self.enrolments[enrolment_external_id]

    def get_subject(self, subject_external_id):
        self.subject_calls.append(subject_external_id)
        if subject_external_id not in self.subjects:
            raise LookupError("no subject {}".format(subject_external_id))
        return self.subjects[subject_external_id]

    def get_subject_tree(self, subject_external_id):
        if subject_external_id not in self.trees:
            raise LookupError("no subject {}".format(subject_external_id))
        return self.trees[subject_external_id]

    def normalize(self, kind, raw, subject_raw=None):
        self.normalize_calls.append(raw["normalized"].external_id)
        return raw["normalized"]

    def visit_status(self, kind, raw):
        return raw.get("status", "done")

    def is_skipped_by_legacy(self, kind, raw):
        return bool(raw.get("legacy_skip"))

    def legacy_save(self, kind, raw, context):
        self.legacy_calls.append((kind, raw["normalized"].external_id))
        if self.legacy_error is not None:
            raise self.legacy_error
        return self.legacy_result

    def legacy_handles(self, kind, subject_type, encounter_type=""):
        return subject_type == "Household" and kind != "enrolment"


def raw(normalized, status="done", legacy_skip=False):
    return {"normalized": normalized, "status": status, "legacy_skip": legacy_skip}


def tree(subject, enrolments=(), encounters=()):
    return contracts.SubjectTree(subject=subject, enrolments=list(enrolments), encounters=list(encounters))
