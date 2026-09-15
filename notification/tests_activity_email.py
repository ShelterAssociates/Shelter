"""Activity report emails for console / shell runs."""

import csv
import os
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from notification.models import EmailContact, EmailPurpose, EmailRecipient, JobRequest, JobRun
from notification.services import email as job_email


def contact(slug):
    return EmailContact.objects.create(name=slug, email="{}@shelter-associates.org".format(slug))


def purpose(key, to):
    row = EmailPurpose.objects.create(key=key, display_name=key)
    for address in to:
        EmailRecipient.objects.create(purpose=row, contact=address, kind="to")
    return row


@override_settings(DEBUG=False, BASE_APP_URL="https://app.test")
class ActivityReportTests(TestCase):
    def setUp(self):
        self.developer, self.data = contact("developer"), contact("data")
        purpose("avni_console_activity", [self.developer, self.data])
        purpose("avni_bulk_update", [self.developer, self.data])
        self.user = User.objects.create(username="priya", email="priya@shelter-associates.org")
        self.run = JobRun.objects.create(job_key="rhs_sync", status="success", trigger="manual", records_total=3, records_ok=3)
        self.request = JobRequest.objects.create(job_key="rhs_sync", params={"from_date": "2026-01-01", "subject_types": ["Household"]},
                                                 requested_by=self.user, status="done", summary="success: 3 ok", job_run=self.run)

    def test_sync_report_goes_to_team_with_requester_in_cc(self):
        job_email.send_activity_report(self.request, self.run)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(sorted(message.to), [self.data.email, self.developer.email])
        self.assertEqual(message.cc, [self.user.email])
        self.assertIn("priya", message.subject)
        self.assertIn("RHS registration", message.subject)
        body = message.alternatives[0][0]
        self.assertIn("priya", body)
        self.assertIn("id {}".format(self.user.pk), body)
        self.assertIn("from 2026-01-01", body)
        self.assertIn("/avni-console/runs/{}/".format(self.request.pk), body)

    def test_bulk_report_goes_to_team_only_and_attaches_changes(self):
        self.request.job_key = "avni_bulk_update"
        self.request.params = {"bulk_update_id": 7, "dry_run": False}
        self.request.save()
        self.run.job_key = "avni_bulk_update"
        self.run.save()
        handle, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(handle, "w", newline="") as out:
            writer = csv.writer(out)
            writer.writerow(["uuid", "field", "old", "new", "status", "error"])
            for i in range(250):
                writer.writerow(["u{}".format(i), "Aadhaar number", "1", "2", "updated", ""])
        try:
            with mock.patch.object(job_email, "changes_file_for", return_value=path):
                job_email.send_activity_report(self.request, self.run)
        finally:
            os.remove(path)
        message = mail.outbox[0]
        self.assertEqual(sorted(message.to), [self.data.email, self.developer.email])
        self.assertEqual(message.cc, [], "bulk updates go to developer and data only")
        body = message.alternatives[0][0]
        self.assertIn("250 change", body)
        self.assertNotIn("u0", body, "changes live in the attachment, not the body")
        self.assertNotIn("Aadhaar number", body)
        self.assertEqual([name for name, _, _ in message.attachments], ["changes.csv"])

    def test_dry_run_is_marked(self):
        self.request.job_key = "avni_bulk_update"
        self.request.params = {"bulk_update_id": 7, "dry_run": True}
        self.request.save()
        job_email.send_activity_report(self.request, self.run)
        self.assertIn("DRY RUN", mail.outbox[0].subject)

    def test_failed_request_without_run_still_reports(self):
        self.request.job_run = None
        self.request.status = "failed"
        self.request.error = "Stopped unexpectedly"
        self.request.save()
        job_email.send_activity_report(self.request, None)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("failed", mail.outbox[0].subject.lower())
        self.assertIn("Stopped unexpectedly", mail.outbox[0].alternatives[0][0])

    def test_no_recipients_logs_and_returns_none(self):
        EmailRecipient.objects.all().delete()
        with override_settings(JOB_NOTIFY_FALLBACK_EMAILS=[]):
            self.assertIsNone(job_email.send_activity_report(self.request, self.run))
        self.assertEqual(len(mail.outbox), 0)

    def test_requester_not_duplicated_when_already_a_recipient(self):
        self.user.email = self.developer.email
        self.user.save()
        job_email.send_activity_report(self.request, self.run)
        self.assertEqual(mail.outbox[0].cc, [])
