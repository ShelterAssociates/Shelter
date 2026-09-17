"""Key generation and how provider ids and names find their standard concept."""

from django.test import TestCase

from survey import concepts, contracts
from survey.models import Concept, ConceptAlias
from survey.tests.support import ref


class SlugTests(TestCase):
    def test_words_become_one_lowercase_key(self):
        self.assertEqual(concepts.slugify_key("Current place of defecation"), "current_place_of_defecation")

    def test_punctuation_and_repeats_collapse(self):
        self.assertEqual(concepts.slugify_key("Have you applied  for a toilet??"), "have_you_applied_for_a_toilet")

    def test_non_ascii_names_have_no_slug(self):
        self.assertEqual(concepts.slugify_key("शौचालय"), "")

    def test_key_is_capped(self):
        self.assertLessEqual(len(concepts.slugify_key("word " * 100)), concepts.MAX_KEY_LENGTH)


class UniqueKeyTests(TestCase):
    def test_free_name_keeps_its_slug(self):
        self.assertEqual(concepts.unique_key("Water source"), "water_source")

    def test_collision_gets_a_suffix(self):
        Concept.objects.create(key="water_source", name="Water source")
        self.assertEqual(concepts.unique_key("Water source"), "water_source_2")

    def test_keys_claimed_earlier_in_the_same_run_are_avoided(self):
        cache = concepts.ConceptCache()
        cache.claimed_keys.add("water_source")
        self.assertEqual(concepts.unique_key("Water source", cache.claimed_keys), "water_source_2")

    def test_unsluggable_names_are_numbered(self):
        self.assertEqual(concepts.unique_key("शौचालय"), "concept_1")
        Concept.objects.create(key="concept_1", name="शौचालय")
        self.assertEqual(concepts.unique_key("पाणी"), "concept_2")


class ResolveTests(TestCase):
    def test_first_sighting_creates_concept_and_alias(self):
        concept = concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        self.assertEqual(concept.key, "water_source")
        self.assertEqual(concept.sa_text, "Water source")
        self.assertEqual(concept.data_type, "coded")
        self.assertTrue(concept.is_question)
        alias = concept.aliases.get()
        self.assertEqual((alias.provider, alias.external_id, alias.external_name), ("avni", "c-1", "Water source"))

    def test_second_sighting_reuses_the_alias(self):
        concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        self.assertEqual(Concept.objects.count(), 1)
        self.assertEqual(ConceptAlias.objects.count(), 1)

    def test_id_wins_over_name(self):
        first = concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        again = concepts.resolve(ref("Water supply", "coded", "c-1"), "avni")
        self.assertEqual(first.pk, again.pk)

    def test_a_rename_keeps_the_key_and_moves_sa_text(self):
        concept = concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        concepts.resolve(ref("Water supply", "coded", "c-1"), "avni")
        concept.refresh_from_db()
        self.assertEqual(concept.key, "water_source")
        self.assertEqual(concept.name, "Water supply")
        self.assertEqual(concept.sa_text, "Water supply")

    def test_a_rename_leaves_an_edited_sa_text_alone(self):
        concept = concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        Concept.objects.filter(pk=concept.pk).update(sa_text="Source of water (SA)")
        concepts.resolve(ref("Water supply", "coded", "c-1"), "avni")
        concept.refresh_from_db()
        self.assertEqual(concept.sa_text, "Source of water (SA)")

    def test_name_only_sighting_finds_the_concept_and_adds_an_alias(self):
        concept = Concept.objects.create(key="water_source", name="Water source")
        found = concepts.resolve(ref("Water source"), "avni")
        self.assertEqual(found.pk, concept.pk)
        self.assertEqual(concept.aliases.count(), 1)

    def test_a_placeholder_gets_its_name_and_key_when_first_named(self):
        placeholder = concepts.resolve(contracts.ConceptRef(external_id="c-9", name="", data_type=""), "avni")
        self.assertEqual(placeholder.key, "concept_1")
        concepts.resolve(ref("Toilet users", "coded", "c-9"), "avni")
        placeholder.refresh_from_db()
        self.assertEqual(placeholder.key, "toilet_users")
        self.assertEqual(placeholder.name, "Toilet users")

    def test_roles_are_or_ed_in(self):
        concepts.resolve(ref("Yes", "", "a-1"), "avni", role="answer")
        concept = concepts.resolve(ref("Yes", "", "a-1"), "avni", role="question")
        self.assertTrue(concept.is_answer)
        self.assertTrue(concept.is_question)

    def test_answers_are_stored_as_answer_type(self):
        concept = concepts.resolve(ref("Use CTB", "coded", "a-2"), "avni", role="answer")
        self.assertEqual(concept.key, "use_ctb")
        self.assertEqual(concept.data_type, "answer")

    def test_a_known_type_fills_an_unknown_one(self):
        concept = concepts.resolve(ref("Members", "", "c-3"), "avni")
        self.assertEqual(concept.data_type, "unknown")
        concepts.resolve(ref("Members", "numeric", "c-3"), "avni")
        concept.refresh_from_db()
        self.assertEqual(concept.data_type, "numeric")

    def test_another_provider_maps_its_own_id_onto_the_same_key(self):
        concept = concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        kobo = concepts.resolve(ref("Water source", "coded", "grp/water"), "kobo")
        self.assertEqual(kobo.pk, concept.pk)
        self.assertEqual(concept.aliases.count(), 2)

    def test_an_empty_ref_resolves_to_nothing(self):
        self.assertIsNone(concepts.resolve(contracts.ConceptRef(), "avni"))

    def test_create_false_does_not_write(self):
        self.assertIsNone(concepts.resolve(ref("Unseen", "text", "c-x"), "avni", create=False))
        self.assertEqual(Concept.objects.count(), 0)


class UpsertCatalogTests(TestCase):
    def entry(self):
        return contracts.CatalogEntry(
            subject_type="Household", kind="subject", label="Household registration",
            form_external_id="form-1",
            concepts=[
                (ref("Water source", "coded", "c-1"), [ref("Tap", "", "a-1"), ref("Well", "", "a-2")]),
                (ref("Members", "numeric", "c-2"), []),
            ],
        )

    def test_questions_and_answers_are_claimed(self):
        counts = concepts.upsert_catalog([self.entry()], "avni")
        self.assertEqual(counts, {"forms": 1, "questions": 2, "answers": 2})
        self.assertEqual(sorted(Concept.objects.values_list("key", flat=True)), ["members", "tap", "water_source", "well"])
        self.assertEqual(Concept.objects.get(key="tap").source, "catalog")

    def test_running_it_twice_changes_nothing(self):
        concepts.upsert_catalog([self.entry()], "avni")
        concepts.upsert_catalog([self.entry()], "avni")
        self.assertEqual(Concept.objects.count(), 4)
        self.assertEqual(ConceptAlias.objects.count(), 4)

    def test_the_catalog_upgrades_a_concept_first_seen_in_a_record(self):
        observed = concepts.resolve(ref("Water source", "coded", "c-1"), "avni")
        self.assertEqual(observed.source, "observed")
        concepts.upsert_catalog([self.entry()], "avni")
        observed.refresh_from_db()
        self.assertEqual(observed.source, "catalog")
