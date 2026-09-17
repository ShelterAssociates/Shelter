"""Registry jobs run through the real recorder against a fake AVNI."""

from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase

from avni import paths, window
from avni.client import reset_client, use_client
from avni.jobs import daily_sync, manual_sync
from avni.tests.support import FakeApi, encounter_record, make_city, make_slum, page, program_encounter_record, subject_record
from graphs.models import HouseholdData
from notification.models import JobDefinition, JobRun, JobStepConfig
from notification.services import registry, reporting
from survey import connector
from survey.models import Record, SyncSwitch

SINCE = "2026-01-01T00:00:00.000Z"
NIGHTLY_LISTINGS = (
    paths.subjects("Household", SINCE), paths.subjects("Structure", SINCE),
    paths.subjects("Detailed Socio Economic Survey", SINCE),
    paths.program_encounters("Daily Reporting", SINCE), paths.program_encounters("Family factsheet", SINCE),
    paths.subjects("New_Mobilization_Form", SINCE),
)
NIGHTLY_STEPS = [name for name, _, _, _ in daily_sync.STEPS]


class JobTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.api = FakeApi()
        use_client(self.api)
        connector.reset_provider()

    def tearDown(self):
        reset_client()
        connector.reset_provider()

    def switch(self, subject_type="Household", kind="subject", program="", encounter_type="", enabled=True):
        return SyncSwitch.objects.create(
            provider="avni", subject_type=subject_type, kind=kind, program=program,
            encounter_type=encounter_type, is_enabled=enabled,
        )

    def empty_nightly_listings(self, *skip):
        for path in NIGHTLY_LISTINGS:
            if path not in skip:
                self.api.routes[path] = page([])

    def run_job(self, key, params=None, definition=None):
        recorder = reporting.start(key, trigger="manual", definition=definition)
        registry.resolve(key)(recorder, params)
        return recorder.finish()


