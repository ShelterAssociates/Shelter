"""Sponsor project uploads must not let HTML/JS run in the application's origin."""

import io
import shutil
import tempfile
import zipfile

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from master.forms import SlumForm
from sponsor.forms import ProjectDocumentForm, ProjectImageForm, SponsorForm, SponsorProjectDetailsSubFieldsForm
from sponsor.models import ProjectDocuments, ProjectImages, Sponsor, SponsorProject

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
HTML = b"<html><script>alert('UPLOAD-TEST')</script></html>"


def image_bytes(fmt):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, fmt)
    return buf.getvalue()


def upload(name, content, content_type="application/octet-stream"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class UploadValidationTests(TestCase):
    def document_form(self, name, content):
        return ProjectDocumentForm(data={}, files={"document": upload(name, content)})

    def image_form(self, name, content):
        return ProjectImageForm(data={}, files={"image": upload(name, content)})

    def test_document_accepts_a_real_pdf(self):
        form = self.document_form("report.pdf", PDF)
        form.is_valid()
        self.assertNotIn("document", form.errors)

    def test_document_rejects_html_js_php_svg_xml_and_kml(self):
        for name in ("test.html", "test.htm", "test.js", "test.php", "test.svg", "test.xml", "test.kml", "test.csv"):
            self.assertIn("document", self.document_form(name, HTML).errors, name)

    def test_document_accepts_real_jpg_jpeg_and_png(self):
        for name, fmt in (("clip.jpg", "JPEG"), ("clip.jpeg", "JPEG"), ("clip.png", "PNG")):
            form = self.document_form(name, image_bytes(fmt))
            form.is_valid()
            self.assertNotIn("document", form.errors, name)

    def test_document_rejects_other_image_types_and_fake_images(self):
        self.assertIn("document", self.document_form("clip.jfif", image_bytes("JPEG")).errors)
        self.assertIn("document", self.document_form("clip.gif", image_bytes("GIF")).errors)
        self.assertIn("document", self.document_form("clip.jpg", HTML).errors)
        self.assertIn("document", self.document_form("clip.png", image_bytes("JPEG")).errors)

    def test_document_rejects_html_renamed_to_pdf(self):
        self.assertIn("document", self.document_form("test.pdf", HTML).errors)

    def test_image_accepts_real_jpg_and_png(self):
        for name, fmt in (("a.jpg", "JPEG"), ("a.jpeg", "JPEG"), ("a.png", "PNG")):
            form = self.image_form(name, image_bytes(fmt))
            form.is_valid()
            self.assertNotIn("image", form.errors, name)

    def test_image_rejects_real_image_saved_under_an_active_extension(self):
        for name in ("evil.html", "evil.svg", "evil.php"):
            self.assertIn("image", self.image_form(name, image_bytes("PNG")).errors, name)

    def test_image_rejects_other_formats_and_mismatched_extension(self):
        self.assertIn("image", self.image_form("a.jpg", image_bytes("GIF")).errors)
        self.assertIn("image", self.image_form("a.png", image_bytes("JPEG")).errors)

    def test_sponsor_logo_follows_the_image_rules(self):
        form = SponsorForm(data={}, files={"logo": upload("logo.html", image_bytes("PNG"))})
        self.assertIn("logo", form.errors)

    def test_ff_report_zip_field_accepts_only_real_zip_files(self):
        def errors(name, content):
            return SponsorProjectDetailsSubFieldsForm(data={}, files={"zip_file": upload(name, content)}).errors
        self.assertIn("zip_file", errors("report.html", HTML))
        self.assertIn("zip_file", errors("report.zip", HTML))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("household.pdf", PDF)
        self.assertNotIn("zip_file", errors("report.zip", buf.getvalue()))

    def test_slum_factsheet_accepts_only_pdf(self):
        def errors(name, content):
            return SlumForm(data={}, files={"factsheet": upload(name, content)}).errors
        self.assertIn("factsheet", errors("fs.html", HTML))
        self.assertIn("factsheet", errors("fs.pdf", HTML))
        self.assertNotIn("factsheet", errors("fs.pdf", PDF))


class SponsorFixtureMixin:
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media)
        self.media_override.enable()
        group, _ = Group.objects.get_or_create(name="sponsor")
        self.owner = User.objects.create_user("hdfclife", password="x")
        self.other = User.objects.create_user("othersponsor", password="x")
        for user in (self.owner, self.other):
            user.groups.add(group)
        self.admin = User.objects.create_superuser("shelter", "s@example.org", "x")
        sponsor = Sponsor.objects.create(organization_name="HDFCLife", address="Pune", user=self.owner)
        Sponsor.objects.create(organization_name="Other", address="Pune", user=self.other)
        self.project = SponsorProject.objects.create(
            name="Toilet facilitation", project_type="1", funds_sponsored=100, status="2",
            created_by=self.admin, sponsor=sponsor,
        )

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def stored_document(self, name, content):
        doc = ProjectDocuments(sponsor_project=self.project)
        doc.document.save(name, ContentFile(content))
        return doc


