"""Registry jobs run through the real recorder against a fake AVNI."""

from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase

from avni import paths, watermark
from avni.client import reset_client, use_client
from avni.jobs import manual_sync
from avni.tests.support import FakeApi, make_city, make_slum, page, subject_record
from graphs.models import HouseholdData
from notification.models import JobDefinition, JobRun, JobStepConfig
from notification.services import registry, reporting

SINCE = "2026-01-01T00:00:00.000Z"


class JobTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.api = FakeApi()
        use_client(self.api)

    def tearDown(self):
        reset_client()

    def run_job(self, key, params=None, definition=None):
        recorder = reporting.start(key, trigger="manual", definition=definition)
        registry.resolve(key)(recorder, params)
        return recorder.finish()


class DailySyncTests(JobTestCase):
    def test_every_step_runs_even_when_one_cannot_list(self):
        self.api.routes[paths.program_encounters("Daily Reporting", SINCE)] = page([])
        self.api.routes[paths.program_encounters("Family factsheet", SINCE)] = page([])
        self.api.routes[paths.subjects("New_Mobilization_Form", SINCE)] = page([])
        # households listing is missing -> AvniError inside step 1
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"})
        names = list(run.steps.order_by("order").values_list("name", "status"))
        self.assertEqual(names, [
            ("households:Household", "failed"), ("daily_reporting", "success"),
            ("family_factsheets", "success"), ("mobilization", "success"),
        ])
        self.assertIn("AvniError", run.steps.get(name="households:Household").error)
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.window_label, "modified since 2026-01-01T00:00:00.000Z")

    def test_disabled_step_is_skipped(self):
        definition = JobDefinition.objects.create(key="avni_daily_sync", display_name="d")
        JobStepConfig.objects.create(job=definition, step_name="households:Household", is_enabled=False)
        for path in (paths.program_encounters("Daily Reporting", SINCE), paths.program_encounters("Family factsheet", SINCE),
                     paths.subjects("New_Mobilization_Form", SINCE)):
            self.api.routes[path] = page([])
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"}, definition)
        self.assertEqual(run.steps.get(name="households:Household").status, "disabled")
        self.assertEqual(run.status, "success")
        self.assertNotIn(paths.subjects("Household", SINCE), self.api.calls)

    def test_saves_households_end_to_end(self):
        self.api.routes[paths.subjects("Household", SINCE)] = page([subject_record("a", number="1")])
        for path in (paths.program_encounters("Daily Reporting", SINCE), paths.program_encounters("Family factsheet", SINCE),
                     paths.subjects("New_Mobilization_Form", SINCE)):
            self.api.routes[path] = page([])
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"})
        self.assertEqual((run.status, run.records_ok), ("success", 1))
        self.assertTrue(HouseholdData.objects.filter(household_number="1").exists())


class ManualSyncTests(JobTestCase):
    def test_rhs_sync_subject_types_and_from_date(self):
        self.api.routes[paths.subjects("Structure", SINCE)] = page([subject_record("s", number="5")])
        run = self.run_job("rhs_sync", {"subject_types": ["Structure"], "from_date": "2026-01-01"})
        self.assertEqual([s.name for s in run.steps.all()], ["households:Structure"])
        self.assertEqual(run.records_ok, 1)

    def test_rhs_sync_rejects_unknown_subject_type(self):
        with self.assertRaises(ValueError):
            manual_sync.rhs_sync(reporting.start("rhs_sync"), {"subject_types": ["Toilet"]})

    def test_rhs_sync_defaults_to_both_types(self):
        self.api.routes[paths.subjects("Household", SINCE)] = page([])
        self.api.routes[paths.subjects("Structure", SINCE)] = page([])
        run = self.run_job("rhs_sync", {"from_date": "2026-01-01"})
        self.assertEqual(sorted(s.name for s in run.steps.all()), ["households:Household", "households:Structure"])

    def test_mobilization_all_dates_uses_epoch(self):
        self.api.routes[paths.subjects("New_Mobilization_Form", watermark.EPOCH)] = page([])
        run = self.run_job("mobilization_sync", {"all_dates": True})
        self.assertEqual(run.window_label, "modified since " + watermark.EPOCH)
        self.assertEqual(run.status, "success")

    def test_rim_sync_uses_given_slums_and_toilets_flag(self):
        with mock.patch("avni.sync.rim.slum_location_uuid", return_value=None):
            run = self.run_job("rim_sync", {"slum_ids": [self.slum.id], "include_toilets": False})
        self.assertEqual([s.name for s in run.steps.all()], ["rim"])
        self.assertEqual(run.window_label, "1 slum(s), all dates")

    def test_encounter_sync_one_step_per_type(self):
        for kind in ("Water", "Waste"):
            self.api.routes[paths.encounters(kind, SINCE)] = page([])
        run = self.run_job("encounter_sync", {"encounter_types": ["Water", "Waste"], "from_date": "2026-01-01"})
        self.assertEqual([s.name for s in run.steps.all()], ["encounters:Water", "encounters:Waste"])

    def test_file_import_validates_params(self):
        with self.assertRaises(ValueError):
            manual_sync.file_import(reporting.start("file_import"), {"kind": "nope", "path": "/x"})
        with self.assertRaises(ValueError):
            manual_sync.file_import(reporting.start("file_import"), {"kind": "water"})

    def test_file_import_missing_file_fails_the_step(self):
        run = self.run_job("file_import", {"kind": "water", "path": "/no/such/file.json"})
        step = run.steps.get()
        self.assertEqual(step.status, "failed")
        self.assertIn("FileNotFoundError", step.error)


class RunJobCommandTests(JobTestCase):
    def test_params_reach_the_job(self):
        self.api.routes[paths.subjects("Structure", SINCE)] = page([])
        out = StringIO()
        call_command("run_job", "rhs_sync", "--trigger", "manual", "--no-email",
                     "--params", '{"subject_types": ["Structure"], "from_date": "2026-01-01"}', stdout=out)
        run = JobRun.objects.get(job_key="rhs_sync")
        self.assertEqual([s.name for s in run.steps.all()], ["households:Structure"])
        self.assertEqual(run.trigger, "manual")
        self.assertIn("RUN_ID=", out.getvalue())

    def test_bad_params_rejected_before_running(self):
        with self.assertRaises(CommandError):
            call_command("run_job", "rhs_sync", "--params", "not json", stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("run_job", "rhs_sync", "--params", "[1]", stdout=StringIO())
        self.assertFalse(JobRun.objects.exists())

    def test_every_registry_key_resolves(self):
        for key in registry.known_keys():
            self.assertTrue(callable(registry.resolve(key)), key)
