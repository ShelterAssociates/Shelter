"""Turn spreadsheet column headers into AVNI concept names, strictly.

Resolution order per header: id column, reserved top-level field, exact concept
name, exact question name (what the team sees in the app), normalised match,
a mapping the user chose in the preview. Anything else is unknown; close
matches are offered as suggestions but never applied on their own.
"""

import difflib
import re
from collections import Counter, namedtuple

Resolution = namedtuple("Resolution", "header kind concept_name question candidates message")

ID_HEADERS = {"uuid", "id", "avni uuid", "subject id", "encounter id", "enrolment id"}
VOIDED = "Voided"

# Top-level (non-observation) fields the API accepts, per form type.
RESERVED_BY_FORM_TYPE = {
    "IndividualProfile": {"First name", "Last name", "Registration date"},
    "ProgramEnrolment": {"Enrolment datetime", "Exit datetime"},
    "ProgramEncounter": {"Encounter date time", "Cancel date time"},
    "Encounter": {"Encounter date time", "Cancel date time"},
}

# Observation types a spreadsheet cell cannot express.
UNSUPPORTED_TYPES = {"Image", "Video", "Audio", "File", "Location", "Subject", "Encounter",
                     "GroupAffiliation", "QuestionGroup", "PhoneNumber"}

SUGGESTION_CUTOFF = 0.8
PUNCTUATION = re.compile(r"[?:.*_]+$")
SPACES = re.compile(r"\s+")


def normalize(text):
    text = SPACES.sub(" ", str(text or "")).strip().strip('"\'').casefold()
    return PUNCTUATION.sub("", text).strip()


def reserved_for(form):
    return {VOIDED} | RESERVED_BY_FORM_TYPE.get(form.form_type, set())


def resolve_headers(form, header_list, chosen=None):
    """One Resolution per non-blank header, in spreadsheet order."""
    questions = list(form.questions.filter(is_active=True))
    index = QuestionIndex(questions, reserved_for(form))
    chosen = chosen or {}
    resolutions = [index.resolve(header, chosen.get(header)) for header in header_list if str(header or "").strip()]
    return flag_duplicates(resolutions)


class QuestionIndex(object):
    def __init__(self, questions, reserved):
        self.reserved = {normalize(name): name for name in reserved}
        self.by_concept = {q.concept_name: q for q in questions}
        self.by_question = {q.question_name: q for q in questions}
        self.by_normalized = {}
        for question in questions:
            for name in (question.concept_name, question.question_name):
                self.by_normalized.setdefault(normalize(name), set()).add(question.concept_name)
        self.names = sorted(set(self.by_concept) | set(self.by_question))

    def resolve(self, header, chosen_concept=None):
        text = str(header).strip()
        key = normalize(text)
        if text.startswith("#"):
            return Resolution(header, "ignored", None, None, [], "Columns starting with # are ignored.")
        if key in ID_HEADERS:
            return Resolution(header, "id", None, None, [], "")
        if key in self.reserved:
            return Resolution(header, "reserved", self.reserved[key], None, [], "")
        if chosen_concept and chosen_concept in self.by_concept:
            return self.for_question(header, "chosen", self.by_concept[chosen_concept])
        if text in self.by_concept:
            return self.for_question(header, "exact_concept", self.by_concept[text])
        if text in self.by_question:
            return self.for_question(header, "exact_question", self.by_question[text])
        concepts = sorted(self.by_normalized.get(key, ()))
        if len(concepts) == 1:
            return self.for_question(header, "normalized", self.by_concept[concepts[0]])
        if len(concepts) > 1:
            return Resolution(header, "ambiguous", None, None, concepts, "Matches more than one question; pick one.")
        suggestions = self.suggestions(text)
        message = "Not a question of this form." + (" Did you mean: {}?".format(", ".join(suggestions)) if suggestions else "")
        return Resolution(header, "unknown", None, None, suggestions, message)

    def for_question(self, header, kind, question):
        if question.data_type in UNSUPPORTED_TYPES:
            return Resolution(header, "unsupported", question.concept_name, question, [],
                              "{} questions cannot be updated from a spreadsheet.".format(question.data_type))
        return Resolution(header, kind, question.concept_name, question, [], "")

    def suggestions(self, text):
        matches = difflib.get_close_matches(text, self.names, n=3, cutoff=SUGGESTION_CUTOFF)
        concepts = []
        for name in matches:
            question = self.by_concept.get(name) or self.by_question.get(name)
            if question.concept_name not in concepts:
                concepts.append(question.concept_name)
        return concepts


def flag_duplicates(resolutions):
    counts = Counter(r.concept_name for r in resolutions if r.concept_name and r.kind != "ignored")
    flagged = []
    for resolution in resolutions:
        if resolution.concept_name and counts[resolution.concept_name] > 1:
            flagged.append(resolution._replace(kind="duplicate", message="Two columns point at the same question."))
        else:
            flagged.append(resolution)
    return flagged


OK_KINDS = {"id", "reserved", "exact_concept", "exact_question", "normalized", "chosen", "ignored"}


def problems(resolutions):
    """Human-readable reasons the upload cannot run yet."""
    issues = []
    if not any(r.kind == "id" for r in resolutions):
        issues.append("A 'uuid' column is required.")
    for resolution in resolutions:
        if resolution.kind not in OK_KINDS:
            issues.append("'{}': {}".format(resolution.header, resolution.message or resolution.kind))
    if not any(r.kind in OK_KINDS - {"id", "ignored"} for r in resolutions):
        issues.append("No column to update: add at least one question or 'Voided' column.")
    return issues


def all_resolved(resolutions):
    return not problems(resolutions)
