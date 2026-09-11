import logging
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest import mock

from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from notification.models import (
    DAY_KEYS,
    EmailContact,
    EmailPurpose,
    EmailRecipient,
    JobDefinition,
    JobRun,
)
from notification.services import contacts, reporting


class NoRunTests(SimpleTestCase):
    def test_helpers_are_noops_without_a_run(self):
        reporting.fail(ValueError("x"))
        reporting.expect(5)
        reporting.skip()
        with reporting.record(slum="a", household="1") as item:
            self.assertIsNone(item)


class FakeStep(object):
    def __init__(self):
        self.errors = []

    def note_error(self, message):
        self.errors.append(message)


class ErrorCaptureTests(SimpleTestCase):
    def test_malformed_logger_call_does_not_raise(self):
        step = FakeStep()
        handler = reporting._ErrorCapture(step)
        log = logging.getLogger("notification.tests.malformed")
        log.addHandler(handler)
        try:
            log.error(ValueError("boom"), "0042")
        finally:
            log.removeHandler(handler)
        self.assertEqual(len(step.errors), 1)
        self.assertIn("boom", step.errors[0])

    def test_error_inside_record_marks_record(self):
        step = FakeStep()
        handler = reporting._ErrorCapture(step)
        item = reporting._Record("slum", "hh", None)
        reporting._state.record = item
        try:
            handler.emit(logging.LogRecord("x", logging.ERROR, "", 0, "bad %s", ("y",), None))
        finally:
            reporting._state.record = None
        self.assertTrue(item.failed)
        self.assertEqual(item.reason, "bad y")
        self.assertEqual(step.errors, [])


class DetailWriterTests(SimpleTestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_creates_directory_and_writes_lines(self):
        path = os.path.join(self.dir, "run", "job.txt")
        writer = reporting._DetailWriter(path)
        writer.line("OK", "step", "Pune", "Ganesh Nagar", "0412")
        writer.line("FAIL", "step", "Thane", "Kisan", "0087", "KeyError: 'x'")
        writer.close()
        with open(path) as handle:
            content = handle.read()
        self.assertIn("OK", content)
        self.assertIn("KeyError", content)

    def test_unwritable_path_is_silent(self):
        writer = reporting._DetailWriter("/proc/definitely/not/writable.txt")
        writer.line("OK", "s", "c", "sl", "hh")
        writer.close()


class ScheduleParsingTests(SimpleTestCase):
    def test_times_and_days(self):
        d = JobDefinition(expected_times="02:00, 23:15,bad", expected_days="mon,Wed")
        self.assertEqual(d.expected_time_list(), [(2, 0), (23, 15)])
        self.assertEqual(d.expected_day_set(), {"mon", "wed"})
        self.assertEqual(JobDefinition(expected_days="*").expected_day_set(), set(DAY_KEYS))

    def test_month_days(self):
        d = JobDefinition(expected_days_of_month="1, 16,x")
        self.assertEqual(d.expected_month_day_set(), {1, 16})
        self.assertEqual(JobDefinition().expected_month_day_set(), set())


@override_settings(DEBUG=False)
class RecorderDbTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def test_full_run_rolls_up_counts_and_cities(self):
        recorder = reporting.start("unit", trigger="manual")
        with recorder.step("s1", loggers=["notification.tests.run"]) as step:
            step.expect(4)
            with reporting.record(city="Pune", household="1"):
                pass
            with reporting.record(city="Pune", household="2"):
                reporting.fail(KeyError("k"))
            with reporting.record(city="Thane", household="3"):
                logging.getLogger("notification.tests.run").error("swallowed %s", "err")
            step.skip(reason="voided")
        run = recorder.finish()

        self.assertEqual(run.status, "partial")
        self.assertEqual((run.records_total, run.records_ok, run.records_failed), (3, 1, 2))
        step_model = run.steps.get()
        self.assertEqual(step_model.records_skipped, 2)
        stats = {c.city_name: (c.records_ok, c.records_failed) for c in step_model.city_stats.all()}
        self.assertEqual(stats, {"Pune": (1, 1), "Thane": (0, 1)})
        self.assertEqual(len(step_model.sample_failures), 2)
        self.assertTrue(os.path.exists(run.detail_file_path))
        self.assertIn("job_reports", run.detail_file_path)

    def test_exception_propagates_and_step_fails(self):
        recorder = reporting.start("unit2", trigger="manual")
        with self.assertRaises(RuntimeError):
            with recorder.step("boom"):
                with reporting.record(city="Pune", household="1"):
                    raise RuntimeError("bad")
        run = recorder.finish(status="failed", error="bad")
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.steps.get().status, "failed")
        self.assertIsNone(reporting.active_run())


