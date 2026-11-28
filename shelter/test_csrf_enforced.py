"""CSRF is checked on every browser endpoint, and every page sends the token with its AJAX calls."""

import re
import subprocess

from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.test import Client, SimpleTestCase, TestCase
from django.urls import get_resolver

# Only views no browser session can reach: the AVNI app (API key header) and
# browser CSP reports (sent without a token). DRF views check CSRF themselves.
ALLOWED_EXEMPT = {"component.avni_map.map_subject_to_structure", "shelter.views.csp_report"}
JQUERY = re.compile(r"<script[^>]*src=[^>]*(jquery(-[0-9.]+)?(\.min)?\.js|jquery/jquery\.js)", re.IGNORECASE)


def routes(patterns=None):
    for pattern in get_resolver().url_patterns if patterns is None else patterns:
        if hasattr(pattern, "url_patterns"):
            yield from routes(pattern.url_patterns)
        else:
            yield pattern.callback


class ExemptViewTests(SimpleTestCase):
    def test_only_allowed_views_skip_csrf(self):
        exempt = set()
        for callback in routes():
            if not getattr(callback, "csrf_exempt", False) or hasattr(callback, "cls") or hasattr(callback, "view_class"):
                continue
            exempt.add("%s.%s" % (callback.__module__, callback.__name__))
        self.assertEqual(exempt, ALLOWED_EXEMPT)

    def test_every_page_with_jquery_loads_the_csrf_script(self):
        files = subprocess.check_output(["git", "ls-files", "-z", "*.html"]).decode().split("\0")
        missing = []
        for path in files:
            if not path or path.startswith(("static/", "master/static/")) or path.endswith("rest_framework/api.html"):
                continue
            text = open(path, errors="replace").read()
            if JQUERY.search(text) and "js/csrf.js" not in text:
                missing.append(path)
        self.assertEqual(missing, [])


class ForgedRequestTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("shelter", "s@example.org", "Str0ng-pass!")
        self.browser = Client(enforce_csrf_checks=True)
        self.assertTrue(self.browser.login(username="shelter", password="Str0ng-pass!"))

    def post(self, path, token=None, **extra):
        headers = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        if token:
            headers["HTTP_X_CSRFTOKEN"] = token
        return self.browser.post(path, "[]", content_type="application/json", **headers, **extra)

    def token(self):
        response = self.browser.get("/accounts/auth/user/add/")
        return str(response.context["csrf_token"]) if response.context else get_token(response.wsgi_request)

    def test_forged_delete_is_refused(self):
        self.assertEqual(self.post("/mastersheet/delete_selected/").status_code, 403)

    def test_same_kind_of_request_with_the_page_token_passes(self):
        self.assertEqual(self.post("/admin/cityList/").status_code, 403)
        self.assertEqual(self.post("/admin/cityList/", token=self.token()).status_code, 200)

    def test_lookup_endpoints_need_the_token_too(self):
        for path in ("/admin/slumList/", "/mastersheet/sponsorprojectList/", "/graphs/covid_report/", "/admin/search/"):
            self.assertEqual(self.post(path).status_code, 403, path)
