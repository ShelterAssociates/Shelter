"""Household ZIPs and emailed GIS/RIM exports hold PII: never downloadable without the right login."""

import io
import os
import zipfile
from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase

from avni.tests.support import make_city, make_slum
from sponsor.forms import SponsorProjectDetailsSubFieldsForm
from sponsor.models import Sponsor, SponsorProjectDetails, SponsorProjectDetailsSubFields
from sponsor.tests.support import SponsorFixtureMixin

EXPORT_ID = "a" * 32


def zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("household_code_101.pdf", "%PDF-1.4 dummy")
    return buf.getvalue()


class PrivateDownloadCase(SponsorFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.slum = make_slum(make_city())
        self.details = SponsorProjectDetails.objects.create(
            sponsor=Sponsor.objects.get(user=self.owner), sponsor_project=self.project, slum=self.slum,
            household_code=["101", "102"],
        )
        self.sub = SponsorProjectDetailsSubFields(
            sponsor_project_details=self.details, quarter="1", status="1", household_code=["101", "102"]
        )
        self.sub.save()
        self.write("FFReport/HDFCLife/q1.zip", zip_bytes())
        SponsorProjectDetailsSubFields.objects.filter(pk=self.sub.pk).update(zip_file="FFReport/HDFCLife/q1.zip")

    def write(self, relative, content):
        path = os.path.join(self.media, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(content)

    def assert_login_redirect(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/accounts/login/"), response["Location"])


class FFReportZipTests(PrivateDownloadCase):
    def url(self, pk=None):
        return "/sponsor/ffreport/%d/" % (pk or self.sub.pk)

    def test_without_a_session_the_zip_is_refused(self):
        self.assert_login_redirect(self.client.get(self.url()))

    def test_owning_sponsor_downloads_it(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(b"".join(response.streaming_content), zip_bytes())

    def test_another_sponsor_gets_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_staff_downloads_it(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_missing_file_or_unknown_row_is_404(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url(pk=999999)).status_code, 404)
        os.remove(os.path.join(self.media, "FFReport/HDFCLife/q1.zip"))
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_sponsor_page_and_admin_link_to_the_protected_view(self):
        self.client.force_login(self.owner)
        page = self.client.get("/sponsor/").content.decode()
        self.assertIn(self.url(), page)
        self.assertNotIn("/media/FFReport", page)
        form = SponsorProjectDetailsSubFieldsForm(instance=SponsorProjectDetailsSubFields.objects.get(pk=self.sub.pk))
        self.assertIn(self.url(), str(form["zip_file"]))

    def test_media_url_of_the_zip_is_blocked(self):
        self.assertEqual(self.client.get("/media/FFReport/HDFCLife/q1.zip").status_code, 403)
        self.assertEqual(self.client.get("/media/hdfclife.zip").status_code, 403)


def fake_birt(command):
    with open(command, "wb") as pdf:
        pdf.write(b"%PDF-1.4 dummy")


@mock.patch("sponsor.views.build_command", lambda template, pdf_file, key: pdf_file)
@mock.patch("sponsor.views.report_exec", fake_birt)
class CreateZipTests(PrivateDownloadCase):
    def url(self, slum=None):
        return "/sponsor/%s/" % (slum or self.slum.name)

    def test_without_a_session_it_is_refused(self):
        self.assert_login_redirect(self.client.get(self.url()))

    def test_user_who_is_not_a_sponsor_gets_404_not_500(self):
        self.client.force_login(User.objects.create_user("plain", password="x"))
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_sponsor_of_another_slum_gets_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_owner_gets_the_pdfs_and_nothing_is_left_in_media(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
        self.assertEqual(sorted(names), ["household_code_101.pdf", "household_code_102.pdf"])
        self.assertEqual(sorted(os.listdir(self.media)), ["FFReport"])


class EmailedExportLinkTests(PrivateDownloadCase):
    GIS_URL = "/component/gis-export-download/%s/" % EXPORT_ID
    RIM_URL = "/mastersheet/rim-data-download/download/%s/" % EXPORT_ID

    def setUp(self):
        super().setUp()
        self.write("gis_exports/%s/slum-export.zip" % EXPORT_ID, zip_bytes())
        self.write("rim_exports/%s/rim-data-export.csv" % EXPORT_ID, b"slum,household\nX,101\n")
        self.staff = User.objects.create_user("staffer", password="x", is_staff=True)

    def test_without_a_session_both_links_go_to_login_and_back(self):
        for url in (self.GIS_URL, self.RIM_URL):
            response = self.client.get(url)
            self.assert_login_redirect(response)
            self.assertIn("next=" + url, response["Location"])

    def test_logged_in_user_without_export_rights_is_refused(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.GIS_URL).status_code, 403)
        self.assertEqual(self.client.get(self.RIM_URL).status_code, 403)

    def test_gis_account_gets_the_gis_export(self):
        self.client.force_login(User.objects.create_user("GIS", password="x"))
        response = self.client.get(self.GIS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, zip_bytes())

    def test_rim_download_group_member_gets_the_rim_export(self):
        self.staff.groups.add(Group.objects.get_or_create(name="Team Leader")[0])
        self.client.force_login(self.staff)
        response = self.client.get(self.RIM_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"X,101", response.content)

    def test_superuser_gets_both(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.GIS_URL).status_code, 200)
        self.assertEqual(self.client.get(self.RIM_URL).status_code, 200)

    def test_media_urls_of_the_exports_are_blocked(self):
        self.assertEqual(self.client.get("/media/gis_exports/%s/slum-export.zip" % EXPORT_ID).status_code, 403)
        self.assertEqual(self.client.get("/media/rim_exports/%s/rim-data-export.csv" % EXPORT_ID).status_code, 403)
