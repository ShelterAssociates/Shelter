"""Writing normalized records: identity, versions, value typing, counters."""

from django.test import TestCase
from django.utils import timezone

from graphs.models import HouseholdData
from survey import contracts, store
from survey.models import Answer, Concept, Record, SlumDataVersion
from survey.tests.fakes import FakeProvider
from survey.tests.support import make_city, make_slum, normalized, observation, ref


def moment(text):
    return timezone.make_aware(timezone.datetime.strptime(text, "%Y-%m-%d %H:%M"))


def utc_moment(text):
    return timezone.make_aware(timezone.datetime.strptime(text, "%Y-%m-%d %H:%M"), timezone.utc)


class StoreTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.provider = FakeProvider()
        self.context = store.SyncContext(self.provider)

    def household(self, number="42"):
        return HouseholdData.objects.create(
            household_number=number, slum=self.slum, city=self.city,
            submission_date="2020-01-01T00:00:00Z", rhs_data={},
        )


class RecordWriteTests(StoreTestCase):
    def test_a_new_record_is_created_with_its_identity(self):
        self.household()
        self.assertEqual(store.upsert(normalized(), self.context), "created")
        row = Record.objects.get()
        self.assertEqual(row.provider, "fake")
        self.assertEqual(row.kind, "subject")
        self.assertEqual(row.slum, self.slum)
        self.assertEqual(row.city, self.city)
        self.assertEqual(row.household_number, "42")
        self.assertEqual(row.household, HouseholdData.objects.get())
        self.assertEqual(row.version, 1)
        self.assertEqual(self.context.counts["created"], 1)

    def test_a_second_pass_updates_the_same_row(self):
        store.upsert(normalized(), self.context)
        self.assertEqual(store.upsert(normalized(household_number="43"), self.context), "updated")
        self.assertEqual(Record.objects.count(), 1)
        self.assertEqual(Record.objects.get().household_number, "43")
        self.assertEqual(self.context.counts["updated"], 1)

    def test_household_numbers_are_normalized(self):
        store.upsert(normalized(household_number="0042"), self.context)
        self.assertEqual(Record.objects.get().household_number, "42")

    def test_an_unknown_slum_leaves_the_links_null(self):
        store.upsert(normalized(slum_name="Nowhere"), self.context)
        row = Record.objects.get()
        self.assertIsNone(row.slum)
        self.assertIsNone(row.city)
        self.assertEqual(row.slum_name, "Nowhere")

    def test_a_household_that_does_not_exist_yet_is_counted_unlinked(self):
        store.upsert(normalized(), self.context)
        self.assertIsNone(Record.objects.get().household)
        self.assertEqual(self.context.counts["unlinked"], 1)

    def test_link_household_attaches_the_row_the_legacy_writer_created(self):
        store.upsert(normalized(), self.context)
        self.household()
        self.assertTrue(store.link_household(normalized(), self.context))
        self.assertEqual(Record.objects.get().household, HouseholdData.objects.get())
        self.assertEqual(self.context.counts["unlinked"], 0)

    def test_an_encounter_links_through_its_subject_record(self):
        household = self.household()
        store.upsert(normalized(), self.context)
        encounter = normalized(kind="encounter", external_id="enc-1", subject_external_id="sub-1",
                               encounter_type="Sanitation", household_number="")
        store.upsert(encounter, self.context)
        self.assertEqual(Record.objects.get(external_id="enc-1").household, household)

    def test_a_voided_record_is_kept_with_its_answers(self):
        record = normalized(is_voided=True, observations=[observation("Comment", "gone")])
        store.upsert(record, self.context)
        row = Record.objects.get()
        self.assertTrue(row.is_voided)
        self.assertEqual(row.answers.count(), 1)
        self.assertEqual(self.context.counts["voided"], 1)

    def test_unchanged_sees_a_record_already_stored_at_this_moment(self):
        store.upsert(normalized(), self.context)
        self.assertTrue(store.unchanged("fake", "sub-1", "2026-09-01T06:47:34.548Z"))
        self.assertFalse(store.unchanged("fake", "sub-1", "2026-09-02T06:47:34.548Z"))
        self.assertFalse(store.unchanged("fake", "other", "2026-09-01T06:47:34.548Z"))

    def test_unchanged_is_false_without_a_modification_stamp(self):
        self.assertFalse(store.unchanged("fake", "sub-1", None))

    def test_one_subject_is_fetched_once_for_many_records(self):
        self.provider.subjects["sub-1"] = {"ID": "sub-1"}
        self.context.subject("sub-1")
        self.context.subject("sub-1")
        self.assertEqual(self.provider.subject_calls, ["sub-1"])


