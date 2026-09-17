"""Retries: transient AVNI errors retried in the provider; stopped runs resumed
from their checkpoint; the console's retry button."""

import json

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from requests import ConnectionError as RequestsConnectionError

from avni import paths, provider as avni_provider
from avni.client import AvniError, reset_client, use_client
from avni.jobs import manual_sync, resume as resuming
from avni.provider import AvniProvider
from avni.tests.support import FakeApi, encounter_record, make_city, make_slum, page, subject_record
from graphs.models import HouseholdData
from notification.models import JobRequest, JobRun
from notification.services import registry, reporting
from survey import connector
from survey.models import Record

SINCE = "2026-01-01T00:00:00.000Z"


class FlakyApi(FakeApi):
    """Fails the first `failures` calls to `flaky_path` before answering."""

    def __init__(self, routes, flaky_path, failures, error):
        super(FlakyApi, self).__init__(routes)
        self.flaky_path = flaky_path
        self.failures = failures
        self.error = error

    def get_json(self, path, timeout=None):
        if path == self.flaky_path and self.failures > 0:
            self.failures -= 1
            self.calls.append(path)
            raise self.error
        return super(FlakyApi, self).get_json(path, timeout)


class TransientRetryTests(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city())
        self.sleeps = []
        self._sleep = avni_provider.sleep
        avni_provider.sleep = self.sleeps.append
        self.addCleanup(setattr, avni_provider, "sleep", self._sleep)

    def test_a_503_is_retried_and_then_succeeds(self):
        api = FlakyApi({paths.subject("sub-1"): subject_record()}, paths.subject("sub-1"), 2,
                       AvniError(503, "x", "busy"))
        record = AvniProvider(api=api).get_subject("sub-1")
        self.assertEqual(record["ID"], "sub-1")
        self.assertEqual(self.sleeps, [5, 10], "pauses grow with each attempt")

    def test_a_connection_error_is_retried(self):
        api = FlakyApi({paths.subject("sub-1"): subject_record()}, paths.subject("sub-1"), 1,
                       RequestsConnectionError("reset"))
        self.assertEqual(AvniProvider(api=api).get_subject("sub-1")["ID"], "sub-1")

    def test_a_404_is_not_retried(self):
        api = FlakyApi({}, paths.subject("sub-1"), 5, AvniError(404, "x", "gone"))
        with self.assertRaises(AvniError):
            AvniProvider(api=api).get_subject("sub-1")
        self.assertEqual(self.sleeps, [])

    def test_a_persistent_failure_gives_up_after_the_attempts(self):
        api = FlakyApi({}, paths.subject("sub-1"), 99, AvniError(502, "x", "bad gateway"))
        with self.assertRaises(AvniError):
            AvniProvider(api=api).get_subject("sub-1")
        self.assertEqual(len(self.sleeps), avni_provider.RETRY_ATTEMPTS - 1)

    def test_a_listing_page_is_retried_too(self):
        path = paths.subjects("Household", SINCE)
        first = page([subject_record("a", number="1")], total_pages=2)
        second = page([subject_record("b", number="2")])
        api = FlakyApi({path: [first, second]}, path + "&page=1", 1, AvniError(500, "x", "oops"))
        ids = [r["ID"] for r in AvniProvider(api=api).iter_records("subject", "Household", since=SINCE)]
        self.assertEqual(ids, ["a", "b"])


class ResumeTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.api = FakeApi()
        use_client(self.api)
        connector.reset_provider()
        self.addCleanup(reset_client)
        self.addCleanup(connector.reset_provider)

    def run_job(self, key, params=None):
        recorder = reporting.start(key, trigger="manual")
        registry.resolve(key)(recorder, params)
        return recorder.finish()


