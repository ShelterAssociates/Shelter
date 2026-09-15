"""Form metadata cache: refresh from operationalModules + forms/export, lookups."""

from django.test import TestCase

from avni import metadata
from avni.models import AvniForm, AvniFormMapping, AvniFormQuestion
from avni.tests.support import FakeApi

ST_HOUSEHOLD, ST_TOILET = "st-hh", "st-toilet"
PROGRAM = "prog-san"
ENC_DAILY, ENC_WATER = "enc-daily", "enc-water"


def modules(extra_mappings=()):
    mappings = [
        {"uuid": "m1", "formUUID": "f-reg", "formType": "IndividualProfile", "subjectTypeUUID": ST_HOUSEHOLD, "formName": "Household form"},
        {"uuid": "m2", "formUUID": "f-enrol", "formType": "ProgramEnrolment", "subjectTypeUUID": ST_HOUSEHOLD, "programUUID": PROGRAM, "formName": "Sanitation enrolment"},
        {"uuid": "m3", "formUUID": "f-daily", "formType": "ProgramEncounter", "subjectTypeUUID": ST_HOUSEHOLD, "programUUID": PROGRAM, "encounterTypeUUID": ENC_DAILY, "formName": "Daily Reporting form"},
        {"uuid": "m4", "formUUID": "f-water", "formType": "Encounter", "subjectTypeUUID": ST_HOUSEHOLD, "encounterTypeUUID": ENC_WATER, "formName": "Water form"},
        {"uuid": "m5", "formUUID": "f-cancel", "formType": "ProgramEncounterCancellation", "subjectTypeUUID": ST_HOUSEHOLD, "programUUID": PROGRAM, "encounterTypeUUID": ENC_DAILY, "formName": "Daily cancel"},
        {"uuid": "m6", "formUUID": "f-toilet", "formType": "IndividualProfile", "subjectTypeUUID": ST_TOILET, "formName": "Toilet form"},
    ] + list(extra_mappings)
    return {
        "formMappings": mappings,
        "subjectTypes": [{"uuid": ST_HOUSEHOLD, "name": "Household"}, {"uuid": ST_TOILET, "name": "Toilet"}],
        "programs": [{"uuid": PROGRAM, "name": "Sanitation program"}],
        "encounterTypes": [{"uuid": ENC_DAILY, "name": "Daily Reporting"}, {"uuid": ENC_WATER, "name": "Water"}],
        "forms": [],
    }


def element(name, data_type="Text", answers=None, voided=False, element_type="SingleSelect", mandatory=False, uuid=None, parent=None):
    concept = {"name": name, "uuid": "c-" + (uuid or name), "dataType": data_type}
    if answers is not None:
        concept["answers"] = [{"name": answer, "uuid": "a-" + answer, "order": index} for index, answer in enumerate(answers)]
    built = {"uuid": uuid or "e-" + name, "name": name, "concept": concept, "type": element_type,
             "mandatory": mandatory, "voided": voided, "displayOrder": 1.0}
    if parent:
        built["parentFormElementUuid"] = parent
    return built


def export(uuid, name, form_type, groups):
    return {"uuid": uuid, "name": name, "formType": form_type,
            "formElementGroups": [{"uuid": "g-" + g, "name": g, "voided": False, "displayOrder": i, "formElements": els}
                                  for i, (g, els) in enumerate(groups)]}


def routes(mods=None):
    return {
        "web/operationalModules": mods or modules(),
        "forms/export?formUUID=f-reg": export("f-reg", "Household form", "IndividualProfile", [
            ("Identity", [element("First name"), element("Aadhaar number", "Numeric", mandatory=True),
                          element("Old question", voided=True)]),
            ("Toilet", [element("Do you have a toilet at home?", "Coded", ["Yes", "No"]),
                        element("Use of toilet", "Coded", ["Men", "Women"], element_type="MultiSelect")]),
            ("Members", [element("Total Number of Members", "QuestionGroup"),
                         element("Number of Male members", "Numeric", parent="e-Total Number of Members"),
                         element("Number of Female members", "Numeric", parent="e-Total Number of Members")]),
        ]),
        "forms/export?formUUID=f-enrol": export("f-enrol", "Sanitation enrolment", "ProgramEnrolment", [("Main", [element("Enrol reason")])]),
        "forms/export?formUUID=f-daily": export("f-daily", "Daily Reporting form", "ProgramEncounter", [("Main", [element("Date of agreement", "Date")])]),
        "forms/export?formUUID=f-water": export("f-water", "Water form", "Encounter", [("Main", [element("Type of water connection ?", "Coded", ["Own", "Shared"])])]),
        "forms/export?formUUID=f-toilet": export("f-toilet", "Toilet form", "IndividualProfile", [("Main", [element("ctb name")])]),
    }


