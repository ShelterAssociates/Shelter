"""The generic loop: skip/store/legacy semantics, switches, whole subjects."""

from django.test import TestCase

from graphs.models import HouseholdData
from notification.models import JobRun, JobStep
from notification.services import reporting
from survey import connector, contracts, window
from survey.models import Record, SyncSwitch
from survey.store import SyncContext
from survey.tests.fakes import FakeProvider, raw, tree
from survey.tests.support import make_city, make_slum, normalized, observation


class ConnectorTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.provider = FakeProvider()
        connector.use_provider(self.provider)
        self.addCleanup(connector.reset_provider)
        self.context = SyncContext(self.provider)

    def household(self, number="42"):
        return HouseholdData.objects.create(
            household_number=number, slum=self.slum, city=self.city,
            submission_date="2020-01-01T00:00:00Z", rhs_data={},
        )

    def encounter(self, external_id="enc-1", subject="sub-1", **overrides):
        overrides.setdefault("encounter_type", "Sanitation")
        return normalized(kind="encounter", external_id=external_id, subject_external_id=subject,
                          household_number="", **overrides)

    def with_subject(self, uuid="sub-1"):
        self.provider.subjects[uuid] = {"ID": uuid}

    def switch(self, subject_type="Household", kind="encounter", encounter_type="Water", program="", enabled=True):
        return SyncSwitch.objects.create(
            provider="fake", subject_type=subject_type, kind=kind, program=program,
            encounter_type=encounter_type, is_enabled=enabled,
        )


class RecordSemanticsTests(ConnectorTestCase):
    def test_a_done_record_is_stored_and_handed_to_legacy(self):
        saved = connector.sync_record("subject", raw(normalized()), self.context)
        self.assertTrue(saved)
        self.assertEqual(Record.objects.count(), 1)
        self.assertEqual(self.provider.legacy_calls, [("subject", "sub-1")])
        self.assertEqual(self.context.counts["created"], 1)
        self.assertEqual(self.context.counts["legacy_saved"], 1)

    def test_a_scheduled_visit_is_counted_and_never_stored(self):
        saved = connector.sync_record("encounter", raw(self.encounter(), status="scheduled"), self.context)
        self.assertFalse(saved)
        self.assertEqual(Record.objects.count(), 0)
        self.assertEqual(self.context.counts["scheduled_only"], 1)
        self.assertEqual(self.provider.legacy_calls, [])
        self.assertEqual(self.provider.subject_calls, [], "a scheduled visit costs no subject fetch")

    def test_a_voided_record_is_skipped_by_legacy_but_kept_in_the_store(self):
        saved = connector.sync_record(
            "subject", raw(normalized(is_voided=True), status="voided"), self.context
        )
        self.assertFalse(saved)
        self.assertTrue(Record.objects.get().is_voided)
        self.assertEqual(self.provider.legacy_calls, [])
        self.assertEqual(self.context.counts["voided"], 1)

    def test_an_empty_record_is_skipped_by_legacy_but_kept(self):
        self.with_subject()
        connector.sync_record("encounter", raw(self.encounter(), legacy_skip=True), self.context)
        self.assertEqual(Record.objects.count(), 1)
        self.assertEqual(self.provider.legacy_calls, [])

    def test_a_cancelled_visit_is_stored_without_answers(self):
        self.with_subject()
        cancelled = self.encounter(record_datetime=None, cancel_datetime="2026-09-02T10:00:00.000Z")
        connector.sync_record("encounter", raw(cancelled, status="cancelled", legacy_skip=True), self.context)
        row = Record.objects.get()
        self.assertIsNotNone(row.cancel_datetime)
        self.assertEqual(row.answers.count(), 0)
        self.assertFalse(row.is_filled)

    def test_an_unchanged_record_costs_no_subject_fetch(self):
        self.with_subject()
        connector.sync_record("encounter", raw(self.encounter()), self.context)
        later = SyncContext(self.provider)
        self.provider.subject_calls = []
        self.assertFalse(connector.sync_record("encounter", raw(self.encounter()), later))
        self.assertEqual(later.counts["unchanged"], 1)
        self.assertEqual(self.provider.subject_calls, [])
        self.assertEqual(self.provider.legacy_calls, [("encounter", "enc-1")], "only the first pass reached legacy")

    def test_an_edited_record_is_processed_again(self):
        self.with_subject()
        connector.sync_record("encounter", raw(self.encounter()), self.context)
        edited = self.encounter(last_modified_at="2026-09-05T06:00:00.000Z")
        self.assertTrue(connector.sync_record("encounter", raw(edited), SyncContext(self.provider)))
        self.assertEqual(Record.objects.count(), 1)

    def test_a_voided_record_is_not_rewritten_every_run(self):
        voided = raw(normalized(is_voided=True), status="voided")
        connector.sync_record("subject", voided, self.context)
        later = SyncContext(self.provider)
        self.provider.normalize_calls = []
        connector.sync_record("subject", voided, later)
        self.assertEqual(self.provider.normalize_calls, [])

    def test_a_subject_that_cannot_be_fetched_is_a_failure(self):
        saved = connector.sync_record("encounter", raw(self.encounter(subject="missing")), self.context)
        self.assertFalse(saved)
        self.assertEqual(self.context.counts["failed"], 1)
        self.assertEqual(Record.objects.count(), 0)

    def test_the_subject_is_fetched_once_for_two_of_its_encounters(self):
        self.with_subject()
        connector.sync_record("encounter", raw(self.encounter("enc-1")), self.context)
        connector.sync_record("encounter", raw(self.encounter("enc-2")), self.context)
        self.assertEqual(self.provider.subject_calls, ["sub-1"])

    def test_legacy_declining_to_save_is_not_a_failure(self):
        self.provider.legacy_result = False
        self.assertFalse(connector.sync_record("subject", raw(normalized()), self.context))
        self.assertEqual(Record.objects.count(), 1)
        self.assertEqual(self.context.counts["failed"], 0)

    def test_the_household_is_linked_after_legacy_creates_it(self):
        def create_household(kind, raw_record, context):
            self.household()
            return True

        self.provider.legacy_save = create_household
        connector.sync_record("subject", raw(normalized()), self.context)
        self.assertEqual(Record.objects.get().household, HouseholdData.objects.get())
        self.assertEqual(self.context.counts["unlinked"], 0)

    def test_a_duplicate_household_number_fails_but_legacy_still_runs(self):
        connector.sync_record("subject", raw(normalized(external_id="sub-1")), self.context)
        connector.sync_record("subject", raw(normalized(external_id="sub-2")), self.context)
        self.assertEqual(self.context.counts["duplicate_household"], 1)
        self.assertEqual(len(self.provider.legacy_calls), 2)


