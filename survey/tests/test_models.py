"""Constraints and read helpers of the core tables."""

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from survey.models import Answer, Concept, ConceptAlias, Record
from survey.tests.support import make_city, make_slum


def concept(key, name=None, data_type="text"):
    return Concept.objects.create(key=key, name=name or key, data_type=data_type, is_question=True)


class RecordConstraintTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def record(self, **overrides):
        fields = {
            "provider": "avni", "kind": "subject", "external_id": "sub-1", "version": 1,
            "slum": self.slum, "city": self.city, "household_number": "42",
            "record_datetime": timezone.now(),
        }
        fields.update(overrides)
        return Record.objects.create(**fields)

    def test_same_external_id_twice_in_one_version_is_rejected(self):
        self.record()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.record(household_number="43")

    def test_same_external_id_in_another_version_is_allowed(self):
        self.record()
        self.record(version=2)
        self.assertEqual(Record.objects.filter(external_id="sub-1").count(), 2)

    def test_one_active_household_number_per_slum_and_version(self):
        self.record()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.record(external_id="sub-2")

    def test_voided_household_numbers_are_unlimited(self):
        self.record(is_voided=True)
        self.record(external_id="sub-2", is_voided=True)
        self.record(external_id="sub-3", is_voided=True)
        self.record(external_id="sub-4")
        self.assertEqual(Record.objects.filter(household_number="42").count(), 4)

    def test_the_same_number_in_another_version_is_allowed(self):
        self.record()
        self.record(external_id="sub-2", version=2)
        self.assertEqual(Record.objects.count(), 2)

    def test_encounters_do_not_take_the_household_slot(self):
        self.record()
        self.record(external_id="enc-1", kind="encounter", encounter_type="Sanitation")
        self.assertEqual(Record.objects.count(), 2)

    def test_records_without_a_household_number_do_not_collide(self):
        self.record(household_number="")
        self.record(external_id="sub-2", household_number="")
        self.assertEqual(Record.objects.count(), 2)

    def test_is_filled_is_false_for_a_cancelled_visit(self):
        row = self.record(kind="encounter", record_datetime=None, cancel_datetime=timezone.now())
        self.assertFalse(row.is_filled)
        self.assertTrue(self.record(external_id="enc-2", kind="encounter").is_filled)


class ConceptAliasTests(TestCase):
    def test_one_alias_per_provider_id(self):
        first = concept("water_source")
        ConceptAlias.objects.create(concept=first, provider="avni", external_id="c-1", external_name="Water source")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConceptAlias.objects.create(
                    concept=concept("other"), provider="avni", external_id="c-1", external_name="Other"
                )

    def test_many_aliases_may_have_no_external_id(self):
        ConceptAlias.objects.create(concept=concept("a"), provider="avni", external_name="A")
        ConceptAlias.objects.create(concept=concept("b"), provider="avni", external_name="B")
        self.assertEqual(ConceptAlias.objects.count(), 2)

    def test_the_same_id_may_belong_to_another_provider(self):
        ConceptAlias.objects.create(concept=concept("a"), provider="avni", external_id="c-1", external_name="A")
        ConceptAlias.objects.create(concept=concept("b"), provider="kobo", external_id="c-1", external_name="B")
        self.assertEqual(ConceptAlias.objects.count(), 2)

    def test_one_alias_per_provider_name(self):
        ConceptAlias.objects.create(concept=concept("a"), provider="avni", external_id="c-1", external_name="Same")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConceptAlias.objects.create(
                    concept=concept("b"), provider="avni", external_id="c-2", external_name="Same"
                )


class AnswersByKeyTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.row = Record.objects.create(
            provider="avni", kind="encounter", external_id="enc-1", slum=self.slum, city=self.city
        )

    def answer(self, question, **fields):
        return Answer.objects.create(record=self.row, question=question, **fields)

    def test_single_answers_are_scalars(self):
        self.answer(concept("members", data_type="numeric"), value_text="4", value_number=4.0)
        self.assertEqual(self.row.answers_by_key(), {"members": 4.0})

    def test_repeated_answers_to_one_question_become_a_list(self):
        question = concept("toilet_users", data_type="coded")
        self.answer(question, value_text="Men", position=0)
        self.answer(question, value_text="Women", position=1)
        self.assertEqual(self.row.answers_by_key(), {"toilet_users": ["Men", "Women"]})

    def test_group_children_are_listed_per_repeat(self):
        group = concept("family", data_type="group")
        name = concept("member_name")
        age = concept("member_age", data_type="numeric")
        self.answer(name, group=group, repeat_index=0, value_text="Asha", position=0)
        self.answer(age, group=group, repeat_index=0, value_text="30", value_number=30.0, position=1)
        self.answer(name, group=group, repeat_index=1, value_text="Ravi", position=2)
        self.assertEqual(
            self.row.answers_by_key(),
            {"family": [{"member_name": "Asha", "member_age": 30.0}, {"member_name": "Ravi"}]},
        )

    def test_grouped_and_ungrouped_answers_live_side_by_side(self):
        self.answer(concept("surveyor"), value_text="Asha")
        self.answer(concept("child_name"), group=concept("children", data_type="group"), value_text="Ravi")
        self.assertEqual(
            self.row.answers_by_key(), {"surveyor": "Asha", "children": [{"child_name": "Ravi"}]}
        )
