"""Small paths the main suites do not reach: helpers, __str__, fallbacks."""

from datetime import date, datetime

from django.test import TestCase
from django.utils import timezone

from survey import concepts, connector, contracts, store, switches, versions, window
from survey.models import Answer, Concept, ConceptAlias, Record, SlumDataVersion, SyncSwitch
from survey.tests.fakes import FakeProvider, raw
from survey.tests.support import make_city, make_slum, normalized, observation, ref


class ModelStrTests(TestCase):
    def test_every_model_prints_something_useful(self):
        slum = make_slum(make_city())
        concept = Concept.objects.create(key="k", name="K")
        alias = ConceptAlias.objects.create(concept=concept, provider="avni", external_id="c-1", external_name="K")
        version = SlumDataVersion(slum=slum, version=2, started_on=timezone.now())
        switch = SyncSwitch(subject_type="Household", kind="encounter", encounter_type="Water")
        record = Record(kind="encounter", encounter_type="Water", external_id="e1")
        answer = Answer(question=concept, value_text="hello")
        self.assertEqual(str(concept), "k")
        self.assertEqual(str(alias), "avni:K")
        self.assertEqual(str(ConceptAlias(provider="avni", external_id="c-9")), "avni:c-9")
        self.assertIn("v2", str(version))
        self.assertEqual(str(switch), "Household / encounter / Water")
        self.assertEqual(str(record), "encounter Water e1")
        self.assertIn("hello", str(answer))

    def test_answer_value_prefers_number_then_date_then_text(self):
        moment = timezone.now()
        self.assertEqual(Answer(value_number=2.0, value_text="2").value(), 2.0)
        self.assertEqual(Answer(value_date=moment, value_text="x").value(), moment)
        self.assertEqual(Answer(value_text="t").value(), "t")

    def test_three_answers_to_one_question_extend_the_list(self):
        slum = make_slum(make_city())
        record = Record.objects.create(provider="avni", kind="subject", external_id="s", slum=slum)
        question = Concept.objects.create(key="q", name="Q")
        for index, text in enumerate(("a", "b", "c")):
            Answer.objects.create(record=record, question=question, value_text=text, position=index)
        self.assertEqual(record.answers_by_key(), {"q": ["a", "b", "c"]})


class StoreHelperTests(TestCase):
    def test_parse_moment_accepts_python_dates_and_rejects_junk(self):
        naive = datetime(2026, 9, 1, 10, 0)
        self.assertTrue(timezone.is_aware(store.parse_moment(naive)))
        aware = timezone.make_aware(naive)
        self.assertEqual(store.parse_moment(aware), aware)
        self.assertEqual(store.parse_moment(date(2026, 9, 1)).date(), date(2026, 9, 1))
        self.assertIsNone(store.parse_moment("not a date at all"))
        self.assertIsNone(store.parse_moment(""))
        self.assertIsNotNone(store.parse_moment("1 Sep 2026"), "fuzzy dates still parse")

    def test_resolve_slum_with_no_name(self):
        context = store.SyncContext(FakeProvider())
        self.assertEqual(store.resolve_slum("", context), (None, None))

    def test_text_helpers(self):
        self.assertEqual(store.number_text(4.0), "4")
        self.assertEqual(store.number_text(4.5), "4.5")
        self.assertEqual(store.as_text(None), "")
        self.assertEqual(store.as_text({"a": 1}), '{"a": 1}')
        self.assertIn("<object", store.as_json(object()), "unserialisable falls back to str")
        self.assertIsNone(store.known_answer("", store.SyncContext(FakeProvider())))
        self.assertIsNone(store.known_answer("x" * 600, store.SyncContext(FakeProvider())))

    def test_a_non_household_integrity_error_is_swallowed_only_when_quiet(self):
        make_slum(make_city())
        context = store.SyncContext(FakeProvider())
        too_long = normalized(external_id="e" * 300)
        self.assertEqual(store.upsert(too_long, context, quiet=True), "failed")

    def test_link_household_is_a_no_op_when_the_row_is_already_known(self):
        context = store.SyncContext(FakeProvider())
        context.household_rows["sub-1"] = 5
        self.assertFalse(store.link_household(normalized(), context))

    def test_link_household_without_a_matching_row(self):
        make_slum(make_city())
        context = store.SyncContext(FakeProvider())
        self.assertFalse(store.link_household(normalized(), context))