class DailySyncTests(JobTestCase):
    def test_every_step_runs_even_when_one_cannot_list(self):
        self.empty_nightly_listings(paths.subjects("Household", SINCE))
        # households listing is missing -> AvniError inside step 1
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"})
        names = list(run.steps.order_by("order").values_list("name", "status"))
        self.assertEqual([name for name, _ in names], NIGHTLY_STEPS)
        self.assertEqual(NIGHTLY_STEPS, [
            "households:Household", "households:Structure", "households:Detailed Socio Economic Survey",
            "daily_reporting", "family_factsheets", "mobilization", "household_encounters", "members",
        ])
        self.assertEqual(dict(names)["households:Household"], "failed")
        self.assertEqual(dict(names)["daily_reporting"], "success")
        self.assertEqual(dict(names)["household_encounters"], "success", "an empty catalog is a warning, not a failure")
        self.assertIn("AvniError", run.steps.get(name="households:Household").error)
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.window_label, "modified since 2026-01-01T00:00:00.000Z")

    def test_first_run_without_from_date_asks_from_2018_per_step(self):
        first = window.FIRST_SYNC_START
        for path in NIGHTLY_LISTINGS:
            self.api.routes[path.replace(paths.quote(SINCE, safe=""), paths.quote(first, safe=""))] = page([])
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync")
        self.assertEqual(run.window_label, "per-step window (see steps)")
        self.assertEqual(run.steps.get(name="households:Household").extras["window_start"], first)
        self.assertEqual(run.steps.get(name="daily_reporting").extras["window_start"], first)
        self.assertIn(paths.program_encounters("Daily Reporting", first), self.api.calls)

    def test_disabled_step_is_skipped(self):
        definition = JobDefinition.objects.create(key="avni_daily_sync", display_name="d")
        JobStepConfig.objects.create(job=definition, step_name="households:Household", is_enabled=False)
        self.empty_nightly_listings()
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"}, definition)
        self.assertEqual(run.steps.get(name="households:Household").status, "disabled")
        self.assertEqual(run.status, "success")
        self.assertNotIn(paths.subjects("Household", SINCE), self.api.calls)

    def test_a_switched_off_subject_type_records_its_steps_disabled(self):
        self.switch("Structure", enabled=False)
        self.switch("Household")
        self.switch("Household", kind="program_encounter", program="Sanitation program",
                    encounter_type="Daily Reporting", enabled=False)
        self.empty_nightly_listings()
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"})
        statuses = dict(run.steps.values_list("name", "status"))
        self.assertEqual(statuses["households:Structure"], "disabled")
        self.assertEqual(statuses["daily_reporting"], "disabled")
        self.assertEqual(statuses["households:Household"], "success")
        self.assertNotIn(paths.subjects("Structure", SINCE), self.api.calls)
        self.assertNotIn(paths.program_encounters("Daily Reporting", SINCE), self.api.calls)

    def test_household_encounters_step_runs_every_enabled_kind(self):
        self.switch("Household", kind="encounter", encounter_type="Water")
        self.switch("Household", kind="encounter", encounter_type="Waste", enabled=False)
        self.switch("Detailed Socio Economic Survey", kind="encounter", encounter_type="Water INP")
        self.switch("Household", kind="program_encounter", program="Sanitation program", encounter_type="Daily Reporting")
        self.empty_nightly_listings()
        self.api.routes[paths.encounters("Water", SINCE)] = page([encounter_record("e1", "Water")])
        self.api.routes[paths.encounters("Water INP", SINCE)] = page([])
        self.api.routes[paths.subject("sub-1")] = subject_record()
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"})
        step = run.steps.get(name="household_encounters")
        self.assertEqual(step.status, "success")
        self.assertEqual(step.extras["kinds"], "2")
        self.assertNotIn(paths.encounters("Waste", SINCE), self.api.calls)
        self.assertEqual(Record.objects.get(external_id="e1").encounter_type, "Water")
        self.assertIn("Last_modified_date", HouseholdData.objects.get().rhs_data)

    def test_saves_households_end_to_end(self):
        self.api.routes[paths.subjects("Household", SINCE)] = page([subject_record("a", number="1")])
        self.empty_nightly_listings(paths.subjects("Household", SINCE))
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"})
        self.assertEqual((run.status, run.records_ok), ("success", 1))
        self.assertTrue(HouseholdData.objects.filter(household_number="1").exists())
        self.assertEqual(Record.objects.get(external_id="a").household, HouseholdData.objects.get())

    def test_dses_registrations_land_on_household_keys(self):
        dses = subject_record("d", number="7", subject_type="Detailed Socio Economic Survey",
                              observations={"Ownership status of the house": "Own house"})
        self.api.routes[paths.subjects("Detailed Socio Economic Survey", SINCE)] = page([dses])
        self.empty_nightly_listings(paths.subjects("Detailed Socio Economic Survey", SINCE))
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"})
        self.assertEqual(run.steps.get(name="households:Detailed Socio Economic Survey").records_ok, 1)
        self.assertEqual(HouseholdData.objects.get(household_number="7").rhs_data["group_el9cl08/Ownership_status_of_the_house"], "Own house")


