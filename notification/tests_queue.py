"""JobRequest queue: enqueue/dedupe, claiming, orphan sweep, running."""

from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from notification.models import JobDefinition, JobRequest, JobRun
from notification.services import execute, queue, registry


def fake_job(recorder, params=None):
    from notification.services import reporting

    with recorder.step("work"):
        for number in (params or {}).get("items", []):
            with reporting.record(slum="S", household=number, key=number):
                if number == "bad":
                    reporting.fail(ValueError("bad item"))


def failing_job(recorder, params=None):
    raise RuntimeError("boom")


class QueueTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="data-team")
        self.patch = mock.patch.dict(registry.JOBS, {"fake": "notification.tests_queue:fake_job",
                                                     "failing": "notification.tests_queue:failing_job"})
        self.patch.start()
        self.email = mock.patch("notification.services.queue.job_email.send_activity_report")
        self.send = self.email.start()

    def tearDown(self):
        self.patch.stop()
        self.email.stop()


class EnqueueTests(QueueTestCase):
    def test_creates_queued_request(self):
        request = queue.enqueue("fake", {"items": ["1"]}, self.user)
        self.assertEqual(request.status, "queued")
        self.assertEqual(request.requested_by, self.user)
        self.assertLessEqual(request.scheduled_for, timezone.now())

    def test_dedupe_merges_list_params_into_pending_request(self):
        first = queue.enqueue("fake", {"items": ["1"], "flag": True}, self.user, dedupe_key="fake:today")
        second = queue.enqueue("fake", {"items": ["2", "1"], "flag": False}, self.user, dedupe_key="fake:today")
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.params, {"items": ["1", "2"], "flag": False})
        self.assertEqual(JobRequest.objects.count(), 1)

    def test_dedupe_ignores_finished_requests(self):
        done = queue.enqueue("fake", {}, self.user, dedupe_key="k")
        done.status = "done"
        done.save()
        fresh = queue.enqueue("fake", {}, self.user, dedupe_key="k")
        self.assertNotEqual(done.pk, fresh.pk)

    def test_unknown_job_key_rejected(self):
        with self.assertRaises(registry.JobUnavailable):
            queue.enqueue("nope", {}, self.user)

    def test_pending_for_user(self):
        queue.enqueue("fake", {}, self.user)
        self.assertEqual(queue.pending("fake", self.user).count(), 1)
        self.assertEqual(queue.pending("fake", User.objects.create(username="other")).count(), 0)


class ClaimTests(QueueTestCase):
    def test_claims_oldest_due_request_only(self):
        later = queue.enqueue("fake", {}, self.user, scheduled_for=timezone.now() + timedelta(hours=5))
        second = queue.enqueue("fake", {"n": 2}, self.user)
        first = queue.enqueue("fake", {"n": 1}, self.user)
        JobRequest.objects.filter(pk=first.pk).update(created_on=timezone.now() - timedelta(minutes=5))
        claimed = queue.claim_next()
        self.assertEqual(claimed.pk, first.pk)
        self.assertEqual(claimed.status, "running")
        self.assertEqual(queue.claim_next().pk, second.pk)
        self.assertIsNone(queue.claim_next(), "the future request is not due")
        later.refresh_from_db()
        self.assertEqual(later.status, "queued")

    def test_nothing_to_claim(self):
        self.assertIsNone(queue.claim_next())


class SweepTests(QueueTestCase):
    def test_stale_running_request_is_failed_and_reported(self):
        request = queue.enqueue("fake", {}, self.user)
        JobRequest.objects.filter(pk=request.pk).update(status="running", started_on=timezone.now() - timedelta(hours=9))
        self.assertEqual(queue.sweep_orphans(), 1)
        request.refresh_from_db()
        self.assertEqual(request.status, "failed")
        self.assertIn("restart", request.error)
        self.send.assert_called_once()

    def test_recent_running_request_untouched(self):
        request = queue.enqueue("fake", {}, self.user)
        JobRequest.objects.filter(pk=request.pk).update(status="running", started_on=timezone.now())
        self.assertEqual(queue.sweep_orphans(), 0)


