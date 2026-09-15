"""Refresh and query the cached AVNI form definitions (avni.models).

Source endpoints (AVNI's own web-app API, same auth-token as /api):
  web/operationalModules  -> subject types, programs, encounter types, form mappings
  forms/export?formUUID=  -> a form's groups, questions and their concepts
Rows are deactivated, never deleted, so older uploads keep resolving.
"""

import logging

from django.conf import settings
from django.utils import timezone

from avni.client import AvniError, client
from avni.models import FORM_TYPES, AvniForm, AvniFormMapping, AvniFormQuestion

logger = logging.getLogger(__name__)

SUPPORTED_FORM_TYPES = [key for key, label in FORM_TYPES]
LEVELS = ("registration", "enrolment", "program_encounter", "encounter")
LEVEL_FORM_TYPE = {
    "registration": "IndividualProfile",
    "enrolment": "ProgramEnrolment",
    "program_encounter": "ProgramEncounter",
    "encounter": "Encounter",
}


def refresh_form_cache(api=None):
    """Pull everything and upsert. Returns counts; raises AvniError only when the module list fails."""
    api = api or client()
    modules = api.get_json("web/operationalModules")
    names = Names(modules)
    now = timezone.now()
    counts = {"forms": 0, "mappings": 0, "questions": 0, "export_errors": 0, "deactivated_forms": 0}

    seen_forms, seen_mappings = set(), set()
    for mapping in modules.get("formMappings", []):
        if mapping.get("formType") not in SUPPORTED_FORM_TYPES or mapping.get("voided"):
            continue
        form = upsert_form(mapping, now)
        upsert_mapping(mapping, form, names)
        seen_forms.add(form.uuid)
        seen_mappings.add(mapping["uuid"])
    counts["forms"] = len(seen_forms)
    counts["mappings"] = len(seen_mappings)

    for form in AvniForm.objects.filter(uuid__in=seen_forms):
        try:
            definition = api.get_json("forms/export?formUUID=" + form.uuid)
        except AvniError as exc:
            counts["export_errors"] += 1
            logger.error("Form %s (%s) not exported: %s", form.name, form.uuid, exc)
            continue
        counts["questions"] += upsert_questions(form, definition, now)

    counts["deactivated_forms"] = AvniForm.objects.filter(is_active=True).exclude(uuid__in=seen_forms).update(is_active=False)
    AvniFormMapping.objects.filter(is_active=True).exclude(uuid__in=seen_mappings).update(is_active=False)
    return counts


class Names(object):
    """uuid -> name for subject types, programs and encounter types."""

    def __init__(self, modules):
        self.subject_types = {item["uuid"]: item["name"] for item in modules.get("subjectTypes", [])}
        self.programs = {item["uuid"]: item["name"] for item in modules.get("programs", [])}
        self.encounter_types = {item["uuid"]: item["name"] for item in modules.get("encounterTypes", [])}


def upsert_form(mapping, now):
    form, created = AvniForm.objects.get_or_create(
        uuid=mapping["formUUID"], defaults={"name": mapping.get("formName") or mapping["formUUID"], "form_type": mapping["formType"]}
    )
    form.name = mapping.get("formName") or form.name
    form.form_type = mapping["formType"]
    form.is_active = True
    form.save(update_fields=["name", "form_type", "is_active"])
    return form


def upsert_mapping(mapping, form, names):
    AvniFormMapping.objects.update_or_create(
        uuid=mapping["uuid"],
        defaults={
            "form": form,
            "subject_type": names.subject_types.get(mapping.get("subjectTypeUUID"), mapping.get("subjectTypeUUID") or ""),
            "program": names.programs.get(mapping.get("programUUID"), "") if mapping.get("programUUID") else "",
            "encounter_type": names.encounter_types.get(mapping.get("encounterTypeUUID"), "") if mapping.get("encounterTypeUUID") else "",
            "is_active": True,
        },
    )


def upsert_questions(form, definition, now):
    """Write the form's live questions; anything no longer present goes inactive."""
    seen = set()
    for group in definition.get("formElementGroups", []):
        if group.get("voided"):
            continue
        for element in group.get("formElements", []):
            if element.get("voided") or not element.get("concept"):
                continue
            seen.add(element["uuid"])
            AvniFormQuestion.objects.update_or_create(
                form=form, uuid=element["uuid"], defaults=question_fields(group, element)
            )
    form.questions.filter(is_active=True).exclude(uuid__in=seen).update(is_active=False)
    form.definition = definition
    form.fetched_on = now
    form.save(update_fields=["definition", "fetched_on"])
    return len(seen)


def question_fields(group, element):
    concept = element["concept"]
    answers = [answer["name"] for answer in concept.get("answers") or [] if not answer.get("voided")]
    return {
        "parent_uuid": element.get("parentFormElementUuid") or "",
        "group_name": group.get("name") or "",
        "question_name": element.get("name") or concept["name"],
        "concept_name": concept["name"],
        "concept_uuid": concept.get("uuid") or "",
        "data_type": concept.get("dataType") or "",
        "is_multi_select": element.get("type") == "MultiSelect",
        "answers": answers if concept.get("dataType") == "Coded" else None,
        "is_mandatory": bool(element.get("mandatory")),
        "display_order": float(element.get("displayOrder") or 0),
        "is_active": True,
    }


# -- lookups ------------------------------------------------------------------

def active_mappings():
    return AvniFormMapping.objects.filter(is_active=True, form__is_active=True).select_related("form")


def subject_types():
    return sorted(set(active_mappings().values_list("subject_type", flat=True)))


def levels_for(subject_type):
    """Every form a subject type can be updated through, grouped by level."""
    rows = list(active_mappings().filter(subject_type=subject_type))
    registration = [m.form for m in rows if m.form.form_type == "IndividualProfile"]
    return {
        "registration": registration[0] if registration else None,
        "enrolments": sorted((m.program, m.form) for m in rows if m.form.form_type == "ProgramEnrolment"),
        "program_encounters": sorted((m.program, m.encounter_type, m.form) for m in rows if m.form.form_type == "ProgramEncounter"),
        "encounters": sorted((m.encounter_type, m.form) for m in rows if m.form.form_type == "Encounter"),
    }


def form_for(subject_type, level, program=None, encounter_type=None):
    """The one form for (subject type, level, program, encounter type), or None."""
    if level not in LEVELS:
        raise ValueError("level must be one of {}".format(", ".join(LEVELS)))
    rows = active_mappings().filter(subject_type=subject_type, form__form_type=LEVEL_FORM_TYPE[level])
    if level in ("enrolment", "program_encounter"):
        rows = rows.filter(program=program or "")
    if level in ("program_encounter", "encounter"):
        rows = rows.filter(encounter_type=encounter_type or "")
    mapping = rows.first()
    return mapping.form if mapping else None


def questions_for(form):
    return list(form.questions.filter(is_active=True).order_by("display_order", "id"))


def cache_is_stale():
    """True when the cache is empty or older than AVNI_FORM_CACHE_MAX_AGE_HOURS."""
    newest = AvniForm.objects.filter(is_active=True).order_by("-fetched_on").values_list("fetched_on", flat=True).first()
    if newest is None:
        return True
    max_age = getattr(settings, "AVNI_FORM_CACHE_MAX_AGE_HOURS", 48)
    return newest < timezone.now() - timezone.timedelta(hours=max_age)