class RefreshTests(TestCase):
    def test_refresh_creates_forms_mappings_and_questions(self):
        counts = metadata.refresh_form_cache(api=FakeApi(routes()))
        self.assertEqual(counts["forms"], 5, "cancellation forms are not offered")
        self.assertEqual(counts["mappings"], 5)
        self.assertEqual(AvniForm.objects.filter(is_active=True).count(), 5)
        registration = AvniForm.objects.get(uuid="f-reg")
        names = list(registration.questions.filter(is_active=True).values_list("question_name", flat=True))
        self.assertEqual(names[:4], ["First name", "Aadhaar number", "Do you have a toilet at home?", "Use of toilet"])
        male = registration.questions.get(question_name="Number of Male members")
        self.assertEqual(male.parent_uuid, "e-Total Number of Members")
        self.assertEqual(registration.questions.get(question_name="Total Number of Members").parent_uuid, "")
        toilet = registration.questions.get(question_name="Use of toilet")
        self.assertEqual((toilet.data_type, toilet.is_multi_select, toilet.answers), ("Coded", True, ["Men", "Women"]))
        self.assertEqual(registration.questions.get(question_name="Aadhaar number").is_mandatory, True)
        self.assertFalse(registration.questions.filter(question_name="Old question").exists(), "voided elements are never stored")
        mapping = AvniFormMapping.objects.get(form__uuid="f-daily")
        self.assertEqual((mapping.subject_type, mapping.program, mapping.encounter_type), ("Household", "Sanitation program", "Daily Reporting"))

    def test_refresh_is_idempotent_and_deactivates_removed(self):
        metadata.refresh_form_cache(api=FakeApi(routes()))
        mods = modules()
        mods["formMappings"] = [m for m in mods["formMappings"] if m["formUUID"] != "f-water"]
        second = routes(mods)
        second["forms/export?formUUID=f-reg"]["formElementGroups"][0]["formElements"].pop(0)  # First name removed
        counts = metadata.refresh_form_cache(api=FakeApi(second))
        self.assertEqual(AvniForm.objects.count(), 5, "rows are kept, never deleted")
        self.assertFalse(AvniForm.objects.get(uuid="f-water").is_active)
        self.assertFalse(AvniFormMapping.objects.get(form__uuid="f-water").is_active)
        self.assertFalse(AvniFormQuestion.objects.get(form__uuid="f-reg", question_name="First name").is_active)
        self.assertEqual(counts["deactivated_forms"], 1)

    def test_renamed_question_updates_in_place(self):
        metadata.refresh_form_cache(api=FakeApi(routes()))
        second = routes()
        second["forms/export?formUUID=f-reg"]["formElementGroups"][0]["formElements"][0]["name"] = "Household number"
        metadata.refresh_form_cache(api=FakeApi(second))
        question = AvniFormQuestion.objects.get(form__uuid="f-reg", uuid="e-First name")
        self.assertEqual((question.question_name, question.concept_name), ("Household number", "First name"))

    def test_form_export_failure_keeps_old_questions_and_counts_error(self):
        metadata.refresh_form_cache(api=FakeApi(routes()))
        broken = routes()
        del broken["forms/export?formUUID=f-reg"]
        counts = metadata.refresh_form_cache(api=FakeApi(broken))
        self.assertEqual(counts["export_errors"], 1)
        self.assertEqual(AvniForm.objects.get(uuid="f-reg").questions.filter(is_active=True).count(), 7)
        self.assertTrue(AvniForm.objects.get(uuid="f-reg").is_active)

    def test_modules_failure_raises(self):
        from avni.client import AvniError

        with self.assertRaises(AvniError):
            metadata.refresh_form_cache(api=FakeApi({}))


class LookupTests(TestCase):
    def setUp(self):
        metadata.refresh_form_cache(api=FakeApi(routes()))

    def test_subject_types(self):
        self.assertEqual(metadata.subject_types(), ["Household", "Toilet"])

    def test_levels_for_household(self):
        levels = metadata.levels_for("Household")
        self.assertEqual(levels["registration"].uuid, "f-reg")
        self.assertEqual([(p, f.uuid) for p, f in levels["enrolments"]], [("Sanitation program", "f-enrol")])
        self.assertEqual([(p, e, f.uuid) for p, e, f in levels["program_encounters"]], [("Sanitation program", "Daily Reporting", "f-daily")])
        self.assertEqual([(e, f.uuid) for e, f in levels["encounters"]], [("Water", "f-water")])

    def test_levels_for_toilet_has_only_registration(self):
        levels = metadata.levels_for("Toilet")
        self.assertEqual(levels["registration"].uuid, "f-toilet")
        self.assertEqual((levels["enrolments"], levels["program_encounters"], levels["encounters"]), ([], [], []))

    def test_form_for(self):
        self.assertEqual(metadata.form_for("Household", "registration").uuid, "f-reg")
        self.assertEqual(metadata.form_for("Household", "enrolment", program="Sanitation program").uuid, "f-enrol")
        self.assertEqual(metadata.form_for("Household", "program_encounter", program="Sanitation program", encounter_type="Daily Reporting").uuid, "f-daily")
        self.assertEqual(metadata.form_for("Household", "encounter", encounter_type="Water").uuid, "f-water")
        self.assertIsNone(metadata.form_for("Household", "encounter", encounter_type="Nope"))
        self.assertIsNone(metadata.form_for("Ghost", "registration"))
        with self.assertRaises(ValueError):
            metadata.form_for("Household", "weird")

    def test_questions_for_skips_inactive(self):
        form = AvniForm.objects.get(uuid="f-reg")
        self.assertEqual([q.concept_name for q in metadata.questions_for(form)][:4],
                         ["First name", "Aadhaar number", "Do you have a toilet at home?", "Use of toilet"])

    def test_cache_is_stale_when_never_refreshed_or_old(self):
        self.assertFalse(metadata.cache_is_stale())
        AvniForm.objects.all().delete()
        self.assertTrue(metadata.cache_is_stale())