class ManualSyncTests(JobTestCase):
    def test_rhs_sync_subject_types_and_from_date(self):
        self.api.routes[paths.subjects("Structure", SINCE)] = page([subject_record("s", number="5", subject_type="Structure")])
        run = self.run_job("rhs_sync", {"subject_types": ["Structure"], "from_date": "2026-01-01"})
        self.assertEqual([s.name for s in run.steps.all()], ["households:Structure"])
        self.assertEqual(run.records_ok, 1)

    def test_rhs_sync_rejects_unknown_subject_type(self):
        with self.assertRaises(ValueError):
            manual_sync.rhs_sync(reporting.start("rhs_sync"), {"subject_types": ["Toilet"]})

    def test_rhs_sync_defaults_to_every_household_type(self):
        for subject_type in manual_sync.HOUSEHOLD_SUBJECT_TYPES:
            self.api.routes[paths.subjects(subject_type, SINCE)] = page([])
        run = self.run_job("rhs_sync", {"from_date": "2026-01-01"})
        self.assertEqual(sorted(s.name for s in run.steps.all()),
                         ["households:Detailed Socio Economic Survey", "households:Household", "households:Structure"])

    def test_rhs_sync_refuses_a_switched_off_type(self):
        self.switch("Structure", enabled=False)
        with self.assertRaises(ValueError) as caught:
            manual_sync.rhs_sync(reporting.start("rhs_sync"), {"subject_types": ["Structure"]})
        self.assertIn("switched off", str(caught.exception))

    def test_encounter_sync_refuses_a_switched_off_type(self):
        self.switch("Household", kind="encounter", encounter_type="Water", enabled=False)
        with self.assertRaises(ValueError):
            manual_sync.encounter_sync(reporting.start("encounter_sync"), {"encounter_types": ["Water"]})

    def test_household_encounter_sync_one_step_per_enabled_kind(self):
        self.switch("Household", kind="encounter", encounter_type="Water")
        self.switch("Household", kind="encounter", encounter_type="Waste")
        self.switch("Household", kind="enrolment", program="Sanitation program")
        for path in (paths.encounters("Water", SINCE), paths.encounters("Waste", SINCE)):
            self.api.routes[path] = page([])
        run = self.run_job("household_encounter_sync", {"from_date": "2026-01-01"})
        self.assertEqual(sorted(s.name for s in run.steps.all()), ["encounters:Waste", "encounters:Water"],
                         "AVNI cannot list enrolments; they arrive with their program encounters")
        self.assertEqual(run.status, "success")

    def test_a_program_encounter_brings_its_enrolment_along(self):
        self.switch("Household", kind="program_encounter", program="Sanitation program", encounter_type="Survey")
        self.api.routes[paths.program_encounters("Survey", SINCE)] = page([
            program_encounter_record("p1", "Survey", observations={"a": 1}),
            program_encounter_record("p2", "Survey", observations={"a": 2}),
        ])
        self.api.routes[paths.subject("sub-1")] = subject_record()
        self.api.routes[paths.program_enrolment("enr-1")] = {
            "ID": "enr-1", "Subject ID": "sub-1", "Subject type": "Household", "Program": "Sanitation program",
            "Enrolment datetime": "2026-01-05T00:00:00.000Z", "observations": {"Reason": "x"},
            "audit": {"Created at": "2026-01-05T00:00:00.000Z", "Last modified at": "2026-01-05T00:00:00.000Z"},
        }
        run = self.run_job("household_encounter_sync", {"from_date": "2026-01-01"})
        self.assertEqual(run.status, "success")
        enrolment = Record.objects.get(kind="enrolment")
        self.assertEqual((enrolment.external_id, enrolment.program, enrolment.household_number), ("enr-1", "Sanitation program", "42"))
        self.assertEqual(self.api.calls.count(paths.program_enrolment("enr-1")), 1, "fetched once for two encounters")
        self.assertEqual(run.steps.get().records_ok, 2, "the enrolment adds no step record of its own")

    def test_household_encounter_sync_can_be_limited_to_types(self):
        self.switch("Household", kind="encounter", encounter_type="Water")
        self.switch("Household", kind="encounter", encounter_type="Waste")
        self.api.routes[paths.encounters("Water", SINCE)] = page([])
        run = self.run_job("household_encounter_sync", {"from_date": "2026-01-01", "encounter_types": ["Water"]})
        self.assertEqual([s.name for s in run.steps.all()], ["encounters:Water"])

    def test_household_encounter_sync_rejects_unknown_disabled_or_empty(self):
        self.switch("Household", kind="encounter", encounter_type="Water")
        self.switch("Household", kind="encounter", encounter_type="Waste", enabled=False)
        recorder = reporting.start("household_encounter_sync")
        with self.assertRaises(ValueError):
            manual_sync.household_encounter_sync(recorder, {"encounter_types": ["Nope"]})
        with self.assertRaises(ValueError):
            manual_sync.household_encounter_sync(recorder, {"encounter_types": ["Waste"]})
        with self.assertRaises(ValueError):
            manual_sync.household_encounter_sync(recorder, {"subject_types": ["Toilet"]})
        SyncSwitch.objects.all().delete()
        with self.assertRaises(ValueError):
            manual_sync.household_encounter_sync(recorder, {})

    def test_member_sync_needs_its_switch_on(self):
        with self.assertRaises(ValueError):
            manual_sync.member_sync(reporting.start("member_sync"), {})
        self.switch("Family Member")
        self.switch("Family Member", kind="enrolment", program="MHM")
        self.api.routes[paths.subjects("Family Member", SINCE)] = page([])
        run = self.run_job("member_sync", {"from_date": "2026-01-01"})
        self.assertEqual([s.name for s in run.steps.all()], ["members"])
        self.assertEqual(run.status, "success")

    def test_subject_sync_walks_each_subject_and_notes_totals(self):
        subject = subject_record()
        subject["encounters"] = ["enc-1", "enc-2"]
        scheduled = encounter_record("enc-2", "Water", observations={})
        scheduled["Encounter date time"] = None
        self.api.routes[paths.subject("sub-1")] = subject
        self.api.routes[paths.encounter("enc-1")] = encounter_record("enc-1", "Water")
        self.api.routes[paths.encounter("enc-2")] = scheduled
        run = self.run_job("subject_sync", {"subject_ids": ["sub-1", "sub-1", " ", "ghost"]})
        step = run.steps.get(name="subjects")
        self.assertEqual(run.window_label, "2 subject(s)")
        self.assertEqual((step.records_ok, step.records_failed, step.records_skipped), (2, 1, 1))
        self.assertIn("created 1", step.extras["subject"])
        self.assertIn("scheduled_only 1", step.extras["encounter"])
        self.assertEqual(Record.objects.filter(kind="encounter").count(), 1)
        self.assertTrue(HouseholdData.objects.filter(household_number="42").exists())

    def test_subject_sync_needs_ids(self):
        with self.assertRaises(ValueError):
            manual_sync.subject_sync(reporting.start("subject_sync"), {})

    def test_mobilization_all_dates_uses_epoch(self):
        self.api.routes[paths.subjects("New_Mobilization_Form", window.EPOCH)] = page([])
        run = self.run_job("mobilization_sync", {"all_dates": True})
        self.assertEqual(run.window_label, "modified since " + window.EPOCH)
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


