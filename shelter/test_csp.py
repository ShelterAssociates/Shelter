"""Content-Security-Policy: strict script policy on every page, and nothing in the code that needs it relaxed."""

import json
import re
import subprocess

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings

INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc\s*=)[^>]*>", re.IGNORECASE)
INLINE_HANDLER = re.compile(r"\bon[a-z]+\s*=\s*\\?['\"]", re.IGNORECASE)
VENDOR = re.compile(r"\.min\.js$|^static/admin/|^master/static/|jquery-1|jquery\.fancytree|leaflet\.js|bootstrap")


def tracked(*patterns):
    files = subprocess.check_output(["git", "ls-files", "-z"] + list(patterns)).decode().split("\0")
    return [f for f in files if f and not VENDOR.search(f) and "/migrations/" not in f and "test" not in f]


def directives(response):
    header = response["Content-Security-Policy"]
    return {part.split()[0]: part.split()[1:] for part in header.split("; ")}


class HeaderTests(TestCase):
    def test_login_page_has_a_strict_policy(self):
        policy = directives(self.client.get("/accounts/login/"))
        self.assertEqual(policy["default-src"], ["'self'"])
        self.assertEqual(policy["object-src"], ["'none'"])
        self.assertEqual(policy["base-uri"], ["'self'"])
        self.assertEqual(policy["frame-ancestors"], ["'self'"])
        self.assertNotIn("'unsafe-inline'", policy["script-src"])
        self.assertNotIn("'unsafe-eval'", policy["script-src"])
        self.assertTrue(any(source.startswith("'nonce-") for source in policy["script-src"]))

    def test_every_inline_script_on_the_page_carries_the_header_nonce(self):
        response = self.client.get("/accounts/login/")
        nonce = [s for s in directives(response)["script-src"] if s.startswith("'nonce-")][0][7:-1]
        scripts = INLINE_SCRIPT.findall(response.content.decode())
        self.assertTrue(scripts)
        for tag in scripts:
            self.assertIn('nonce="%s"' % nonce, tag)

    def test_nonce_changes_on_every_request(self):
        first = directives(self.client.get("/accounts/login/"))["script-src"][-1]
        second = directives(self.client.get("/accounts/login/"))["script-src"][-1]
        self.assertNotEqual(first, second)

    def test_logged_in_pages_and_api_get_the_header(self):
        self.client.force_login(User.objects.create_superuser("boss", "b@example.org", "x"))
        for path in ("/admin/", "/accounts/", "/api/city/?format=api"):
            self.assertIn("Content-Security-Policy", self.client.get(path), path)

    @override_settings(CSP_REPORT_ONLY=True)
    def test_report_only_switch(self):
        response = self.client.get("/accounts/login/")
        self.assertIn("Content-Security-Policy-Report-Only", response)
        self.assertNotIn("Content-Security-Policy", response)


class ReportEndpointTests(TestCase):
    def post(self, report):
        return self.client.post("/csp-report/", json.dumps({"csp-report": report}), content_type="application/csp-report")

    def test_violation_is_logged(self):
        with self.assertLogs("shelter.views", "WARNING") as logs:
            response = self.post({"violated-directive": "script-src-elem", "blocked-uri": "https://evil.example/x.js",
                                  "document-uri": "https://uat.shelter-associates.org/"})
        self.assertEqual(response.status_code, 204)
        self.assertIn("evil.example", logs.output[0])

    def test_garbage_and_get_are_harmless(self):
        self.assertEqual(self.client.post("/csp-report/", "not json", content_type="application/json").status_code, 204)
        self.assertEqual(self.client.get("/csp-report/").status_code, 405)

    def test_jquery_feature_test_is_not_logged(self):
        with self.assertRaises(AssertionError):
            with self.assertLogs("shelter.views", "WARNING"):
                self.post({"violated-directive": "script-src-attr", "blocked-uri": "inline",
                           "source-file": "https://uat.shelter-associates.org/static/js/jquery.min.js"})


class CodeGuardTests(SimpleTestCase):
    """Fails when new code would need 'unsafe-inline' again."""

    def test_inline_scripts_in_templates_have_the_nonce(self):
        missing = []
        for path in tracked("*.html"):
            for tag in INLINE_SCRIPT.findall(open(path, errors="replace").read()):
                if "nonce=" not in tag:
                    missing.append("%s: %s" % (path, tag))
        self.assertEqual(missing, [])

    def test_no_inline_event_handlers_or_javascript_urls(self):
        found = []
        for path in tracked("*.html", "*.js", "*.py"):
            text = open(path, errors="replace").read()
            for match in INLINE_HANDLER.finditer(text):
                found.append("%s: %s" % (path, text[match.start():match.start() + 40]))
            if re.search(r"[\"']javascript:", text):
                found.append("%s: javascript: URL" % path)
        self.assertEqual(found, [])

    def test_map_widgets_render_without_inline_script(self):
        from component.admin import CspMapWidget
        from master.forms import LocationWidget
        for html in (LocationWidget().render("shape", None), CspMapWidget().render("shape", None)):
            self.assertEqual(INLINE_SCRIPT.findall(html), [])
            self.assertNotIn("javascript:", html)
