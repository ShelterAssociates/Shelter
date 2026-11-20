"""VAPT #5: names typed in admin are shown on other pages, so HTML in them is refused (output is also escaped in the JS)."""

import hashlib
import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.utils import timezone

from avni.tests.support import make_city, make_slum
from component.models import Metadata, Section
from helpers.models import FormSubmission, OTPVerification, PhotoTypeItem, SponsorPhotoConfig
from master.kmllevelparser import KMLLevelParser
from master.models import AdministrativeWard, CityReference, ElectedRepresentative, ElectoralWard, Slum, WardOfficeContact
from mastersheet.models import ActivityType, MaterialType, SBMUpload, Vendor, VendorType
from reports.models import BeneficiaryIndicator, Deliverable, WorkProgressParameter
from sponsor.models import Sponsor, SponsorProject
from utils.kml import UnsafeKMLError
from utils.validators import MARKUP_MESSAGE, PlainTextAdminMixin

PAYLOAD = "</select><div><img src=x onerror=alert(document.cookie)></div>"
NORMAL = "Ambedkar Nagar & Sons (Part 1) 'A'"

PROTECTED = {
    CityReference: ("city_name", "district_name", "state_name"),
    AdministrativeWard: ("name",),
    ElectoralWard: ("name",),
    Slum: ("name",),
    WardOfficeContact: ("title", "name"),
    ElectedRepresentative: ("name",),
    Section: ("name",),
    Metadata: ("name",),
    Sponsor: ("organization_name",),
    SponsorProject: ("name",),
    VendorType: ("name",),
    Vendor: ("name",),
    MaterialType: ("name",),
    SBMUpload: ("name",),
    ActivityType: ("name",),
    PhotoTypeItem: ("name",),
    SponsorPhotoConfig: ("name",),
    Deliverable: ("name",),
    WorkProgressParameter: ("name",),
    BeneficiaryIndicator: ("name",),
}


def kml(name):
    return (
        '<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><Folder>'
        "<Placemark><name>%s</name><Polygon><outerBoundaryIs><LinearRing><coordinates>"
        "73.1,18.1,0 73.1,18.2,0 73.2,18.2,0 73.2,18.1,0 73.1,18.1,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>"
        "</Folder></Document></kml>" % name
    ).encode("utf-8")


class AdminNameValidationTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        self.request.user = User.objects.create_superuser("shelter", "s@example.org", "x")

    def errors(self, model, field, value):
        form = admin.site._registry[model].get_form(self.request)(data={field: value})
        form.is_valid()
        return form.errors.get(field, [])

    def test_every_listed_admin_uses_the_plain_text_rule(self):
        for model, fields in PROTECTED.items():
            model_admin = admin.site._registry[model]
            self.assertIsInstance(model_admin, PlainTextAdminMixin, model.__name__)
            self.assertEqual(set(model_admin.plain_text_fields), set(fields), model.__name__)

    def test_html_in_any_protected_name_is_refused(self):
        for model, fields in PROTECTED.items():
            for field in fields:
                self.assertIn(MARKUP_MESSAGE, self.errors(model, field, PAYLOAD), "%s.%s" % (model.__name__, field))

    def test_ordinary_names_with_punctuation_are_accepted(self):
        for model, fields in PROTECTED.items():
            for field in fields:
                self.assertNotIn(MARKUP_MESSAGE, self.errors(model, field, NORMAL), "%s.%s" % (model.__name__, field))

    def test_inline_rows_are_checked_too(self):
        ward_admin = admin.site._registry[AdministrativeWard]
        inline = [i for i in ward_admin.get_inline_instances(self.request) if i.model is WardOfficeContact][0]
        row_form = inline.get_formset(self.request).form(data={"title": "Officer", "name": PAYLOAD})
        row_form.is_valid()
        self.assertIn(MARKUP_MESSAGE, row_form.errors.get("name", []))


class KMLNameTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.existing = make_slum(self.city).electoral_ward.administrative_ward

    def test_kml_with_payload_name_is_refused_before_anything_is_deleted(self):
        parser = KMLLevelParser(kml("&lt;img src=x onerror=alert(1)&gt;"), self.city.id, "true", "AdministrativeWard")
        with self.assertRaises(UnsafeKMLError):
            parser.parse_kml()
        self.assertTrue(AdministrativeWard.objects.filter(id=self.existing.id).exists())
        self.assertFalse(AdministrativeWard.objects.filter(name__contains="<").exists())

    def test_kml_with_plain_name_still_imports(self):
        cnt = KMLLevelParser(kml("Ward 7"), self.city.id, "false", "AdministrativeWard").parse_kml()
        self.assertEqual(cnt["created"], 1)
        self.assertTrue(AdministrativeWard.objects.filter(name="Ward 7", city=self.city).exists())


class PublicFormTests(TestCase):
    def test_public_otp_form_stores_the_name_without_markup(self):
        slum = make_slum(make_city())
        OTPVerification.objects.create(
            email="v@example.org", task="FACTSHEET_DOWNLOAD", slum=slum,
            otp=hashlib.sha256(b"123456").hexdigest(), expiry_time=timezone.now() + timedelta(minutes=5),
        )
        response = self.client.post("/helpers/api/verify-otp/", json.dumps({
            "email": "v@example.org", "otp": "123456", "name": "<img src=x onerror=alert(1)>Ravi", "mobile": "98<b>",
        }), content_type="application/json")
        self.assertEqual(response.json()["status"], "verified")
        saved = FormSubmission.objects.get()
        self.assertEqual((saved.name, saved.mobile), ("img src=x onerror=alert(1)Ravi", "98b"))
