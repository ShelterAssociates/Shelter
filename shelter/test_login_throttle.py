"""Repeated failed sign-ins lock the username and the client IP on every password path, for 15 minutes."""

import base64
import hashlib
import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import caches
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from avni.tests.support import make_city, make_slum
from helpers.models import OTPVerification
from shelter.auth_throttle import IP_LIMIT, LOCKED_MESSAGE, USER_LIMIT, client_ip

LOGIN = "/accounts/login/"
PASSWORD = "Str0ng-pass!"
LOCMEM = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "auth_throttle": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "throttle-tests"},
}


@override_settings(CACHES=LOCMEM)
class ThrottleCase(TestCase):
    def setUp(self):
        caches["auth_throttle"].clear()
        self.user = User.objects.create_user("sunita", password=PASSWORD, is_staff=True)

    def login(self, username="sunita", password="wrong", ip="198.51.100.7"):
        """A fresh client every time, like an attacker who drops cookies between tries."""
        client = Client(REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR=ip)
        return client, client.post(LOGIN, {"username": username, "password": password})

    def fail(self, times, **kwargs):
        for _ in range(times):
            self.login(**kwargs)

    def assert_signed_in(self, response):
        self.assertEqual(response.status_code, 302, response.content[:300])

    def assert_locked(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, LOCKED_MESSAGE)


class LoginPageTests(ThrottleCase):
    def test_correct_password_is_refused_after_too_many_failures(self):
        """The auditor's Intruder run: the right password arrives after a list of wrong ones."""
        self.fail(USER_LIMIT)
        client, response = self.login(password=PASSWORD)
        self.assert_locked(response)
        self.assertNotIn("sessionid", client.cookies)

    def test_fewer_failures_do_not_lock_and_success_resets_the_count(self):
        self.fail(USER_LIMIT - 1)
        self.assert_signed_in(self.login(password=PASSWORD)[1])
        self.fail(USER_LIMIT - 1)
        self.assert_signed_in(self.login(password=PASSWORD)[1])

    def test_username_case_does_not_give_extra_tries(self):
        for name in ("sunita", "SUNITA", "Sunita", "sUnita", "sunitA"):
            self.login(username=name)
        self.assert_locked(self.login(password=PASSWORD)[1])

    def test_one_address_trying_many_usernames_is_locked(self):
        for i in range(IP_LIMIT):
            self.login(username="guess%d" % i, ip="203.0.113.9")
        self.assert_locked(self.login(password=PASSWORD, ip="203.0.113.9")[1])
        self.assert_signed_in(self.login(password=PASSWORD, ip="192.0.2.44")[1])

    def test_lock_is_logged(self):
        with self.assertLogs("shelter.auth_throttle", "WARNING") as logs:
            self.fail(USER_LIMIT)
        self.assertIn("user:sunita", "\n".join(logs.output))


class OtherPasswordPathsTests(ThrottleCase):
    def basic(self, password):
        token = base64.b64encode(("sunita:" + password).encode()).decode()
        return Client(REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="198.51.100.7").get(
            "/api/city/", HTTP_AUTHORIZATION="Basic " + token)

    def test_api_basic_auth_failures_count_and_the_lock_applies_there(self):
        for _ in range(USER_LIMIT):
            self.assertIn(self.basic("wrong").status_code, (401, 403))
        self.assertIn(self.basic(PASSWORD).status_code, (401, 403))
        self.assert_locked(self.login(password=PASSWORD)[1])

    def test_token_endpoint_is_locked_too(self):
        self.fail(USER_LIMIT)
        response = Client(REMOTE_ADDR="127.0.0.1", HTTP_X_FORWARDED_FOR="198.51.100.7").post(
            "/api-token-auth/", {"username": "sunita", "password": PASSWORD})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("token", response.json())


class ClientAddressTests(TestCase):
    def request(self, remote, forwarded=None):
        meta = {"REMOTE_ADDR": remote}
        if forwarded:
            meta["HTTP_X_FORWARDED_FOR"] = forwarded
        return type("Request", (), {"META": meta})()

    def test_behind_the_local_proxy_the_address_nginx_saw_is_used(self):
        self.assertEqual(client_ip(self.request("127.0.0.1", "1.1.1.1, 198.51.100.7")), "198.51.100.7")

    def test_a_forged_header_from_outside_is_ignored(self):
        self.assertEqual(client_ip(self.request("203.0.113.5", "1.1.1.1")), "203.0.113.5")


@override_settings(CACHES=LOCMEM)
class OtpThrottleTests(TestCase):
    def setUp(self):
        caches["auth_throttle"].clear()
        OTPVerification.objects.create(
            email="v@example.org", task="FACTSHEET_DOWNLOAD", slum=make_slum(make_city()),
            otp=hashlib.sha256(b"123456").hexdigest(), expiry_time=timezone.now() + timedelta(minutes=5),
        )

    def verify(self, otp):
        return Client().post("/helpers/api/verify-otp/", json.dumps({"email": "v@example.org", "otp": otp}),
                             content_type="application/json").json()["status"]

    def test_new_sessions_do_not_reset_the_otp_attempt_limit(self):
        for guess in ("000001", "000002", "000003", "000004", "000005"):
            self.assertEqual(self.verify(guess), "invalid")
        self.assertEqual(self.verify("123456"), "blocked")
