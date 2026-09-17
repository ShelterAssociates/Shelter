"""The nightly form cache refresh also builds the concept dictionary and switches."""

from django.test import TestCase

from avni.client import reset_client, use_client
from avni.tests.support import FakeApi
from avni.tests.test_metadata import routes
from notification.services import registry, reporting
from survey import connector
from survey.models import Concept, ConceptAlias, SyncSwitch


class FormCacheRefreshJobTests(TestCase):
    def setUp(self):
        use_client(FakeApi(routes()))
        connector.reset_provider()
        self.addCleanup(reset_client)
        self.addCleanup(connector.reset_provider)

    def run_job(self):
        recorder = reporting.start("avni_form_cache_refresh", trigger="manual")
        registry.resolve("avni_form_cache_refresh")(recorder, None)
        return recorder.finish()

    def test_concepts_and_switches_follow_the_catalog(self):
        run = self.run_job()
        self.assertEqual([s.name for s in run.steps.order_by("order")], ["form_cache_refresh", "survey_catalog"])
        self.assertEqual(run.status, "success")
        self.assertEqual(Concept.objects.get(key="do_you_have_a_toilet_at_home").data_type, "coded")
        self.assertEqual(Concept.objects.get(key="men").data_type, "answer")
        self.assertEqual(ConceptAlias.objects.get(external_id="c-First name").concept.key, "first_name")
        self.assertEqual(Concept.objects.get(key="number_of_male_members").source, "catalog")
        switches = {(s.subject_type, s.kind, s.encounter_type): s for s in SyncSwitch.objects.all()}
        self.assertTrue(switches[("Household", "encounter", "Water")].is_enabled)
        self.assertEqual(switches[("Household", "encounter", "Water")].label, "Water form")
        self.assertFalse(switches[("Toilet", "subject", "")].is_enabled)
        extras = run.steps.get(name="survey_catalog").extras
        self.assertEqual(extras["switches_created"], "5")

    def test_a_second_refresh_creates_nothing_new(self):
        self.run_job()
        concepts, aliases, switches = Concept.objects.count(), ConceptAlias.objects.count(), SyncSwitch.objects.count()
        run = self.run_job()
        self.assertEqual((Concept.objects.count(), ConceptAlias.objects.count(), SyncSwitch.objects.count()),
                         (concepts, aliases, switches))
        self.assertEqual(run.steps.get(name="survey_catalog").extras["switches_created"], "0")
