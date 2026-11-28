"""UAT and prod each use their own BIRT and Superset, and `manage.py check` warns when they are mixed."""

import re
import tempfile
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings

from utils.checks import birt_report_design_exists, environment_is_not_mixed

UAT = "https://uat.shelter-associates.org"


@override_settings(GRAPH_DETAILS={"toilet_construction": ("fixture", 7)}, GRAPHS_BUILD_URL="/graph/%s/%s")
class GraphsPageTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("boss", "b@example.org", "x"))

    @override_settings(GRAPHS_PUBLIC_URL="https://uat-graphs.shelter-associates.org/")
    def test_iframe_uses_this_servers_superset(self):
        response = self.client.get("/graphs/type/toilet_construction/")
        self.assertContains(response, 'src="https://uat-graphs.shelter-associates.org/login/"')
        self.assertNotContains(response, "https://graphs.shelter-associates.org")

    def test_csp_allows_exactly_the_configured_superset(self):
        response = self.client.get("/graphs/type/toilet_construction/")
        frame_src = re.search(r"frame-src ([^;]*)", response["Content-Security-Policy"]).group(1).split()
        origin = "{0.scheme}://{0.netloc}".format(urlparse(settings.GRAPHS_PUBLIC_URL))
        self.assertEqual(frame_src, ["'self'", origin])
        self.assertContains(response, 'src="%s/login/"' % settings.GRAPHS_PUBLIC_URL.rstrip("/"))

    def test_csp_frame_source_is_built_from_the_setting(self):
        source = open("shelter/settings.py").read()
        self.assertRegex(source, r'"frame-src": \[[^\]]*urlparse\(GRAPHS_PUBLIC_URL\)')


@override_settings(DEBUG=False)
class MixedEnvironmentCheckTests(SimpleTestCase):
    def ids(self, check):
        return [message.id for message in check(None)]

    @override_settings(BASE_APP_URL=UAT, BIRT_REPORT_URL="http://report.shelter-associates.org/",
                       GRAPHS_PUBLIC_URL="https://uat-graphs.shelter-associates.org/")
    def test_uat_pointing_at_prod_birt_warns(self):
        self.assertEqual(self.ids(environment_is_not_mixed), ["shelter.W002"])

    @override_settings(BASE_APP_URL=UAT, BIRT_REPORT_URL="https://uat-report.shelter-associates.org/",
                       GRAPHS_PUBLIC_URL="https://graphs.shelter-associates.org/")
    def test_uat_pointing_at_prod_superset_warns(self):
        self.assertEqual(self.ids(environment_is_not_mixed), ["shelter.W002"])

    @override_settings(BASE_APP_URL=UAT, BIRT_REPORT_URL="https://uat-report.shelter-associates.org/",
                       GRAPHS_PUBLIC_URL="https://uat-graphs.shelter-associates.org/")
    def test_uat_with_its_own_services_passes(self):
        self.assertEqual(self.ids(environment_is_not_mixed), [])

    @override_settings(BASE_APP_URL="https://app.shelter-associates.org", BIRT_REPORT_URL="http://report.shelter-associates.org/",
                       GRAPHS_PUBLIC_URL="https://graphs.shelter-associates.org/")
    def test_prod_with_prod_services_passes(self):
        self.assertEqual(self.ids(environment_is_not_mixed), [])

    def test_missing_birt_design_warns(self):
        with override_settings(BIRT_REPORT_CMD="sh /opt/birt-runtime/ReportEngine/genReport.sh -f PDF -o {} -p key={} /nope/FFReport.rptdesign"):
            self.assertEqual(self.ids(birt_report_design_exists), ["shelter.W003"])

    def test_existing_birt_design_passes(self):
        with tempfile.NamedTemporaryFile(suffix=".rptdesign") as design:
            with override_settings(BIRT_REPORT_CMD="sh genReport.sh -f PDF -o {} -p key={} %s" % design.name):
                self.assertEqual(self.ids(birt_report_design_exists), [])

    @override_settings(BASE_APP_URL="http://127.0.0.1:8000", BIRT_REPORT_URL="http://report.shelter-associates.org/")
    def test_local_machines_are_not_checked(self):
        self.assertEqual(self.ids(environment_is_not_mixed), [])

    @override_settings(DEBUG=True, BASE_APP_URL=UAT, BIRT_REPORT_URL="http://report.shelter-associates.org/",
                       BIRT_REPORT_CMD="sh x /nope/FFReport.rptdesign")
    def test_development_is_not_checked(self):
        self.assertEqual(self.ids(environment_is_not_mixed) + self.ids(birt_report_design_exists), [])