class DuplicateHouseholdTests(StoreTestCase):
    def test_a_second_active_household_number_fails_and_is_counted(self):
        store.upsert(normalized(external_id="sub-1"), self.context)
        outcome = store.upsert(normalized(external_id="sub-2"), self.context)
        self.assertEqual(outcome, "failed")
        self.assertEqual(self.context.counts["duplicate_household"], 1)
        self.assertEqual(Record.objects.count(), 1)

    def test_the_message_names_the_record_holding_the_number(self):
        store.upsert(normalized(external_id="sub-1"), self.context)
        message = store.duplicate_message(normalized(external_id="sub-2"), self.context)
        self.assertIn("household number 42", message)
        self.assertIn("Lokmanya Nagar", message)
        self.assertIn("sub-1", message)

    def test_a_voided_duplicate_is_allowed(self):
        store.upsert(normalized(external_id="sub-1"), self.context)
        self.assertEqual(store.upsert(normalized(external_id="sub-2", is_voided=True), self.context), "created")
        self.assertEqual(Record.objects.count(), 2)


class VersionRoutingTests(StoreTestCase):
    def start_version_two(self, when="2026-09-10 00:00"):
        SlumDataVersion.objects.create(slum=self.slum, version=2, started_on=moment(when))

    def test_records_modified_before_the_new_version_stay_in_version_one(self):
        self.start_version_two()
        store.upsert(normalized(last_modified_at="2026-09-05T10:00:00.000Z"), self.context)
        self.assertEqual(Record.objects.get().version, 1)

    def test_an_edit_after_the_new_version_writes_a_second_row(self):
        store.upsert(normalized(last_modified_at="2026-09-05T10:00:00.000Z"), self.context)
        self.start_version_two()
        later_run = store.SyncContext(self.provider)
        store.upsert(normalized(last_modified_at="2026-09-12T10:00:00.000Z"), later_run)
        self.assertEqual(sorted(Record.objects.values_list("version", flat=True)), [1, 2])
        old = Record.objects.get(version=1)
        self.assertEqual(old.last_modified_at, utc_moment("2026-09-05 10:00"))

    def test_an_untouched_old_record_is_not_copied_into_the_new_version(self):
        store.upsert(normalized(last_modified_at="2026-09-05T10:00:00.000Z"), self.context)
        self.start_version_two()
        self.assertTrue(store.unchanged("fake", "sub-1", "2026-09-05T10:00:00.000Z"))
        self.assertEqual(Record.objects.count(), 1)

    def test_a_version_added_mid_run_applies_from_the_next_run(self):
        """version_for reads a slum's versions once per run, like every other memo."""
        self.start_version_two()
        store.upsert(normalized(last_modified_at="2026-09-12T10:00:00.000Z"), self.context)
        self.assertEqual(Record.objects.get().version, 2)