class ReportingTests(ConnectorTestCase):
    def run_with_recorder(self, kind, record):
        recorder = reporting.start("test_job", trigger="manual")
        with recorder.step("step") as step:
            connector.sync_record(kind, record, self.context)
        recorder.finish()
        return step

    def test_a_saved_record_counts_as_ok(self):
        step = self.run_with_recorder("subject", raw(normalized()))
        self.assertEqual((step.ok, step.failed, step.skipped), (1, 0, 0))

    def test_a_scheduled_visit_counts_as_skipped(self):
        step = self.run_with_recorder("encounter", raw(self.encounter(), status="scheduled"))
        self.assertEqual((step.ok, step.failed, step.skipped), (0, 0, 1))

    def test_a_voided_subject_counts_as_skipped(self):
        step = self.run_with_recorder("subject", raw(normalized(is_voided=True), status="voided"))
        self.assertEqual((step.ok, step.failed, step.skipped), (0, 0, 1))

    def test_an_unfetchable_subject_counts_as_failed(self):
        step = self.run_with_recorder("encounter", raw(self.encounter(subject="missing")))
        self.assertEqual((step.ok, step.failed, step.skipped), (0, 1, 0))

    def test_the_run_is_attributed_to_the_slum(self):
        self.run_with_recorder("subject", raw(normalized()))
        self.assertEqual(JobStep.objects.get().city_stats.count(), 1)
        self.assertEqual(JobRun.objects.count(), 1)


class SyncKindTests(ConnectorTestCase):
    def test_every_listed_record_is_processed(self):
        self.provider.listings[("subject", "Household", "", "")] = [
            raw(normalized(external_id="sub-1", household_number="1")),
            raw(normalized(external_id="sub-2", household_number="2")),
        ]
        saved = connector.sync_kind("subject", "Household", context=self.context)
        self.assertEqual(saved, 2)
        self.assertEqual(Record.objects.count(), 2)

    def test_an_empty_listing_saves_nothing(self):
        self.assertEqual(connector.sync_kind("encounter", "Household", encounter_type="Water",
                                             context=self.context), 0)

    def test_a_kind_never_synced_is_listed_from_the_first_sync_start(self):
        Record.objects.create(provider="fake", kind="encounter", external_id="s1", subject_type="Household", encounter_type="Sanitation",
                              last_modified_at="2026-06-01T09:00:00Z")
        connector.sync_kind("encounter", "Household", encounter_type="Water", context=self.context)
        connector.sync_kind("encounter", "Household", encounter_type="Sanitation", context=self.context)
        self.assertEqual(self.provider.windows[("encounter", "Household", "", "Water")], window.FIRST_SYNC_START)
        self.assertEqual(self.provider.windows[("encounter", "Household", "", "Sanitation")], "2026-05-31T00:00:00.000Z")