class CheckpointTests(ResumeTestCase):
    def test_a_listing_step_notes_its_checkpoint_and_count(self):
        self.api.routes[paths.subjects("Household", SINCE)] = page([
            subject_record("a", number="1", modified="2026-02-01T00:00:00.000Z"),
            subject_record("b", number="2", modified="2026-02-02T00:00:00.000Z"),
        ])
        run = self.run_job("rhs_sync", {"subject_types": ["Household"], "from_date": "2026-01-01"})
        extras = run.steps.get().extras
        self.assertEqual(extras["checkpoint"], "2026-02-02T00:00:00.000Z")
        self.assertEqual(extras["processed"], "2")

    def test_the_checkpoint_survives_a_crash_mid_step(self):
        path = paths.subjects("Household", SINCE)
        self.api.routes[path] = page([subject_record("a", number="1", modified="2026-02-01T00:00:00.000Z")], total_pages=2)
        self.api.routes[path + "&page=1"] = AvniError(500, path, "boom")
        original = avni_provider.sleep
        avni_provider.sleep = lambda seconds: None
        try:
            run = self.run_job("rhs_sync", {"subject_types": ["Household"], "from_date": "2026-01-01"})
        finally:
            avni_provider.sleep = original
        step = run.steps.get()
        self.assertEqual(step.status, "partial", "one record was saved before the crash")
        self.assertIn("AvniError", step.error)
        self.assertEqual(step.extras["checkpoint"], "2026-02-01T00:00:00.000Z")
        self.assertEqual(step.records_ok, 1)
        self.assertEqual(run.status, "partial")

    def test_failed_records_keep_their_key(self):
        self.api.routes[paths.subjects("Household", SINCE)] = page([subject_record("bad", number="1", slum="Nowhere")])
        run = self.run_job("rhs_sync", {"subject_types": ["Household"], "from_date": "2026-01-01"})
        self.assertEqual(run.steps.get().sample_failures[0]["key"], "bad")


class ResumeRunTests(ResumeTestCase):
    def stopped_run(self):
        """A rhs_sync run whose Household step stopped after one record and whose Structure step never ran."""
        run = JobRun.objects.create(job_key="rhs_sync", status="failed")
        run.steps.create(name="households:Household", order=0, status="failed",
                         extras={"checkpoint": "2026-02-01T00:00:00.000Z", "processed": "1"})
        return run

    def test_resume_starts_each_step_from_its_checkpoint(self):
        stopped = self.stopped_run()
        resumed_path = paths.subjects("Household", "2026-02-01T00:00:00.000Z")
        self.api.routes[resumed_path] = page([subject_record("b", number="2")])
        self.api.routes[paths.subjects("Structure", SINCE)] = page([])
        run = self.run_job("rhs_sync", {"subject_types": ["Household", "Structure"], "from_date": "2026-01-01",
                                        "resume_run": stopped.pk})
        self.assertEqual(run.status, "success")
        self.assertIn(resumed_path, self.api.calls, "the Household step starts at the checkpoint")
        self.assertIn(paths.subjects("Structure", SINCE), self.api.calls, "a step with no earlier record uses the original window")
        self.assertEqual(run.steps.get(name="households:Household").extras["resumed_from"], "2026-02-01T00:00:00.000Z")
        self.assertTrue(HouseholdData.objects.filter(household_number="2").exists())

    def test_steps_that_already_succeeded_are_skipped(self):
        stopped = JobRun.objects.create(job_key="encounter_sync", status="partial")
        stopped.steps.create(name="encounters:Water", order=0, status="success", extras={"checkpoint": "x"})
        stopped.steps.create(name="encounters:Waste", order=1, status="failed", extras={})
        self.api.routes[paths.encounters("Waste", SINCE)] = page([])
        run = self.run_job("encounter_sync", {"encounter_types": ["Water", "Waste"], "from_date": "2026-01-01",
                                              "resume_run": stopped.pk})
        self.assertNotIn(paths.encounters("Water", SINCE), self.api.calls)
        self.assertIn("already done in run #{}".format(stopped.pk), run.steps.get(name="encounters:Water").extras["resumed"])
        self.assertEqual(run.status, "success")

    def test_an_unknown_run_id_is_refused(self):
        with self.assertRaises(ValueError):
            manual_sync.rhs_sync(reporting.start("rhs_sync"), {"subject_types": ["Household"], "resume_run": 999999})

    def test_subject_sync_redoes_failed_subjects_and_the_rest(self):
        stopped = JobRun.objects.create(job_key="subject_sync", status="partial")
        stopped.steps.create(name="subjects", order=0, status="partial", extras={"processed": "2"},
                             sample_failures=[{"key": "s2", "reason": "boom"}])
        for uuid in ("s2", "s3", "s4"):
            self.api.routes[paths.subject(uuid)] = subject_record(uuid, number=uuid[1:])
        run = self.run_job("subject_sync", {"subject_ids": ["s1", "s2", "s3", "s4"], "resume_run": stopped.pk})
        self.assertEqual(run.window_label, "3 subject(s), resuming run #{}".format(stopped.pk))
        self.assertNotIn(paths.subject("s1"), self.api.calls, "s1 was done in the earlier run")
        self.assertEqual(sorted(Record.objects.values_list("external_id", flat=True)), ["s2", "s3", "s4"])
        self.assertEqual(run.steps.get().extras["processed"], "3")

    def test_which_runs_can_be_resumed(self):
        self.assertTrue(resuming.can_resume(JobRun(job_key="rhs_sync", status="failed")))
        self.assertTrue(resuming.can_resume(JobRun(job_key="subject_sync", status="crashed")))
        self.assertFalse(resuming.can_resume(JobRun(job_key="rhs_sync", status="success")))
        self.assertFalse(resuming.can_resume(JobRun(job_key="rim_sync", status="failed")))
        self.assertFalse(resuming.can_resume(None))


