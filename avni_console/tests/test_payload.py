"""Write bodies: PATCH for subjects/encounters, PUT for program encounters/enrolments."""

from django.test import TestCase

from avni_console.services import payload, values
from avni_console.tests.test_headers_values import make_form


class PatchBodyTests(TestCase):
    def setUp(self):
        self.form = make_form("IndividualProfile")
        self.questions = {q.concept_name: q for q in self.form.questions.all()}
        self.fetched = {
            "ID": "sub-1", "Voided": False, "Registration date": "2018-03-20",
            "location": {"Slum": "S", "City": "C"},
            "observations": {
                "First name": "42", "Aadhaar number": 1111, "Do you have a toilet at home?": "No",
                "Total Number of Members": {"c-e8": 2},
            },
            "audit": {"Last modified at": "2026-01-01T00:00:00.000Z"},
        }

    def test_subject_patch_sends_only_changes_plus_subject_type(self):
        changes = {"Aadhaar number": 2222, "Do you have a toilet at home?": "Yes"}
        write = payload.build_write(self.form, "Household", "sub-1", self.fetched, changes, {})
        self.assertEqual((write.method, write.path), ("PATCH", "api/subject/sub-1"))
        self.assertEqual(write.body, {"Subject type": "Household",
                                      "observations": {"Aadhaar number": 2222, "Do you have a toilet at home?": "Yes"}})

    def test_clear_becomes_null_in_patch(self):
        write = payload.build_write(self.form, "Household", "sub-1", self.fetched, {"Aadhaar number": values.CLEAR}, {})
        self.assertEqual(write.body["observations"], {"Aadhaar number": None})

    def test_voided_and_top_level_fields(self):
        write = payload.build_write(self.form, "Household", "sub-1", self.fetched, {}, {"Voided": True, "Registration date": "2020-01-01"})
        self.assertEqual(write.body, {"Subject type": "Household", "Voided": True, "Registration date": "2020-01-01"})

    def test_group_child_sends_whole_group_by_name(self):
        changes = {"Number of Male members": 5}
        write = payload.build_write(self.form, "Household", "sub-1", self.fetched, changes, {})
        self.assertEqual(write.body["observations"], {"Total Number of Members": {"Number of Male members": 5}})

    def test_group_child_keeps_siblings_when_group_has_more_children(self):
        self.fetched["observations"]["Total Number of Members"] = {"c-e8": 2, "c-other": 7}
        write = payload.build_write(self.form, "Household", "sub-1", self.fetched, {"Number of Male members": 5}, {})
        group = write.body["observations"]["Total Number of Members"]
        self.assertEqual(group["Number of Male members"], 5)
        self.assertEqual(group["c-other"], 7, "unknown sibling uuids are kept as-is rather than dropped")

    def test_encounter_patch_uses_encounter_type(self):
        form = make_form("Encounter")
        fetched = {"ID": "enc-1", "Encounter type": "Water", "Subject ID": "sub-1", "observations": {"Comment if any ?": "old"}}
        write = payload.build_write(form, "Household", "enc-1", fetched, {"Comment if any ?": "new"}, {})
        self.assertEqual((write.method, write.path), ("PATCH", "api/encounter/enc-1"))
        self.assertEqual(write.body, {"Encounter type": "Water", "observations": {"Comment if any ?": "new"}})


class PutBodyTests(TestCase):
    def setUp(self):
        self.form = make_form("ProgramEncounter")
        self.fetched = {
            "ID": "penc-1", "Voided": False, "Encounter type": "Daily Reporting", "Program": "Sanitation program",
            "Subject ID": "sub-1", "Enrolment ID": "enr-1", "Encounter date time": "2026-01-01T00:00:00.000Z",
            "observations": {"Comment if any ?": "old", "Aadhaar number": 1, "Total Number of Members": {"c-e8": 2}},
            "cancelObservations": {}, "audit": {"Last modified at": "x"},
        }

    def test_put_sends_full_body_with_edits(self):
        write = payload.build_write(self.form, "Household", "penc-1", self.fetched, {"Comment if any ?": "new"}, {"Voided": True})
        self.assertEqual((write.method, write.path), ("PUT", "api/programEncounter/penc-1"))
        self.assertEqual(write.body["Encounter type"], "Daily Reporting")
        self.assertEqual(write.body["Program"], "Sanitation program")
        self.assertEqual(write.body["observations"]["Comment if any ?"], "new")
        self.assertEqual(write.body["observations"]["Aadhaar number"], 1, "untouched observations are re-sent")
        self.assertTrue(write.body["Voided"])
        self.assertNotIn("audit", write.body)
        self.assertNotIn("ID", write.body)

    def test_put_clear_removes_key(self):
        write = payload.build_write(self.form, "Household", "penc-1", self.fetched, {"Comment if any ?": values.CLEAR}, {})
        self.assertNotIn("Comment if any ?", write.body["observations"])

    def test_put_remaps_every_group_uuid_to_names(self):
        write = payload.build_write(self.form, "Household", "penc-1", self.fetched, {}, {"Voided": True})
        self.assertEqual(write.body["observations"]["Total Number of Members"], {"Number of Male members": 2})

    def test_enrolment_put_path(self):
        form = make_form("ProgramEnrolment")
        fetched = {"ID": "enr-1", "Program": "Sanitation program", "Subject ID": "sub-1", "observations": {}}
        write = payload.build_write(form, "Household", "enr-1", fetched, {"Comment if any ?": "x"}, {})
        self.assertEqual((write.method, write.path), ("PUT", "api/programEnrolment/enr-1"))


class DiffTests(TestCase):
    def setUp(self):
        self.form = make_form()

    def test_diff_reads_old_values_including_group_children(self):
        fetched = {"observations": {"Aadhaar number": 1, "Total Number of Members": {"c-e8": 2}}, "Voided": False}
        old = payload.current_values(self.form, fetched, ["Aadhaar number", "Number of Male members", "Comment if any ?"], ["Voided"])
        self.assertEqual(old, {"Aadhaar number": 1, "Number of Male members": 2, "Comment if any ?": None, "Voided": False})

    def test_unchanged_values_are_dropped(self):
        fetched = {"observations": {"Aadhaar number": 1, "Use of toilet": ["Men", "Women"]}}
        changes = payload.real_changes(self.form, fetched, {"Aadhaar number": 1, "Use of toilet": ["Women", "Men"], "Comment if any ?": "new"})
        self.assertEqual(changes, {"Comment if any ?": "new"})

    def test_clear_of_missing_value_is_not_a_change(self):
        fetched = {"observations": {}}
        self.assertEqual(payload.real_changes(self.form, fetched, {"Aadhaar number": values.CLEAR}), {})