class StepCountTests(ConnectorTestCase):
    def sync_in_step(self, *calls):
        recorder = reporting.start("test_job", trigger="manual")
        with recorder.step("step") as step:
            for kind, subject_type, kwargs in calls:
                connector.sync_kind(kind, subject_type, context=self.context, **kwargs)
        recorder.finish()
        return step.model.extras

    def test_a_listing_step_notes_created_and_updated_separately(self):
        self.provider.listings[("subject", "Household", "", "")] = [
            raw(normalized(external_id="sub-1", household_number="1")),
            raw(normalized(external_id="sub-2", household_number="2")),
        ]
        first = self.sync_in_step(("subject", "Household", {}))
        self.assertEqual((first["created"], first["updated"]), ("2", "0"))
        self.provider.listings[("subject", "Household", "", "")][0] = raw(
            normalized(external_id="sub-1", household_number="1", last_modified_at="2026-09-02T06:47:34.548Z")
        )
        second = self.sync_in_step(("subject", "Household", {}))
        self.assertEqual((second["created"], second["updated"], second["unchanged"]), ("0", "1", "1"))

    def test_a_shared_context_notes_each_step_on_its_own(self):
        self.with_subject()
        self.provider.listings[("encounter", "Household", "", "Water")] = [raw(self.encounter("w1", encounter_type="Water"))]
        self.provider.listings[("encounter", "Household", "", "Waste")] = [raw(self.encounter("x1", encounter_type="Waste"))]
        recorder = reporting.start("test_job", trigger="manual")
        with recorder.step("encounters:Water") as water:
            connector.sync_kind("encounter", "Household", encounter_type="Water", context=self.context)
        with recorder.step("encounters:Waste") as waste:
            connector.sync_kind("encounter", "Household", encounter_type="Waste", context=self.context)
        recorder.finish()
        self.assertEqual(water.model.extras["created"], "1")
        self.assertEqual(waste.model.extras["created"], "1", "not the running total of the shared context")

    def test_sync_kinds_notes_the_total_over_its_kinds(self):
        self.with_subject()
        self.switch(encounter_type="Water")
        self.switch(encounter_type="Waste")
        self.provider.listings[("encounter", "Household", "", "Water")] = [raw(self.encounter("w1", encounter_type="Water"))]
        self.provider.listings[("encounter", "Household", "", "Waste")] = [raw(self.encounter("x1", encounter_type="Waste"))]
        recorder = reporting.start("test_job", trigger="manual")
        with recorder.step("household_encounters") as step:
            connector.sync_kinds(("Household",), context=self.context)
        recorder.finish()
        self.assertEqual((step.model.extras["created"], step.model.extras["kinds"]), ("2", "2"))


class SyncKindsTests(ConnectorTestCase):
    def test_only_enabled_kinds_run(self):
        self.switch(encounter_type="Water")
        self.switch(encounter_type="Waste", enabled=False)
        self.provider.listings[("encounter", "Household", "", "Water")] = [raw(self.encounter())]
        self.with_subject()
        results = connector.sync_kinds(["Household"], context=self.context)
        self.assertEqual(list(results), ["encounters:Water"])

    def test_the_steps_with_their_own_nightly_job_are_excluded(self):
        self.switch(kind="program_encounter", encounter_type="Daily Reporting", program="Sanitation")
        self.switch(kind="program_encounter", encounter_type="Family factsheet", program="Sanitation")
        self.switch(kind="program_encounter", encounter_type="Survey", program="Sanitation")
        results = connector.sync_kinds(["Household"], context=self.context)
        self.assertEqual(list(results), ["program_encounters:Sanitation/Survey"])

    def test_registrations_are_left_to_their_own_steps(self):
        self.switch(kind="subject", encounter_type="")
        self.switch(encounter_type="Water")
        self.assertEqual(list(connector.sync_kinds(["Household"], context=self.context)), ["encounters:Water"])

    def test_an_empty_catalog_warns_and_returns_nothing(self):
        self.assertEqual(connector.sync_kinds(["Household"], context=self.context), {})

    def test_many_subject_types_share_one_context(self):
        self.switch(subject_type="Household", encounter_type="Water")
        self.switch(subject_type="Detailed Socio Economic Survey", encounter_type="Water INP")
        results = connector.sync_kinds(
            ["Household", "Detailed Socio Economic Survey"], context=self.context
        )
        self.assertEqual(sorted(results), ["encounters:Water", "encounters:Water INP"])

    def test_step_names_keep_the_legacy_shape(self):
        rows = [
            SyncSwitch(subject_type="Household", kind="subject"),
            SyncSwitch(subject_type="Household", kind="enrolment", program="Sanitation"),
            SyncSwitch(subject_type="Household", kind="encounter", encounter_type="Water"),
            SyncSwitch(subject_type="Household", kind="program_encounter", program="Sanitation",
                       encounter_type="Daily Reporting"),
        ]
        self.assertEqual(
            [connector.step_name(row) for row in rows],
            ["households:Household", "enrolments:Sanitation", "encounters:Water",
             "program_encounters:Sanitation/Daily Reporting"],
        )


