import datetime
import io
import os
import shutil
import tempfile
import zipfile
from unittest import mock

import openpyxl
import pytz
from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from notification.models import JobRequest
from notification.services import email as job_email, queue
from plates.models import PlateActivity, PlateBatch, PlateTemplate
from plates.services import batch as batches, retention
from plates.tests.support import HEADERS, good_rows, sample_workbook, workbook_bytes

GROUP = "sticker_plates_generation"
IST = pytz.timezone("Asia/Kolkata")


class PlatesTestCase(TestCase):
    """A seeded database, a temporary MEDIA_ROOT and a logged-in group member."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media, PLATES_GROUPS=[GROUP], PLATES_MIN_FREE_DISK_GB=0, BASE_APP_URL="https://app.example.org")
        override.enable()
        self.addCleanup(override.disable)
        call_command("seed_plate_presets", stdout=io.StringIO())
        self.user = self.member("maker")
        self.client.force_login(self.user)

    def member(self, username):
        user = User.objects.create_user(username, email="{}@shelter-associates.org".format(username), password="x", is_staff=True)
        user.groups.add(Group.objects.get(name=GROUP))
        return user

    def files_under(self, folder):
        return [os.path.join(root, name) for root, _, names in os.walk(os.path.join(self.media, folder)) for name in names]

    def template(self, plate_type="digipin"):
        return PlateTemplate.objects.get(plate_type=plate_type, is_default=True)

    def upload(self, content, plate_type="digipin", name="nimajga.xlsx", holes=True):
        data = {"plate_type": plate_type, "template": self.template(plate_type).pk, "file": SimpleUploadedFile(name, content)}
        if holes:
            data["holes"] = "on"
        return self.client.post(reverse("plates:bulk_new"), data)

    def draft(self, content=None, plate_type="digipin"):
        self.upload(content or workbook_bytes(HEADERS[plate_type], good_rows(20, plate_type)), plate_type)
        return PlateBatch.objects.latest("pk")

    def confirm(self, batch, email="maker@shelter-associates.org"):
        return self.client.post(reverse("plates:bulk_confirm", args=[batch.public_id]), {"checked_demo": "yes", "email": email})

    def run_queue(self):
        request = queue.claim_next()
        self.assertIsNotNone(request)
        return queue.run(request)


class BulkFlowTests(PlatesTestCase):
    def test_draft_queued_running_done_with_20_rows(self):
        batch = self.draft()
        self.assertEqual(batch.status, "draft")
        page = self.client.get(reverse("plates:bulk_check", args=[batch.public_id]))
        self.assertContains(page, "Generate 20 plates")
        self.assertContains(page, "4J6M8286K8_1.png")
        demo = self.client.get(reverse("plates:bulk_demo_image", args=[batch.public_id, 2]))
        self.assertEqual(Image.open(io.BytesIO(demo.content)).size, (3000, 900))
        self.assertEqual(demo["Cache-Control"], "private, no-store")
        self.assertEqual(self.files_under("plate_exports") + [name for name in self.files_under("") if name.endswith(".png") and "plate_assets" not in name], [])

        self.confirm(batch)
        batch.refresh_from_db()
        self.assertEqual((batch.status, batch.confirmed_by, batch.row_count), ("queued", self.user, 20))
        self.assertEqual(batch.job_request.job_key, "plate_batch")
        self.assertIn("Plates queued: Nimajga Mal, DIGIPIN, 20 plates", [message.subject for message in mail.outbox])

        mail.outbox.clear()
        request = self.run_queue()
        batch.refresh_from_db()
        self.assertEqual((request.status, batch.status, batch.made_count, batch.skipped_count), ("done", "done", 20, 0))
        self.assertEqual([message.subject for message in mail.outbox], ["Plates ready: Nimajga Mal, DIGIPIN, 20 made, 0 skipped"])
        self.assertIn("/plates/batches/{}/".format(batch.public_id), mail.outbox[0].body)
        self.assertNotIn(self.media, mail.outbox[0].body)
        self.assert_zip(batch)

    def assert_zip(self, batch):
        self.assertTrue(batch.file_path.startswith(os.path.join(self.media, "plate_exports")))
        self.assertTrue(os.path.basename(batch.file_path).startswith("ichalkaranji_digipin_"))
        response = self.client.get(reverse("plates:batch_download", args=[batch.public_id]))
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("attachment;", response["Content-Disposition"])
        archive = zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))
        names = archive.namelist()
        self.assertIn("plates.xlsx", names)
        self.assertIn("images/4J6M8286K8_1.png", names)
        self.assertEqual(len([name for name in names if name.startswith("images/")]), 20)
        self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist()))
        plate = Image.open(io.BytesIO(archive.read("images/4J6M8286K8_1.png")))
        self.assertEqual(plate.size, (3000, 900))
        self.assertAlmostEqual(plate.info["dpi"][0], 600, places=1)
        report = openpyxl.load_workbook(io.BytesIO(archive.read("plates.xlsx")))
        self.assertEqual(report.sheetnames, ["Plates", "Batch"])
        self.assertTrue(PlateActivity.objects.filter(action="download", batch=batch).exists())

    def test_sample_file_end_to_end(self):
        batch = self.draft(sample_workbook())
        self.confirm(batch)
        self.run_queue()
        batch.refresh_from_db()
        self.assertEqual((batch.status, batch.made_count, batch.skipped_count), ("done", 5, 7))
        self.assertGreaterEqual(batch.warning_count, 1)
        archive = zipfile.ZipFile(batch.file_path)
        images = sorted(name for name in archive.namelist() if name.startswith("images/"))
        self.assertEqual(images, ["images/3728F37K28_2.png", "images/4J6M8286K8_1.png", "images/4J6M8286K8_12.png",
                                  "images/4J6M8286K8_1_2.png", "images/MMMMMMMMMM_3.png"])

    def test_activity_report_is_not_sent_for_plate_batches(self):
        batch = self.draft()
        self.confirm(batch)
        with mock.patch.object(job_email.contacts, "recipients_for", return_value=(["dev@shelter-associates.org"], [], [])):
            self.run_queue()
        self.assertFalse(any(message.subject.startswith("[Shelter]") for message in mail.outbox))

    def test_confirm_needs_the_tick_and_one_active_batch_per_user(self):
        batch = self.draft()
        response = self.client.post(reverse("plates:bulk_confirm", args=[batch.public_id]), {})
        self.assertIn("Tick", response["Location"])
        batch.refresh_from_db()
        self.assertEqual(batch.status, "draft")
        self.confirm(batch)
        second = self.draft()
        response = self.confirm(second)
        self.assertIn("You+already+have+a+batch+queued", response["Location"])

    def test_confirm_needs_a_shelter_email_which_gets_the_mails_and_the_developer_a_copy(self):
        from notification.models import EmailContact, EmailPurpose, EmailRecipient

        purpose = EmailPurpose.objects.create(key="plates_batch", display_name="Plates batch copy")
        EmailRecipient.objects.create(purpose=purpose, contact=EmailContact.objects.create(name="Developer", email="dev@shelter-associates.org"), kind="to")
        batch = self.draft()
        page = self.client.get(reverse("plates:bulk_check", args=[batch.public_id]))
        self.assertContains(page, 'value="maker@shelter-associates.org"')
        for bad in ("", "someone@gmail.com"):
            response = self.confirm(batch, email=bad)
            self.assertIn("Enter+the+%40shelter-associates.org+email", response["Location"])
        batch.refresh_from_db()
        self.assertEqual(batch.status, "draft")
        self.confirm(batch, email="field.team@shelter-associates.org")
        batch.refresh_from_db()
        self.assertEqual(batch.email, "field.team@shelter-associates.org")
        queued = mail.outbox[-1]
        self.assertEqual((queued.to, queued.cc), (["field.team@shelter-associates.org"], ["dev@shelter-associates.org"]))
        mail.outbox.clear()
        self.run_queue()
        ready = mail.outbox[-1]
        self.assertIn(reverse("plates:batch_download", args=[batch.public_id]), ready.body)
        self.assertEqual(ready.cc, ["dev@shelter-associates.org"])

    def test_zero_valid_rows_cannot_be_queued(self):
        batch = self.draft(workbook_bytes(HEADERS["digipin"], [["1", "BAD", 16.69, 74.45, "Nimajga Mal"]]))
        self.confirm(batch)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "draft")
        self.assertFalse(JobRequest.objects.exists())

    def test_missing_header_refused_before_any_row_is_read(self):
        response = self.upload(workbook_bytes(["House No", "DIGIPIN", "Ward"], [["1", "4J6M8286K8", "9"]]))
        self.assertContains(response, "missing the columns Latitude, Longitude, Slum Name")
        self.assertFalse(PlateBatch.objects.exists())
        self.assertEqual(self.files_under("plate_uploads"), [])

    def test_full_plates_without_drill_holes(self):
        self.upload(workbook_bytes(HEADERS["digipin"], good_rows(2)), holes=False)
        batch = PlateBatch.objects.latest("pk")
        self.assertFalse(batch.holes)
        self.confirm(batch)
        self.run_queue()
        batch.refresh_from_db()
        plate = Image.open(io.BytesIO(zipfile.ZipFile(batch.file_path).read("images/4J6M8286K8_1.png")))
        self.assertNotEqual(plate.convert("RGB").getpixel((118 + 26, 450 + 26)), (255, 255, 255))

    def test_plus_code_batch(self):
        batch = self.draft(plate_type="pluscode")
        self.confirm(batch)
        self.run_queue()
        batch.refresh_from_db()
        self.assertIn("images/7J8PMFV5+5RCH_1.png", zipfile.ZipFile(batch.file_path).namelist())


class CancelAndFailureTests(PlatesTestCase):
    def test_cancel_draft_and_queued(self):
        draft = self.draft()
        self.client.post(reverse("plates:batch_cancel", args=[draft.public_id]))
        draft.refresh_from_db()
        self.assertEqual((draft.status, draft.upload.name), ("cancelled", ""))

        queued = self.draft()
        self.confirm(queued)
        mail.outbox.clear()
        self.client.post(reverse("plates:batch_cancel", args=[queued.public_id]))
        queued.refresh_from_db()
        self.assertEqual((queued.status, queued.cancelled_by, queued.job_request.status), ("cancelled", self.user, "cancelled"))
        self.assertEqual(mail.outbox[0].subject, "Plates cancelled: Nimajga Mal")
        self.assertIsNone(queue.claim_next())

    def test_running_batch_cannot_be_cancelled(self):
        batch = self.draft()
        self.confirm(batch)
        PlateBatch.objects.filter(pk=batch.pk).update(status="running")
        response = self.client.post(reverse("plates:batch_cancel", args=[batch.public_id]))
        self.assertIn("Only+a+draft+or+a+queued+batch", response["Location"])

    def test_orphan_sweep_marks_a_stuck_run_failed_and_emails(self):
        batch = self.draft()
        self.confirm(batch)
        request = queue.claim_next()
        PlateBatch.objects.filter(pk=batch.pk).update(status="running")
        JobRequest.objects.filter(pk=request.pk).update(started_on=timezone.now() - datetime.timedelta(hours=7))
        mail.outbox.clear()
        self.assertEqual(queue.sweep_orphans(), 1)
        self.client.get(reverse("plates:batch_detail", args=[batch.public_id]))
        batch.refresh_from_db()
        self.assertEqual((batch.status, batch.error), ("failed", batches.RESTARTED))
        self.assertIn("Plates failed: Nimajga Mal, DIGIPIN", [message.subject for message in mail.outbox])
        self.client.get(reverse("plates:batch_detail", args=[batch.public_id]))
        self.assertEqual([message.subject for message in mail.outbox].count("Plates failed: Nimajga Mal, DIGIPIN"), 1)

    def test_disk_check_stops_the_batch(self):
        batch = self.draft()
        self.confirm(batch)
        with override_settings(PLATES_MIN_FREE_DISK_GB=10 ** 9):
            self.run_queue()
        batch.refresh_from_db()
        self.assertEqual((batch.status, batch.error), ("failed", batches.LOW_DISK))
        self.assertFalse(os.listdir(retention.export_root()))

    def test_generate_again_makes_a_new_draft_with_the_same_template_version(self):
        batch = self.draft()
        self.confirm(batch)
        PlateBatch.objects.filter(pk=batch.pk).update(status="failed")
        response = self.client.post(reverse("plates:batch_regenerate", args=[batch.public_id]))
        fresh = PlateBatch.objects.latest("pk")
        self.assertRedirects(response, reverse("plates:bulk_check", args=[fresh.public_id]))
        self.assertEqual((fresh.status, fresh.template_id, fresh.regenerated_from_id), ("draft", batch.template_id, batch.pk))
        self.assertNotEqual(fresh.upload.name, batch.upload.name)


class RetentionTests(PlatesTestCase):
    def at(self, *args):
        return IST.localize(datetime.datetime(*args))

    def test_delete_after_is_the_next_five_oclock_after_24_hours(self):
        cases = (
            (self.at(2026, 11, 26, 21, 30), self.at(2026, 11, 28, 5, 0)),
            (self.at(2026, 11, 26, 4, 0), self.at(2026, 11, 27, 5, 0)),
            (self.at(2026, 11, 26, 5, 0), self.at(2026, 11, 27, 5, 0)),
            (self.at(2026, 11, 30, 23, 59), self.at(2026, 12, 2, 5, 0)),
            (self.at(2026, 12, 31, 6, 0), self.at(2027, 1, 2, 5, 0)),
            (self.at(2028, 2, 28, 12, 0), self.at(2028, 3, 1, 5, 0)),
        )
        for finished, expected in cases:
            self.assertEqual(retention.delete_after(finished), expected, finished)

    def test_expired_file_shows_the_friendly_message(self):
        batch = self.draft()
        self.confirm(batch)
        self.run_queue()
        batch.refresh_from_db()
        shutil.rmtree(os.path.dirname(batch.file_path))
        response = self.client.get(reverse("plates:batch_download", args=[batch.public_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, retention.EXPIRED_MESSAGE)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "expired")
        self.assertContains(self.client.get(reverse("plates:batch_detail", args=[batch.public_id])), "Generate again")

    def test_cleanup_command(self):
        old_draft = self.draft()
        PlateBatch.objects.filter(pk=old_draft.pk).update(created_on=timezone.now() - datetime.timedelta(days=8))
        kept = self.draft()
        self.confirm(kept)
        self.run_queue()
        PlateBatch.objects.filter(pk=kept.pk).update(confirmed_on=timezone.now() - datetime.timedelta(days=181))
        kept.refresh_from_db()
        upload_path = kept.upload.path
        shutil.rmtree(os.path.dirname(kept.file_path))
        call_command("cleanup_plate_uploads", stdout=io.StringIO())
        self.assertFalse(PlateBatch.objects.filter(pk=old_draft.pk).exists())
        kept.refresh_from_db()
        self.assertEqual((kept.status, kept.upload.name), ("expired", ""))
        self.assertFalse(os.path.exists(upload_path))

    def test_cleanup_dry_run_changes_nothing(self):
        old_draft = self.draft()
        PlateBatch.objects.filter(pk=old_draft.pk).update(created_on=timezone.now() - datetime.timedelta(days=8))
        out = io.StringIO()
        call_command("cleanup_plate_uploads", "--dry-run", stdout=out)
        self.assertIn("would delete 1 unconfirmed draft", out.getvalue())
        self.assertTrue(PlateBatch.objects.filter(pk=old_draft.pk).exists())