class ConceptEdgeTests(TestCase):
    def test_slug_helpers(self):
        self.assertEqual(concepts.slugify_key("a---b"), "a_b")
        self.assertEqual(concepts.slugify_key(None), "")

    def test_an_alias_gains_its_id_on_a_later_sighting(self):
        concept = concepts.resolve(ref("Water source", "coded"), "avni")
        concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        self.assertEqual(concept.aliases.get().external_id, "c-1")

    def test_a_question_seen_later_as_an_answer_gains_the_answer_role(self):
        concept = concepts.resolve(ref("Other", "text", "c-1"), "avni")
        concepts.resolve(ref("Other", "", "a-1"), "avni", role="answer")
        concept.refresh_from_db()
        self.assertTrue(concept.is_question and concept.is_answer)


class SwitchEdgeTests(TestCase):
    def setUp(self):
        connector.use_provider(FakeProvider())
        self.addCleanup(connector.reset_provider)

    def test_provider_key_passthrough(self):
        self.assertEqual(switches.provider_key("kobo"), "kobo")
        self.assertEqual(switches.provider_key(), "fake")

    def test_enabled_subject_types(self):
        SyncSwitch.objects.create(provider="fake", subject_type="Household", kind="subject")
        SyncSwitch.objects.create(provider="fake", subject_type="Toilet", kind="subject", is_enabled=False)
        self.assertEqual(switches.enabled_subject_types(), ["Household"])
        self.assertEqual(switches.enabled_subject_types(kinds=["encounter"]), [])

    def test_sync_catalog_updates_label_and_form_id(self):
        provider = FakeProvider([contracts.CatalogEntry("Household", "subject", label="Old", form_external_id="f1")])
        switches.sync_catalog(provider)
        provider.catalog_entries = [contracts.CatalogEntry("Household", "subject", label="New", form_external_id="f2")]
        switches.sync_catalog(provider)
        row = SyncSwitch.objects.get()
        self.assertEqual((row.label, row.form_external_id), ("New", "f2"))


class ConnectorEdgeTests(TestCase):
    def setUp(self):
        make_slum(make_city())
        self.provider = FakeProvider()
        connector.use_provider(self.provider)
        self.addCleanup(connector.reset_provider)
        self.context = store.SyncContext(self.provider)

    def test_a_member_enrolment_fetched_on_demand_reaches_its_legacy_writer(self):
        self.provider.subjects["mem-1"] = {"ID": "mem-1"}
        self.provider.legacy_handles = lambda kind, subject_type, encounter_type="": True
        self.provider.enrolments["enr-1"] = raw(normalized(kind="enrolment", external_id="enr-1", subject_external_id="mem-1",
                                                           subject_type="Family Member", program="MHM", household_number=""))
        encounter = raw(normalized(kind="program_encounter", external_id="p1", subject_external_id="mem-1",
                                   subject_type="Family Member", program="MHM", encounter_type="Follow up", household_number=""))
        encounter["enrolment_id"] = "enr-1"
        connector.sync_record("program_encounter", encounter, self.context)
        self.assertEqual([call[0] for call in self.provider.legacy_calls], ["enrolment", "program_encounter"])

    def test_a_quiet_store_survives_a_subject_that_cannot_be_read(self):
        voided = raw(normalized(kind="encounter", external_id="e1", subject_external_id="ghost",
                                encounter_type="Water", household_number="", is_voided=True), status="voided")
        connector.sync_record("encounter", voided, self.context)
        self.assertTrue(Record.objects.get(external_id="e1").is_voided)

    def test_a_quiet_store_survives_a_record_that_cannot_be_normalized(self):
        self.provider.normalize = lambda kind, raw_record, subject_raw=None: (_ for _ in ()).throw(ValueError("bad"))
        connector.sync_record("subject", raw(normalized(is_voided=True), status="voided"), self.context)
        self.assertEqual(Record.objects.count(), 0)
        self.assertEqual(self.context.counts["failed"], 1)