class AdminUploadTests(SponsorFixtureMixin, TestCase):
    def post_project(self, document):
        self.client.force_login(self.admin)
        return self.client.post(
            "/accounts/sponsor/sponsorproject/add/",
            {
                "name": "Test project", "project_type": "1", "funds_sponsored": "10", "status": "2",
                "projectdocuments_set-TOTAL_FORMS": "1", "projectdocuments_set-INITIAL_FORMS": "0",
                "projectdocuments_set-MIN_NUM_FORMS": "0", "projectdocuments_set-MAX_NUM_FORMS": "1000",
                "projectdocuments_set-0-document": document,
                "projectimages_set-TOTAL_FORMS": "0", "projectimages_set-INITIAL_FORMS": "0",
                "projectimages_set-MIN_NUM_FORMS": "0", "projectimages_set-MAX_NUM_FORMS": "1000",
            },
        )

    def test_admin_refuses_the_auditors_html_upload(self):
        response = self.post_project(upload("text.html", HTML, "text/html"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SponsorProject.objects.filter(name="Test project").exists())
        self.assertFalse(ProjectDocuments.objects.exists())

    def test_admin_change_page_links_existing_files_through_the_protected_view(self):
        doc = self.stored_document("report.pdf", PDF)
        self.client.force_login(self.admin)
        response = self.client.get("/accounts/sponsor/sponsorproject/%d/change/" % self.project.pk)
        self.assertContains(response, reverse("sponsor_project_file", args=["document", doc.pk]))
        self.assertNotContains(response, "/media/sponsor_project/")

    def test_admin_saves_a_real_pdf(self):
        response = self.post_project(upload("report.pdf", PDF, "application/pdf"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ProjectDocuments.objects.count(), 1)


class ProjectFileViewTests(SponsorFixtureMixin, TestCase):
    def url(self, kind, pk):
        return reverse("sponsor_project_file", args=[kind, pk])

    def test_anonymous_user_is_sent_to_login(self):
        doc = self.stored_document("report.pdf", PDF)
        response = self.client.get(self.url("document", doc.pk))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/accounts/login/"))

    def test_another_sponsor_cannot_fetch_it(self):
        doc = self.stored_document("report.pdf", PDF)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url("document", doc.pk)).status_code, 404)

    def test_owner_gets_the_pdf_as_a_download_that_cannot_be_rendered_as_html(self):
        doc = self.stored_document("report.pdf", PDF)
        self.client.force_login(self.owner)
        response = self.client.get(self.url("document", doc.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("attachment"))
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("sandbox", response["Content-Security-Policy"])

    def test_staff_can_open_any_project_file(self):
        doc = self.stored_document("report.pdf", PDF)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url("document", doc.pk)).status_code, 200)

    def test_html_uploaded_before_the_fix_is_never_served(self):
        doc = self.stored_document("test.html", HTML)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url("document", doc.pk)).status_code, 404)

    def test_html_stored_under_a_pdf_name_is_never_served(self):
        doc = self.stored_document("02-html-renamed.pdf", HTML)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url("document", doc.pk)).status_code, 404)

    def test_older_jpg_and_ppt_documents_still_download(self):
        for name in ("Lokmat-140517.jpg", "stakeholder_slide.ppt"):
            doc = self.stored_document(name, b"legacy")
            self.client.force_login(self.owner)
            response = self.client.get(self.url("document", doc.pk))
            self.assertEqual(response.status_code, 200, name)
            self.assertTrue(response["Content-Disposition"].startswith("attachment"), name)

    def test_every_active_type_the_auditor_stored_is_refused(self):
        self.client.force_login(self.admin)
        for ext in ("html", "htm", "xhtml", "svg", "svgz", "js", "xml", "php", "php5", "phtml", "jsp", "asp", "aspx", "kml", "json", "csv"):
            doc = self.stored_document("payload." + ext, HTML)
            self.assertEqual(self.client.get(self.url("document", doc.pk)).status_code, 404, ext)

    def test_jfif_project_images_still_display(self):
        img = ProjectImages(sponsor_project=self.project)
        img.image.save("photo.jfif", ContentFile(image_bytes("JPEG")))
        self.client.force_login(self.owner)
        response = self.client.get(self.url("image", img.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_owner_sees_images_inline_as_images(self):
        img = ProjectImages(sponsor_project=self.project)
        img.image.save("photo.png", ContentFile(image_bytes("PNG")))
        self.client.force_login(self.owner)
        response = self.client.get(self.url("image", img.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertFalse(response.get("Content-Disposition", "").startswith("attachment"))

    def test_sponsor_page_links_files_through_the_protected_view(self):
        doc = self.stored_document("report.pdf", PDF)
        self.client.force_login(self.owner)
        response = self.client.get("/sponsor/")
        self.assertContains(response, self.url("document", doc.pk))
        self.assertNotContains(response, "/media/sponsor_project/")