class ContactsTests(TestCase):
    def test_resolves_active_rows_by_kind(self):
        purpose = EmailPurpose.objects.create(key="p", display_name="P")
        a = EmailContact.objects.create(name="A", email="a@example.org")
        b = EmailContact.objects.create(name="B", email="b@example.org")
        c = EmailContact.objects.create(name="C", email="c@example.org", is_active=False)
        EmailRecipient.objects.create(purpose=purpose, contact=a, kind="to")
        EmailRecipient.objects.create(purpose=purpose, contact=b, kind="cc")
        EmailRecipient.objects.create(purpose=purpose, contact=c, kind="to")
        self.assertEqual(contacts.recipients_for("p"), (["a@example.org"], ["b@example.org"], []))

    @override_settings(KML_CHANGE_NOTIFY_EMAILS=["fb@example.org"])
    def test_settings_fallback_when_empty(self):
        self.assertEqual(contacts.recipients_for("kml_change")[0], ["fb@example.org"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class DevRedirectTests(TestCase):
    def setUp(self):
        from helpers.services.send_email import send_email

        self.send_email = send_email
        real = EmailPurpose.objects.create(key="p", display_name="P")
        r = EmailContact.objects.create(name="R", email="real@example.org")
        EmailRecipient.objects.create(purpose=real, contact=r, kind="to")

    @override_settings(DEBUG=True)
    def test_debug_redirects_to_dev_only(self):
        dev = EmailPurpose.objects.create(key="dev_redirect", display_name="Dev")
        d = EmailContact.objects.create(name="Dev", email="dev@example.org")
        EmailRecipient.objects.create(purpose=dev, contact=d, kind="to")
        self.send_email(["real@example.org"], "Hello", None, None, "plain", cc=["cc@example.org"])
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["dev@example.org"])
        self.assertEqual(msg.cc, [])
        self.assertTrue(msg.subject.startswith("[DEV] "))
        self.assertIn("real@example.org", msg.body)
        self.assertIn("cc@example.org", msg.alternatives[0][0])

    @override_settings(DEBUG=True, EMAIL_DEV_REDIRECT_TO=[])
    def test_debug_without_dev_contact_refuses(self):
        with self.assertRaises(RuntimeError):
            self.send_email(["real@example.org"], "Hello", None, None, "plain")
        self.assertEqual(mail.outbox, [])

    @override_settings(DEBUG=False)
    def test_production_untouched(self):
        self.send_email(["real@example.org"], "Hello", None, None, "plain")
        self.assertEqual(mail.outbox[0].to, ["real@example.org"])
        self.assertEqual(mail.outbox[0].subject, "Hello")


class MissedSlotTests(TestCase):
    def _cmd(self):
        from notification.management.commands.send_job_digest import Command

        return Command()

    def _aware(self, y, m, d, hh, mm):
        return timezone.make_aware(datetime(y, m, d, hh, mm))

    def test_missed_and_seen_slots(self):
        job = JobDefinition.objects.create(
            key="j", display_name="J", expected_times="23:00", grace_minutes=60
        )
        since = self._aware(2026, 9, 8, 6, 0)
        until = self._aware(2026, 9, 10, 6, 0)
        JobRun.objects.create(job=job, job_key="j", started_on=self._aware(2026, 9, 8, 23, 10))
        with mock.patch("django.utils.timezone.now", return_value=until):
            missed = self._cmd().missed_slots(job, since, until)
        self.assertEqual([m["expected_at"] for m in missed], [self._aware(2026, 9, 9, 23, 0)])

    def test_month_day_filter(self):
        job = JobDefinition.objects.create(
            key="f", display_name="F", expected_times="23:00",
            expected_days_of_month="1,16", grace_minutes=60,
        )
        since = self._aware(2026, 9, 1, 0, 0)
        until = self._aware(2026, 9, 20, 0, 0)
        with mock.patch("django.utils.timezone.now", return_value=until):
            missed = self._cmd().missed_slots(job, since, until)
        self.assertEqual(
            [m["expected_at"].day for m in missed], [1, 16]
        )

    def test_slot_still_within_grace_is_not_missed(self):
        job = JobDefinition.objects.create(
            key="g", display_name="G", expected_times="23:00", grace_minutes=120
        )
        until = self._aware(2026, 9, 9, 23, 30)
        with mock.patch("django.utils.timezone.now", return_value=until):
            missed = self._cmd().missed_slots(job, until - timedelta(days=1), until)
        self.assertEqual(missed, [])


@override_settings(DEBUG=False)
class ReportExternalJobTests(TestCase):
    def test_creates_completed_run_with_metrics(self):
        from django.core.management import call_command

        JobDefinition.objects.create(key="ext", display_name="Ext", runner="external")
        call_command(
            "report_external_job", "ext", "--exit-code", "0",
            "--metric", "dirs_removed=3", "--metric", "mb_reclaimed=12", "--no-email",
        )
        run = JobRun.objects.get(job_key="ext")
        self.assertEqual(run.status, "success")
        self.assertEqual(run.steps.get().extras, {"dirs_removed": "3", "mb_reclaimed": "12"})

    def test_nonzero_exit_is_failed(self):
        from django.core.management import call_command

        call_command("report_external_job", "ext2", "--exit-code", "1", "--no-email")
        run = JobRun.objects.get(job_key="ext2")
        self.assertEqual(run.status, "failed")
        self.assertIn("exit code 1", run.error)
        self.assertFalse(JobDefinition.objects.get(key="ext2").is_active)


@override_settings(DEBUG=False)
class AdminSwitchTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def test_disabled_step_is_recorded_not_run(self):
        job = JobDefinition.objects.create(key="sw", display_name="Sw")
        job.step_configs.create(step_name="b", is_enabled=False)
        ran = []
        recorder = reporting.start("sw", trigger="manual", definition=job)
        for name in ("a", "b"):
            with recorder.step(name) as step:
                if step.disabled:
                    continue
                ran.append(name)
                with reporting.record(city="Pune", household="1"):
                    pass
        run = recorder.finish()
        self.assertEqual(ran, ["a"])
        self.assertEqual(run.status, "success")
        self.assertEqual(
            list(run.steps.values_list("name", "status")), [("a", "success"), ("b", "disabled")]
        )
        self.assertEqual(set(job.step_configs.values_list("step_name", flat=True)), {"a", "b"})

    def test_inactive_job_does_nothing(self):
        from django.core.management import call_command
        from io import StringIO

        JobDefinition.objects.create(key="selftest", display_name="S", is_active=False)
        out = StringIO()
        call_command("run_job", "selftest", "--no-email", stdout=out)
        self.assertIn("switched off", out.getvalue())
        self.assertFalse(JobRun.objects.filter(job_key="selftest").exists())