class SubjectTreeTests(ConnectorTestCase):
    def build_tree(self):
        subject = raw(normalized(external_id="sub-1"))
        enrolment = raw(normalized(kind="enrolment", external_id="enr-1", subject_external_id="sub-1",
                                   program="Sanitation", household_number=""))
        program_encounter = raw(normalized(kind="program_encounter", external_id="penc-1",
                                           subject_external_id="sub-1", program="Sanitation",
                                           encounter_type="Daily Reporting", household_number=""))
        encounter = raw(self.encounter("enc-1"))
        self.provider.trees["sub-1"] = tree(subject, [(enrolment, [program_encounter])], [encounter])
        return subject, enrolment, program_encounter, encounter

    def test_a_subject_is_synced_registration_first_then_down_the_tree(self):
        self.build_tree()
        summary = connector.sync_subject("sub-1", self.context)
        self.assertEqual(
            [call[0] for call in self.provider.legacy_calls],
            ["subject", "enrolment", "program_encounter", "encounter"],
        )
        self.assertEqual(Record.objects.count(), 4)
        self.assertEqual(sorted(summary), ["encounter", "enrolment", "program_encounter", "subject"])
        self.assertEqual(summary["subject"]["created"], 1)

    def test_the_subject_is_never_re_fetched_for_its_own_encounters(self):
        self.build_tree()
        connector.sync_subject("sub-1", self.context)
        self.assertEqual(self.provider.subject_calls, [])

    def test_a_scheduled_visit_under_a_subject_is_counted_not_stored(self):
        subject = raw(normalized(external_id="sub-1"))
        scheduled = raw(self.encounter("enc-2", record_datetime=None), status="scheduled")
        self.provider.trees["sub-1"] = tree(subject, [], [scheduled])
        summary = connector.sync_subject("sub-1", self.context)
        self.assertEqual(summary["encounter"]["scheduled_only"], 1)
        self.assertEqual(Record.objects.filter(kind="encounter").count(), 0)

    def test_switched_off_kinds_are_left_alone(self):
        self.build_tree()
        SyncSwitch.objects.create(provider="fake", subject_type="Household", kind="encounter",
                                  encounter_type="Sanitation", is_enabled=False)
        connector.sync_subject("sub-1", self.context)
        self.assertEqual([call[0] for call in self.provider.legacy_calls],
                         ["subject", "enrolment", "program_encounter"])

    def test_a_missing_subject_is_a_failure(self):
        recorder = reporting.start("test_job", trigger="manual")
        with recorder.step("subjects") as step:
            self.assertEqual(connector.sync_subject("nope", self.context), {})
        recorder.finish()
        self.assertEqual(step.failed, 1)
        self.assertEqual(self.context.counts["failed"], 1)