class VersionAndWindowEdgeTests(TestCase):
    def test_current_version(self):
        slum = make_slum(make_city())
        SlumDataVersion.objects.create(slum=slum, version=3, started_on=timezone.now() - timezone.timedelta(days=1))
        self.assertEqual(versions.current_version(slum.id), 3)

    def test_structure_window_reads_structure_cities_only(self):
        from graphs.models import HouseholdData

        city = make_city("Banthara Town")
        slum = make_slum(city)
        HouseholdData.objects.create(household_number="1", slum=slum, city=city, submission_date="2026-03-01T00:00:00Z")
        self.assertIsNotNone(window.latest_submission("Structure"))
        self.assertIsNone(window.latest_submission("Household"))


class WindowStartTests(TestCase):
    """Each kind follows the newest record of that kind we hold; nothing held means 2018."""

    def test_first_sync_of_a_kind_starts_from_2018(self):
        self.assertEqual(window.window_start(kind="encounter", encounter_type="Water"), window.FIRST_SYNC_START)

    def test_a_kind_follows_the_newest_record_of_its_own_type(self):
        Record.objects.create(provider="avni", kind="encounter", external_id="w1", encounter_type="Water",
                              last_modified_at="2026-03-05T09:00:00Z")
        Record.objects.create(provider="avni", kind="encounter", external_id="s1", encounter_type="Sanitation",
                              last_modified_at="2026-06-01T09:00:00Z")
        self.assertEqual(window.window_start(kind="encounter", encounter_type="Water"), "2026-03-04T00:00:00.000Z")

    def test_program_encounters_are_told_apart_by_program_and_type(self):
        Record.objects.create(provider="avni", kind="program_encounter", external_id="p1", program="RHS",
                              encounter_type="Daily Reporting", last_modified_at="2026-03-05T09:00:00Z")
        self.assertEqual(
            window.window_start(kind="program_encounter", program="RHS", encounter_type="Daily Reporting"),
            "2026-03-04T00:00:00.000Z",
        )
        self.assertEqual(
            window.window_start(kind="program_encounter", program="RHS", encounter_type="Family factsheet"),
            window.FIRST_SYNC_START,
        )

    def test_a_non_household_subject_type_follows_its_own_records(self):
        from graphs.models import HouseholdData

        city = make_city()
        slum = make_slum(city)
        HouseholdData.objects.create(household_number="1", slum=slum, city=city, submission_date="2026-03-01T00:00:00Z")
        self.assertEqual(window.window_start("Family Member"), window.FIRST_SYNC_START)
        Record.objects.create(provider="avni", kind="subject", external_id="m1", subject_type="Family Member",
                              last_modified_at="2026-04-10T09:00:00Z")
        self.assertEqual(window.window_start("Family Member"), "2026-04-09T00:00:00.000Z")

    def test_household_registrations_keep_following_the_mastersheet(self):
        from graphs.models import HouseholdData

        self.assertEqual(window.window_start("Household"), window.FIRST_SYNC_START)
        city = make_city()
        slum = make_slum(city)
        HouseholdData.objects.create(household_number="1", slum=slum, city=city, submission_date="2026-03-01T00:00:00Z")
        self.assertEqual(window.window_start("Household"), "2026-02-28T00:00:00.000Z")

    def test_an_earlier_successful_run_does_not_hide_a_kind_never_synced(self):
        from notification.models import JobRun
        from notification.services import reporting

        JobRun.objects.create(job_key="avni_daily_sync", status="success", started_on=timezone.now())
        recorder = reporting.start("avni_daily_sync")
        try:
            self.assertEqual(window.window_start(kind="encounter", encounter_type="Water"), window.FIRST_SYNC_START)
        finally:
            recorder.finish()
