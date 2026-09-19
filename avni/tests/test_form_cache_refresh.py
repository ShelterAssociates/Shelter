"""The nightly form cache refresh also builds the concept dictionary and switches."""

from django.test import TestCase

from avni import paths
from avni.client import reset_client, use_client
from avni.sync import locations
from avni.tests.support import FakeApi, make_city, make_slum
from avni.tests.test_locations_match import slum_location
from avni.tests.test_metadata import routes
from notification.services import registry, reporting
from survey import connector
from survey.models import Concept, ConceptAlias, SlumAlias, SyncSwitch


class FormCacheRefreshJobTests(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city("Thane"))
        self.routes = routes()
        self.routes[paths.locations(locations.LOCATIONS_SINCE)] = {
            "content": [slum_location("u-1", "Lokmanya Nagar"), slum_location("u-2", "Unknown")], "totalPages": 1,
        }
        use_client(FakeApi(self.routes))
        connector.reset_provider()
        self.addCleanup(reset_client)
        self.addCleanup(connector.reset_provider)

    def run_job(self):
        recorder = reporting.start("avni_form_cache_refresh", trigger="manual")
        registry.resolve("avni_form_cache_refresh")(recorder, None)
        return recorder.finish()

    def test_concepts_and_switches_follow_the_catalog(self):
        run = self.run_job()
        self.assertEqual([s.name for s in run.steps.order_by("order")], ["form_cache_refresh", "survey_catalog", "slum_locations"])
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

    def test_slums_in_both_avni_and_db_are_aliased_by_exact_name(self):
        run = self.run_job()
        self.assertEqual(SlumAlias.objects.get(slum=self.slum, provider="avni").external_id, "u-1")
        extras = run.steps.get(name="slum_locations").extras
        self.assertEqual((extras["created"], extras["unmatched_avni"]), ("1", "1"))
        self.assertEqual(self.run_job().steps.get(name="slum_locations").extras["created"], "0")

    def test_locations_outage_fails_only_its_step(self):
        del self.routes[paths.locations(locations.LOCATIONS_SINCE)]
        use_client(FakeApi(self.routes))
        run = self.run_job()
        self.assertEqual(run.steps.get(name="slum_locations").status, "failed")
        self.assertEqual(run.steps.get(name="survey_catalog").status, "success")