class MoreManualSyncTests(JobTestCase):
    def test_family_factsheet_and_daily_reporting_refuse_when_switched_off(self):
        self.switch("Household", kind="program_encounter", program="P", encounter_type="Family factsheet", enabled=False)
        self.switch("Household", kind="program_encounter", program="P", encounter_type="Daily Reporting", enabled=False)
        with self.assertRaises(ValueError):
            manual_sync.family_factsheet_sync(reporting.start("family_factsheet_sync"), {})
        with self.assertRaises(ValueError):
            manual_sync.daily_reporting_sync(reporting.start("daily_reporting_sync"), {})

    def test_rim_sync_runs_toilets_by_default(self):
        with mock.patch("avni.sync.rim.slum_location_uuid", return_value=None):
            run = self.run_job("rim_sync", {"slum_ids": [self.slum.id]})
        self.assertEqual([s.name for s in run.steps.all()], ["rim", "toilets"])

    def test_the_members_nightly_step_runs_every_member_kind(self):
        self.switch("Family Member")
        self.switch("Family Member", kind="program_encounter", program="MHM", encounter_type="Follow up")
        self.empty_nightly_listings()
        self.api.routes[paths.subjects("Family Member", SINCE)] = page([])
        self.api.routes[paths.program_encounters("Follow up", SINCE)] = page([])
        with mock.patch("avni.jobs.daily_sync.time.sleep"):
            run = self.run_job("avni_daily_sync", {"from_date": "2026-01-01"})
        self.assertEqual(run.steps.get(name="members").extras["kinds"], "2")

    def test_form_cache_refresh_honours_disabled_steps(self):
        definition = JobDefinition.objects.create(key="avni_form_cache_refresh", display_name="d")
        JobStepConfig.objects.create(job=definition, step_name="form_cache_refresh", is_enabled=False)
        JobStepConfig.objects.create(job=definition, step_name="survey_catalog", is_enabled=False)
        run = self.run_job("avni_form_cache_refresh", None, definition)
        self.assertEqual(set(run.steps.values_list("status", flat=True)), {"disabled"})


class ResumeHelperTests(JobTestCase):
    def test_processed_and_failed_keys_tolerate_missing_or_odd_extras(self):
        from avni.jobs import resume as resuming

        run = JobRun.objects.create(job_key="rhs_sync", status="failed")
        run.steps.create(name="s", order=0, status="failed", extras={"processed": "many"})
        resume = resuming.from_params({"resume_run": run.pk})
        self.assertEqual(resuming.processed(resume, "s"), 0)
        self.assertEqual(resuming.failed_keys(resume, "missing"), [])
        self.assertIsNone(resuming.checkpoint(resume, "missing"))
        self.assertIsNone(resuming.from_params({}))


class ProgramEncounterJobTests(JobTestCase):
    def test_family_factsheet_and_daily_reporting_jobs_run(self):
        self.api.routes[paths.program_encounters("Family factsheet", SINCE)] = page([])
        self.api.routes[paths.program_encounters("Daily Reporting", SINCE)] = page([])
        for key, step in (("family_factsheet_sync", "family_factsheets"), ("daily_reporting_sync", "daily_reporting")):
            run = self.run_job(key, {"from_date": "2026-01-01"})
            self.assertEqual([s.name for s in run.steps.all()], [step])
            self.assertEqual(run.status, "success")