class DescribeSubjectTests(ConnectorTestCase):
    def setUp(self):
        super(DescribeSubjectTests, self).setUp()
        subject = raw(normalized(external_id="sub-1", observations=[observation("Comment", "hi")]))
        done = raw(self.encounter("enc-1"))
        scheduled = raw(self.encounter("enc-2", record_datetime=None), status="scheduled")
        self.provider.trees["sub-1"] = tree(subject, [], [done, scheduled])

    def test_the_identity_block_comes_from_the_subject(self):
        described = connector.describe_subject("sub-1", self.context)
        self.assertEqual(described["subject_id"], "sub-1")
        self.assertEqual(described["subject_type"], "Household")
        self.assertEqual(described["slum"], "Lokmanya Nagar")
        self.assertEqual(described["household_number"], "42")
        self.assertFalse(described["is_voided"])

    def test_every_form_is_listed_with_its_status(self):
        forms = connector.describe_subject("sub-1", self.context)["forms"]
        self.assertEqual([form["status"] for form in forms], ["done", "done", "scheduled"])
        self.assertEqual([form["kind"] for form in forms], ["subject", "encounter", "encounter"])

    def test_already_synced_forms_are_marked(self):
        self.with_subject()
        connector.sync_record("subject", raw(normalized(external_id="sub-1")), self.context)
        forms = connector.describe_subject("sub-1", SyncContext(self.provider))["forms"]
        self.assertTrue(forms[0]["synced"])
        self.assertFalse(forms[1]["synced"])

    def test_forms_say_whether_a_legacy_writer_exists(self):
        forms = connector.describe_subject("sub-1", self.context)["forms"]
        self.assertTrue(all(form["legacy"] for form in forms))

    def test_switched_off_forms_are_marked_not_enabled(self):
        SyncSwitch.objects.create(provider="fake", subject_type="Household", kind="encounter",
                                  encounter_type="Sanitation", is_enabled=False)
        forms = connector.describe_subject("sub-1", self.context)["forms"]
        self.assertTrue(forms[0]["enabled"])
        self.assertFalse(forms[1]["enabled"])

    def test_describing_writes_nothing(self):
        connector.describe_subject("sub-1", self.context)
        self.assertEqual(Record.objects.count(), 0)


class ProviderLoadingTests(TestCase):
    def test_the_setting_names_the_provider(self):
        connector.reset_provider()
        self.addCleanup(connector.reset_provider)
        with self.settings(SURVEY_PROVIDER="survey.tests.fakes.FakeProvider"):
            self.assertIsInstance(connector.provider(), FakeProvider)

    def test_a_bare_name_is_rejected(self):
        with self.assertRaises(ImportError):
            connector.load_provider("NotDotted")

    def test_the_contract_base_class_refuses_to_guess(self):
        with self.assertRaises(NotImplementedError):
            contracts.Provider().catalog()


class EnrolmentOnDemandTests(ConnectorTestCase):
    def program_encounter(self, external_id="penc-1", enrolment="enr-1"):
        record = normalized(kind="program_encounter", external_id=external_id, subject_external_id="sub-1",
                            program="Sanitation", encounter_type="Survey", household_number="")
        built = raw(record)
        built["enrolment_id"] = enrolment
        return built

    def test_the_enrolment_is_fetched_once_and_stored_quietly(self):
        self.with_subject()
        self.provider.enrolments["enr-1"] = raw(normalized(kind="enrolment", external_id="enr-1",
                                                           subject_external_id="sub-1", program="Sanitation", household_number=""))
        connector.sync_record("program_encounter", self.program_encounter("penc-1"), self.context)
        connector.sync_record("program_encounter", self.program_encounter("penc-2"), self.context)
        self.assertEqual(self.provider.enrolment_calls, ["enr-1"])
        self.assertEqual(Record.objects.filter(kind="enrolment").count(), 1)
        self.assertEqual([call[0] for call in self.provider.legacy_calls], ["program_encounter", "program_encounter"],
                         "no legacy writer for a household enrolment")

    def test_an_enrolment_already_stored_is_not_fetched(self):
        self.with_subject()
        store_context = SyncContext(self.provider)
        connector.store.upsert(normalized(kind="enrolment", external_id="enr-1", subject_external_id="sub-1",
                                          program="Sanitation", household_number=""), store_context)
        connector.sync_record("program_encounter", self.program_encounter(), self.context)
        self.assertEqual(self.provider.enrolment_calls, [])

    def test_a_missing_enrolment_does_not_fail_the_encounter(self):
        self.with_subject()
        saved = connector.sync_record("program_encounter", self.program_encounter(enrolment="ghost"), self.context)
        self.assertTrue(saved)
        self.assertEqual(Record.objects.filter(kind="enrolment").count(), 0)

    def test_unlistable_kinds_are_left_out_of_the_listing_plan(self):
        self.provider.unlistable.add("enrolment")
        SyncSwitch.objects.create(provider="fake", subject_type="Household", kind="enrolment", program="Sanitation")
        SyncSwitch.objects.create(provider="fake", subject_type="Household", kind="encounter", encounter_type="Water")
        self.assertEqual([row.kind for row in connector.enabled_rows(["Household"])], ["encounter"])
