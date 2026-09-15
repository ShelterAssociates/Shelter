"""Excel header resolution and cell coercion against cached form questions."""

from datetime import date, datetime

from django.test import TestCase

from avni.models import AvniForm, AvniFormQuestion
from avni_console.services import headers, values


def make_form(form_type="IndividualProfile"):
    form = AvniForm.objects.create(uuid="f-" + form_type, name="Form", form_type=form_type)
    specs = [
        ("e1", "Aadhaar number", "Aadhaar number", "Numeric", None, False, ""),
        ("e2", "Do you have a toilet at home?", "Do you have a toilet at home?", "Coded", ["Yes", "No"], False, ""),
        ("e3", "Use of toilet", "Use of toilet", "Coded", ["Men", "Women", "Children, girls"], True, ""),
        ("e4", "Name of the surveyor", "Surveyor (normal/coded)", "Text", None, False, ""),
        ("e5", "Date of Survey", "Date of Survey", "Date", None, False, ""),
        ("e6", "Family Photo", "Family Photo", "Image", None, False, ""),
        ("e7", "Total Number of Members", "Total Number of Members", "QuestionGroup", None, False, ""),
        ("e8", "Number of Male members", "Number of Male members", "Numeric", None, False, "e7"),
        ("e9", "Comment", "Comment if any ?", "Text", None, False, ""),
        ("e10", "Type of shop", "Type of shop", "Text", None, False, ""),
        ("e11", "Type of house*", "Type of house*", "Text", None, False, ""),
    ]
    for uuid, question, concept, data_type, answers, multi, parent in specs:
        AvniFormQuestion.objects.create(
            form=form, uuid=uuid, question_name=question, concept_name=concept, concept_uuid="c-" + uuid,
            data_type=data_type, answers=answers, is_multi_select=multi, parent_uuid=parent,
        )
    return form


class HeaderTests(TestCase):
    def setUp(self):
        self.form = make_form()

    def kinds(self, header_list, chosen=None):
        return {r.header: r.kind for r in headers.resolve_headers(self.form, header_list, chosen)}

    def test_exact_concept_and_question_names(self):
        result = {r.header: r for r in headers.resolve_headers(self.form, ["uuid", "Aadhaar number", "Name of the surveyor"])}
        self.assertEqual(result["uuid"].kind, "id")
        self.assertEqual(result["Aadhaar number"].kind, "exact_concept")
        self.assertEqual(result["Name of the surveyor"].kind, "exact_question")
        self.assertEqual(result["Name of the surveyor"].concept_name, "Surveyor (normal/coded)")

    def test_normalised_matches(self):
        self.assertEqual(self.kinds(["uuid", " do you have a toilet at home ", "COMMENT", "type of house"]),
                         {"uuid": "id", " do you have a toilet at home ": "normalized", "COMMENT": "normalized", "type of house": "normalized"})

    def test_unknown_with_suggestions(self):
        resolution = [r for r in headers.resolve_headers(self.form, ["uuid", "Aadhar numbr"]) if r.header == "Aadhar numbr"][0]
        self.assertEqual(resolution.kind, "unknown")
        self.assertEqual(resolution.candidates, ["Aadhaar number"])

    def test_totally_unknown_has_no_candidates(self):
        resolution = [r for r in headers.resolve_headers(self.form, ["uuid", "Favourite colour"]) if r.header == "Favourite colour"][0]
        self.assertEqual((resolution.kind, resolution.candidates), ("unknown", []))

    def test_reserved_headers_per_form_type(self):
        self.assertEqual(self.kinds(["ID", "voided", "Registration date", "First name"]),
                         {"ID": "id", "voided": "reserved", "Registration date": "reserved", "First name": "reserved"})
        encounter_form = make_form("Encounter")
        kinds = {r.header: r.kind for r in headers.resolve_headers(encounter_form, ["uuid", "Registration date", "Encounter date time"])}
        self.assertEqual(kinds["Registration date"], "unknown")
        self.assertEqual(kinds["Encounter date time"], "reserved")

    def test_missing_id_column_is_an_error(self):
        resolutions = headers.resolve_headers(self.form, ["Aadhaar number"])
        self.assertFalse(headers.all_resolved(resolutions))
        self.assertIn("uuid", headers.problems(resolutions)[0])

    def test_duplicate_targets_flagged(self):
        kinds = self.kinds(["uuid", "Comment", "Comment if any ?"])
        self.assertEqual((kinds["Comment"], kinds["Comment if any ?"]), ("duplicate", "duplicate"))

    def test_chosen_mapping_overrides_unknown(self):
        kinds = self.kinds(["uuid", "Aadhar numbr"], chosen={"Aadhar numbr": "Aadhaar number"})
        self.assertEqual(kinds["Aadhar numbr"], "chosen")

    def test_chosen_mapping_must_be_a_real_concept(self):
        kinds = self.kinds(["uuid", "Aadhar numbr"], chosen={"Aadhar numbr": "Nope"})
        self.assertEqual(kinds["Aadhar numbr"], "unknown")

    def test_unsupported_data_types_are_flagged(self):
        kinds = self.kinds(["uuid", "Family Photo", "Total Number of Members"])
        self.assertEqual(kinds["Family Photo"], "unsupported")
        self.assertEqual(kinds["Total Number of Members"], "unsupported")

    def test_group_child_resolves_with_parent(self):
        resolution = [r for r in headers.resolve_headers(self.form, ["uuid", "Number of Male members"]) if r.question][0]
        self.assertEqual(resolution.question.parent_uuid, "e7")
        self.assertTrue(headers.all_resolved(headers.resolve_headers(self.form, ["uuid", "Number of Male members"])))

    def test_blank_and_ignored_headers(self):
        kinds = self.kinds(["uuid", "", "  ", "#notes"])
        self.assertNotIn("", kinds)
        self.assertEqual(kinds["#notes"], "ignored")


