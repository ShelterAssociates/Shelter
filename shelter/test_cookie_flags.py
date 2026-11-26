"""Every cookie the app sends is HttpOnly, Secure and SameSite, and no JavaScript needs to read one."""

import re
import subprocess

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from shelter.middleware import CookieFlagsMiddleware

VENDOR = re.compile(r"\.min\.js$|^static/admin/|^master/static/|jquery-1|jquery\.fancytree|leaflet\.js|bootstrap")


def assert_flags(test, response):
    test.assertTrue(response.cookies)
    for name, cookie in response.cookies.items():
        test.assertTrue(cookie["httponly"], name)
        test.assertTrue(cookie["secure"], name)
        test.assertEqual(cookie["samesite"], "Lax", name)


class CookieFlagTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("shelter", "s@example.org", "Str0ng-pass!")

    def login(self):
        response = self.client.post("/accounts/login/", {"username": "shelter", "password": "Str0ng-pass!"})
        self.assertEqual(response.status_code, 302)
        return response

    def test_csrf_cookie_on_the_login_page(self):
        response = self.client.get("/accounts/login/")
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        assert_flags(self, response)

    def test_cookies_set_at_login(self):
        response = self.login()
        self.assertIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        assert_flags(self, response)

    def test_cookie_deletions_at_logout(self):
        self.login()
        response = self.client.get("/accounts/logout/")
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_NAME]["max-age"], 0)
        assert_flags(self, response)

    def test_settings_are_in_settings_py(self):
        source = open("shelter/settings.py").read()
        self.assertIn("CSRF_COOKIE_SECURE = True", source)
        self.assertIn("CSRF_COOKIE_HTTPONLY = True", source)


class MiddlewareTests(SimpleTestCase):
    def response_for(self, **cookie):
        def view(request):
            response = HttpResponse()
            response.set_cookie("third_party", "x", **cookie)
            return response
        return CookieFlagsMiddleware(view)(RequestFactory().get("/"))

    @override_settings(DEBUG=False, SESSION_COOKIE_SECURE=False)
    def test_any_cookie_gets_the_flags_in_production(self):
        assert_flags(self, self.response_for())

    def test_stricter_samesite_is_kept(self):
        self.assertEqual(self.response_for(samesite="Strict").cookies["third_party"]["samesite"], "Strict")

    @override_settings(DEBUG=True, SESSION_COOKIE_SECURE=False)
    def test_plain_http_development_keeps_working(self):
        cookie = self.response_for().cookies["third_party"]
        self.assertTrue(cookie["httponly"])
        self.assertFalse(cookie["secure"])

    def test_no_javascript_reads_cookies(self):
        files = subprocess.check_output(["git", "ls-files", "-z", "*.js", "*.html"]).decode().split("\0")
        found = [f for f in files if f and not VENDOR.search(f) and "document.cookie" in open(f, errors="replace").read()]
        self.assertEqual(found, [])