class AnswerTypeTests(StoreTestCase):
    def store_one(self, *observations):
        store.upsert(normalized(observations=list(observations)), self.context)
        return list(Record.objects.get().answers.select_related("question", "answer", "group").all())

    def test_numeric(self):
        row = self.store_one(observation("Members", "4", "numeric"))[0]
        self.assertEqual(row.value_number, 4.0)
        self.assertEqual(row.value_text, "4")
        self.assertIsNone(row.value_date)

    def test_numeric_that_is_not_a_number_keeps_the_text(self):
        row = self.store_one(observation("Members", "many", "numeric"))[0]
        self.assertIsNone(row.value_number)
        self.assertEqual(row.value_text, "many")

    def test_date(self):
        row = self.store_one(observation("Date of survey", "2026-09-01", "date"))[0]
        self.assertEqual(row.value_date, moment("2026-09-01 00:00"))
        self.assertTrue(row.value_text.startswith("2026-09-01"))

    def test_datetime(self):
        row = self.store_one(observation("Seen at", "2026-09-01T06:47:34.548Z", "datetime"))[0]
        self.assertIsNotNone(row.value_date)

    def test_time_that_cannot_be_parsed_stays_text(self):
        row = self.store_one(observation("Duration", "PT2H", "time"))[0]
        self.assertEqual(row.value_text, "PT2H")

    def test_coded_links_the_answer_concept(self):
        row = self.store_one(observation("Water source", "Tap", "coded", answer_name="Tap"))[0]
        self.assertEqual(row.answer.name, "Tap")
        self.assertEqual(row.answer.key, "tap")
        self.assertTrue(row.answer.is_answer)
        self.assertEqual(row.value_text, "Tap")

    def test_multi_select_writes_one_row_per_option(self):
        rows = self.store_one(
            observation("Toilet users", "Men", "coded", answer_name="Men", position=0),
            observation("Toilet users", "Women", "coded", answer_name="Women", position=1),
        )
        self.assertEqual([row.value_text for row in rows], ["Men", "Women"])
        self.assertEqual(len({row.question_id for row in rows}), 1)

    def test_text(self):
        row = self.store_one(observation("Comment", "all fine", "text"))[0]
        self.assertEqual(row.value_text, "all fine")

    def test_media_keeps_the_url(self):
        row = self.store_one(observation("Photo", "https://x/y.jpg", "media"))[0]
        self.assertEqual(row.value_text, "https://x/y.jpg")

    def test_location_is_stored_as_json(self):
        row = self.store_one(observation("Where", {"x": 1.5, "y": 2.5}, "location"))[0]
        self.assertEqual(row.value_text, '{"x": 1.5, "y": 2.5}')

    def test_reference(self):
        row = self.store_one(observation("Linked subject", "sub-9", "reference"))[0]
        self.assertEqual(row.value_text, "sub-9")

    def test_unknown_numbers_are_inferred(self):
        row = self.store_one(observation("Count", 7, "unknown"))[0]
        self.assertEqual(row.value_number, 7.0)

    def test_unknown_booleans_read_as_yes_or_no(self):
        self.assertEqual(self.store_one(observation("Has toilet", True, "unknown"))[0].value_text, "Yes")

    def test_unknown_text_links_a_known_answer_concept(self):
        Concept.objects.create(key="use_ctb", name="Use CTB", data_type="answer", is_answer=True)
        row = self.store_one(observation("Where do you go", "Use CTB", "unknown"))[0]
        self.assertEqual(row.answer.key, "use_ctb")

    def test_unknown_structures_become_json(self):
        row = self.store_one(observation("Anything", ["a", "b"], "unknown"))[0]
        self.assertEqual(row.value_text, '["a", "b"]')

    def test_group_children_keep_their_group_and_repeat(self):
        group = ref("Family member", "group", "g-1")
        rows = self.store_one(
            observation("Name", "Asha", group=group, repeat_index=0, position=0),
            observation("Name", "Ravi", group=group, repeat_index=1, position=1),
        )
        self.assertEqual([row.repeat_index for row in rows], [0, 1])
        self.assertEqual(rows[0].group.key, "family_member")

    def test_answers_are_replaced_not_appended(self):
        store.upsert(normalized(observations=[observation("Comment", "first")]), self.context)
        first_ids = list(Answer.objects.values_list("id", flat=True))
        store.upsert(normalized(observations=[observation("Comment", "second")]), self.context)
        self.assertEqual(Answer.objects.count(), 1)
        self.assertEqual(Answer.objects.get().value_text, "second")
        self.assertNotEqual(list(Answer.objects.values_list("id", flat=True)), first_ids)

    def test_an_observation_with_no_concept_at_all_is_dropped(self):
        rows = self.store_one(
            contracts.Observation(question=contracts.ConceptRef(), value="x"),
            observation("Comment", "kept"),
        )
        self.assertEqual([row.value_text for row in rows], ["kept"])

    def test_answers_by_key_reads_what_was_written(self):
        self.store_one(
            observation("Members", "4", "numeric"),
            observation("Name", "Asha", group=ref("Family member", "group", "g-1"), repeat_index=0),
        )
        self.assertEqual(
            Record.objects.get().answers_by_key(),
            {"members": 4.0, "family_member": [{"name": "Asha"}]},
        )


class QuietTests(StoreTestCase):
    def test_quiet_swallows_a_failure_and_counts_it(self):
        broken = normalized(external_id="x" * 300)
        self.assertEqual(store.upsert(broken, self.context, quiet=True), "failed")
        self.assertEqual(self.context.counts["failed"], 1)

    def test_loud_lets_the_failure_out(self):
        with self.assertRaises(Exception):
            store.upsert(normalized(external_id="x" * 300), self.context)
