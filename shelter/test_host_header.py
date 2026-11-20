"""VAPT #7: a forged Host header must not be answered or end up in links the app sends out."""

import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from avni.tests.support import make_city, make_slum
from utils.checks import allowed_hosts_are_explicit

UAT = "uat.shelter-associates.org"
BASE = "https://" + UAT


class AllowedHostsCheckTests(TestCase):
    def ids(self):
        return [m.id for m in allowed_hosts_are_explicit(None)]

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["*"], BASE_APP_URL=BASE)
    def test_wildcard_hosts_fail_the_check(self):
        self.assertEqual(self.ids(), ["shelter.E001"])

    @override_settings(DEBUG=False, ALLOWED_HOSTS=[], BASE_APP_URL=BASE)
    def test_empty_hosts_fail_the_check(self):
        self.assertEqual(self.ids(), ["shelter.E001"])

    @override_settings(DEBUG=False, ALLOWED_HOSTS=[UAT], BASE_APP_URL=BASE)
    def test_explicit_hosts_matching_base_url_pass(self):
        self.assertEqual(self.ids(), [])

    @override_settings(DEBUG=False, ALLOWED_HOSTS=[UAT], BASE_APP_URL="http://127.0.0.1:8000")
    def test_base_url_outside_allowed_hosts_warns(self):
        self.assertEqual(self.ids(), ["shelter.W001"])

    @override_settings(DEBUG=True, ALLOWED_HOSTS=["*"])
    def test_development_is_not_checked(self):
        self.assertEqual(self.ids(), [])


@override_settings(ALLOWED_HOSTS=[UAT])
class HostValidationTests(TestCase):
    def test_request_for_another_host_is_refused(self):
        self.assertEqual(self.client.get("/accounts/login/", HTTP_HOST="attacker.com").status_code, 400)

    def test_request_for_our_host_is_served(self):
        self.assertEqual(self.client.get("/accounts/login/", HTTP_HOST=UAT).status_code, 200)


class RunNow:
    """Stands in for threading.Thread: runs the export job immediately."""

    def __init__(self, target, **kwargs):
        self.target, self.name = target, "test"

    def start(self):
        self.target()

    def is_alive(self):
        return False


@override_settings(ALLOWED_HOSTS=["*"], BASE_APP_URL=BASE)
class EmailedLinkTests(TestCase):
    """Even with a loose ALLOWED_HOSTS, emailed links use BASE_APP_URL, not the Host header."""

    def setUp(self):
        self.slum = make_slum(make_city())
        self.request = {"HTTP_HOST": "attacker.com", "content_type": "application/json"}

    def test_rim_export_email_link_uses_base_app_url(self):
        self.client.force_login(User.objects.create_superuser("boss", "b@example.org", "x"))
        with mock.patch("mastersheet.views.threading.Thread", RunNow), \
                mock.patch("mastersheet.views._run_large_rim_export_job") as job:
            self.client.post("/mastersheet/rim-data-download/submit/", json.dumps({
                "mode": "slum_codes", "slum_codes": [self.slum.shelter_slum_code],
                "email_export": True, "email_address": "gis@shelter-associates.org",
            }), **self.request)
        self.assertEqual(job.call_args[0][2], BASE)

    def test_gis_export_email_link_uses_base_app_url(self):
        self.client.force_login(User.objects.create_user("GIS", password="x"))
        with mock.patch("component.views.threading.Thread", RunNow), \
                mock.patch("component.views._run_large_gis_export_job") as job:
            self.client.post("/component/export-filtered-kml/", json.dumps({
                "slum_id": self.slum.id, "email_export": True, "email_address": "gis@shelter-associates.org",
            }), **self.request)
        self.assertEqual(job.call_args[0][5], BASE)