class CoerceTests(TestCase):
    def setUp(self):
        self.form = make_form()
        self.by_concept = {q.concept_name: q for q in self.form.questions.all()}

    def coerce(self, concept, cell):
        return values.coerce(cell, self.by_concept[concept])

    def test_blank_means_no_change_and_clear_token(self):
        self.assertIs(self.coerce("Aadhaar number", None), values.NO_CHANGE)
        self.assertIs(self.coerce("Aadhaar number", "__clear__"), values.CLEAR)

    def test_numeric(self):
        self.assertEqual(self.coerce("Aadhaar number", "1234"), 1234)
        self.assertEqual(self.coerce("Aadhaar number", 12.0), 12)
        self.assertEqual(self.coerce("Aadhaar number", "12.5"), 12.5)
        with self.assertRaises(values.CellError):
            self.coerce("Aadhaar number", "twelve")

    def test_text_is_stringified(self):
        self.assertEqual(self.coerce("Comment if any ?", 42), "42")
        self.assertEqual(self.coerce("Comment if any ?", " hi "), "hi")

    def test_coded_single_case_insensitive(self):
        self.assertEqual(self.coerce("Do you have a toilet at home?", " yes "), "Yes")
        with self.assertRaises(values.CellError) as raised:
            self.coerce("Do you have a toilet at home?", "maybe")
        self.assertIn("Yes, No", str(raised.exception))

    def test_coded_multi_split_and_comma_inside_answer(self):
        self.assertEqual(self.coerce("Use of toilet", "men; WOMEN"), ["Men", "Women"])
        self.assertEqual(self.coerce("Use of toilet", "Men, Women"), ["Men", "Women"])
        self.assertEqual(self.coerce("Use of toilet", "Children, girls"), ["Children, girls"])
        self.assertEqual(self.coerce("Use of toilet", ["men"]), ["Men"])
        with self.assertRaises(values.CellError):
            self.coerce("Use of toilet", "Men; Dogs")

    def test_dates(self):
        self.assertEqual(self.coerce("Date of Survey", date(2026, 1, 5)), "2026-01-05")
        self.assertEqual(self.coerce("Date of Survey", datetime(2026, 1, 5, 10)), "2026-01-05")
        self.assertEqual(self.coerce("Date of Survey", "2026-01-05"), "2026-01-05")
        self.assertEqual(self.coerce("Date of Survey", "05/01/2026"), "2026-01-05", "day first, as the team writes dates")
        self.assertEqual(self.coerce("Date of Survey", "05-01-2026"), "2026-01-05")
        with self.assertRaises(values.CellError):
            self.coerce("Date of Survey", "someday")

    def test_voided_and_top_level_fields(self):
        self.assertIs(values.coerce_reserved("Voided", "yes"), True)
        self.assertIs(values.coerce_reserved("Voided", 0), False)
        with self.assertRaises(values.CellError):
            values.coerce_reserved("Voided", "maybe")
        self.assertEqual(values.coerce_reserved("Registration date", "05/01/2026"), "2026-01-05")
        self.assertEqual(values.coerce_reserved("Encounter date time", datetime(2026, 1, 5, 10, 30)), "2026-01-05T05:00:00.000Z")
        self.assertEqual(values.coerce_reserved("First name", 42), "42")

    def test_unsupported_type_raises(self):
        with self.assertRaises(values.CellError):
            self.coerce("Family Photo", "https://x")