class RunTests(QueueTestCase):
    def test_successful_run_links_job_run_and_emails(self):
        request = queue.claim_next() or queue.enqueue("fake", {"items": ["1", "2"]}, self.user)
        request = queue.claim_next()
        queue.run(request)
        request.refresh_from_db()
        self.assertEqual(request.status, "done")
        self.assertEqual(request.job_run.status, "success")
        self.assertEqual(request.job_run.trigger, "manual")
        self.assertEqual(request.job_run.records_ok, 2)
        self.assertIn("2 ok", request.summary)
        self.send.assert_called_once_with(request, request.job_run)

    def test_partial_run_is_done_with_failure_in_summary(self):
        queue.enqueue("fake", {"items": ["1", "bad"]}, self.user)
        request = queue.claim_next()
        queue.run(request)
        request.refresh_from_db()
        self.assertEqual(request.status, "done")
        self.assertEqual(request.job_run.status, "partial")
        self.assertIn("1 failed", request.summary)

    def test_crashing_job_marks_request_failed(self):
        queue.enqueue("failing", {}, self.user)
        request = queue.claim_next()
        queue.run(request)
        request.refresh_from_db()
        self.assertEqual(request.status, "failed")
        self.assertEqual(request.job_run.status, "crashed")
        self.assertIn("boom", request.error)
        self.send.assert_called_once()

    def test_email_failure_never_breaks_the_run(self):
        self.send.side_effect = RuntimeError("smtp down")
        queue.enqueue("fake", {}, self.user)
        request = queue.claim_next()
        queue.run(request)
        request.refresh_from_db()
        self.assertEqual(request.status, "done")

    def test_definition_created_on_first_run_and_inactive_definition_skips(self):
        queue.enqueue("fake", {}, self.user)
        queue.run(queue.claim_next())
        definition = JobDefinition.objects.get(key="fake")
        definition.is_active = False
        definition.save()
        queue.enqueue("fake", {}, self.user)
        request = queue.claim_next()
        queue.run(request)
        request.refresh_from_db()
        self.assertEqual(request.status, "cancelled")
        self.assertIn("switched off", request.error)


class ExecuteTests(QueueTestCase):
    def test_execute_returns_finished_run(self):
        run = execute.execute("fake", trigger="cron", params={"items": ["1"]})
        self.assertEqual((run.status, run.records_ok), ("success", 1))
        self.assertTrue(JobRun.objects.filter(pk=run.pk).exists())

    def test_execute_unknown_key_is_failed_run(self):
        run = execute.execute("nope", trigger="cron")
        self.assertEqual(run.status, "failed")
        self.assertIn("Unknown job", run.error)

    def test_execute_crash_is_crashed_run(self):
        run = execute.execute("failing", trigger="cron")
        self.assertEqual(run.status, "crashed")
        self.assertIn("boom", run.error)


@override_settings(DEBUG=False, JOB_NOTIFY_FALLBACK_EMAILS=["team@shelter-associates.org"])
class DigestQueueHealthTests(QueueTestCase):
    """The daily digest covers manual runs and the queue's health."""

    def digest_body(self):
        from django.core import mail
        from notification.services import email as job_email

        runs = list(JobRun.objects.all())
        job_email.send_digest(runs, [], timezone.now() - timedelta(days=1), timezone.now())
        return mail.outbox[-1].alternatives[0][0]

    def test_manual_runs_show_requester_and_params(self):
        queue.enqueue("fake", {"items": ["1"], "from_date": "2026-01-01"}, self.user)
        queue.run(queue.claim_next())
        body = self.digest_body()
        self.assertIn("data-team", body)
        self.assertIn("2026-01-01", body)
        self.assertIn("Requested by", body)

    def test_stuck_queue_is_flagged(self):
        request = queue.enqueue("fake", {}, self.user)
        JobRequest.objects.filter(pk=request.pk).update(scheduled_for=timezone.now() - timedelta(hours=3))
        body = self.digest_body()
        self.assertIn("JOB_QUEUE_RUNNER", body)
        self.assertIn("#{}".format(request.pk), body)

    def test_failed_requests_without_a_run_are_listed(self):
        request = queue.enqueue("fake", {}, self.user)
        JobRequest.objects.filter(pk=request.pk).update(status="failed", error=queue.ORPHAN_MESSAGE, finished_on=timezone.now())
        body = self.digest_body()
        self.assertIn("Stopped unexpectedly", body)

    def test_healthy_queue_has_no_queue_section(self):
        body = self.digest_body()
        self.assertNotIn("Queue problems", body)