@override_settings(AVNI_SYNC_GROUPS=["Data Team"])
class ConsoleRetryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("sync", password="x")
        self.user.groups.add(Group.objects.create(name="Data Team"))
        self.client.force_login(self.user)

    def request_with_run(self, status="failed", job_key="rhs_sync", user=None):
        run = JobRun.objects.create(job_key=job_key, status=status)
        return JobRequest.objects.create(job_key=job_key, params={"from_date": "2026-01-01"},
                                         requested_by=user or self.user, status="failed", job_run=run)

    def test_the_button_shows_only_for_stopped_sync_runs(self):
        stopped = self.request_with_run()
        self.assertContains(self.client.get(reverse("avni_console:run_detail", args=[stopped.pk])), "Retry from where it stopped")
        finished = self.request_with_run(status="success")
        self.assertNotContains(self.client.get(reverse("avni_console:run_detail", args=[finished.pk])), "Retry from where it stopped")

    def test_retry_queues_the_same_job_with_resume_run(self):
        stopped = self.request_with_run()
        response = self.client.post(reverse("avni_console:run_retry", args=[stopped.pk]), "{}", content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        retry = JobRequest.objects.exclude(pk=stopped.pk).get()
        self.assertEqual(retry.job_key, "rhs_sync")
        self.assertEqual(retry.params, {"from_date": "2026-01-01", "resume_run": stopped.job_run.pk})
        self.assertEqual(retry.status, "queued")
        self.assertIn("resumes from where run #", json.loads(response.content.decode())["message"])
        self.assertEqual(self.client.post(reverse("avni_console:run_retry", args=[stopped.pk]), "{}",
                                          content_type="application/json").status_code, 409)

    def test_a_finished_run_cannot_be_retried(self):
        finished = self.request_with_run(status="success")
        response = self.client.post(reverse("avni_console:run_retry", args=[finished.pk]), "{}", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_someone_elses_run_is_404(self):
        other = User.objects.create_user("other", password="x")
        theirs = self.request_with_run(user=other)
        self.assertEqual(self.client.post(reverse("avni_console:run_retry", args=[theirs.pk]), "{}",
                                          content_type="application/json").status_code, 404)
