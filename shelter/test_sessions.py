"""VAPT #4: a copied session cookie must not keep working from another browser, and sessions must expire."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.utils import timezone

FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:156.0) Gecko/20100101 Firefox/156.0"
CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
PAGE = "/admin/"


class SessionCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("shelter", "s@example.org", "Str0ng-pass!")

    def browser(self, agent=FIREFOX, login=True):
        client = Client(HTTP_USER_AGENT=agent)
        if login:
            response = client.post("/accounts/login/", {"username": "shelter", "password": "Str0ng-pass!"})
            self.assertEqual(response.status_code, 302)
        return client

    def steal_cookie(self, victim, agent, every_cookie=False):
        thief = Client(HTTP_USER_AGENT=agent)
        names = list(victim.cookies.keys()) if every_cookie else [settings.SESSION_COOKIE_NAME]
        for name in names:
            thief.cookies[name] = victim.cookies[name].value
        return thief

    def assert_logged_out(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/accounts/login/"), response["Location"])


class CookieReplayTests(SessionCase):
    def test_same_browser_keeps_working(self):
        victim = self.browser()
        self.assertEqual(victim.get(PAGE).status_code, 200)
        self.assertEqual(victim.get(PAGE).status_code, 200)

    def test_admin_cookie_pasted_into_another_browser_is_refused(self):
        victim = self.browser(FIREFOX)
        thief = self.steal_cookie(victim, CHROME)
        self.assert_logged_out(thief.get(PAGE))

    def test_replay_from_another_browser_also_ends_the_stolen_session(self):
        victim = self.browser(FIREFOX)
        old_key = victim.cookies[settings.SESSION_COOKIE_NAME].value
        self.steal_cookie(victim, CHROME).get(PAGE)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        self.assert_logged_out(self.steal_cookie(victim, FIREFOX).get(PAGE))

    def test_sessionid_pasted_into_a_private_window_of_the_same_browser_is_refused(self):
        """The auditor's PoE: same machine, same browser, only the sessionid copied into a fresh cookie jar."""
        victim = self.browser(FIREFOX)
        old_key = victim.cookies[settings.SESSION_COOKIE_NAME].value
        private_window = self.steal_cookie(victim, FIREFOX)
        self.assert_logged_out(private_window.get(PAGE))
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        self.assert_logged_out(victim.get(PAGE))

    def test_copying_every_cookie_from_the_same_browser_is_not_detectable(self):
        """Documented limit: whoever can read all of a browser's cookies already controls that machine."""
        victim = self.browser(FIREFOX)
        self.assertEqual(self.steal_cookie(victim, FIREFOX, every_cookie=True).get(PAGE).status_code, 200)

    def test_session_from_before_the_fix_is_bound_on_first_use(self):
        legacy = Client(HTTP_USER_AGENT=FIREFOX)
        legacy.force_login(self.admin)
        session = legacy.session
        session.pop("_client_fingerprint", None)
        session.save()
        self.assertEqual(legacy.get(PAGE).status_code, 200)
        self.assertIn("sa_device", legacy.cookies)
        self.assert_logged_out(self.steal_cookie(legacy, FIREFOX).get(PAGE))


class LogoutAndExpiryTests(SessionCase):
    def test_cookies_are_useless_after_logout(self):
        victim = self.browser()
        copied = self.steal_cookie(victim, FIREFOX, every_cookie=True)
        response = victim.get("/accounts/logout/")
        self.assertEqual(response.cookies["sa_device"]["max-age"], 0)
        self.assert_logged_out(copied.get(PAGE))

    def test_session_and_device_cookies_end_with_the_browser_and_are_httponly(self):
        victim = self.browser()
        for name in (settings.SESSION_COOKIE_NAME, "sa_device"):
            cookie = victim.cookies[name]
            self.assertEqual(cookie["max-age"], "", name)
            self.assertEqual(cookie["expires"], "", name)
            self.assertTrue(cookie["httponly"], name)
            self.assertEqual(cookie["samesite"], "Lax", name)

    def test_idle_timeout_is_eight_hours_and_slides_with_activity(self):
        victim = self.browser()
        victim.get(PAGE)
        key = victim.cookies[settings.SESSION_COOKIE_NAME].value
        remaining = Session.objects.get(session_key=key).expire_date - timezone.now()
        self.assertTrue(timedelta(hours=7, minutes=59) < remaining <= timedelta(hours=8))

    def test_session_idle_past_the_timeout_is_logged_out(self):
        victim = self.browser()
        key = victim.cookies[settings.SESSION_COOKIE_NAME].value
        Session.objects.filter(session_key=key).update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assert_logged_out(victim.get(PAGE))


class MiddlewareOrderTests(TestCase):
    def test_security_middleware_runs_first(self):
        self.assertEqual(settings.MIDDLEWARE[0], "django.middleware.security.SecurityMiddleware")
