"""Site-level auth tests: self-service password reset/change is retired.

Passwords are set by the administrator in Django admin. These tests pin that
the public reset routes are gone, nothing is ever mailed, and the admin's own
set-password form still works.
"""

from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

CONTACT = "developer@shelter-associates.org"


class PasswordResetRetiredTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", "alice@example.org", "AlicePass123")
        mail.outbox = []

    def test_login_page_shows_a_visible_password_reset_button(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("password_reset"))
        self.assertNotContains(response, 'class="login-help" style="display:none;"')

    def test_contact_page_names_the_administrator_address(self):
        response = self.client.get(reverse("password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, CONTACT)

    def test_contact_page_has_no_email_field_to_submit(self):
        response = self.client.get(reverse("password_reset"))
        self.assertNotContains(response, "<form")
        self.assertNotContains(response, 'name="email"')

    def test_posting_to_reset_is_rejected_and_mails_nothing(self):
        response = self.client.post(reverse("password_reset"), {"email": "alice@example.org"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(len(mail.outbox), 0)

    def test_posting_to_password_change_is_rejected_and_mails_nothing(self):
        response = self.client.post(reverse("password_change"), {"email": "alice@example.org"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(len(mail.outbox), 0)

    def test_token_routes_no_longer_exist(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        for path in (
            "/accounts/reset/{}/{}/".format(uid, token),
            "/accounts/reset/done/",
            "/accounts/password_reset/done/",
            "/accounts/password_change/done/",
        ):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertTrue(response["Location"].startswith("/accounts/login/"), path)

    def test_an_emailed_token_can_no_longer_set_a_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        self.client.post(
            "/accounts/reset/{}/{}/".format(uid, token),
            {"new_password1": "TakenOver999", "new_password2": "TakenOver999"},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("AlicePass123"))

    def test_reset_url_names_are_unreversable(self):
        for name in ("password_reset_confirm", "password_reset_done", "password_reset_complete"):
            with self.assertRaises(NoReverseMatch):
                reverse(name)


class RestAuthResetRetiredTests(TestCase):
    """django-rest-auth exposed a second, unauthenticated reset surface."""

    def setUp(self):
        User.objects.create_user("qgis", "qgis@example.org", "QgisPass123")
        mail.outbox = []

    def test_rest_auth_reset_endpoints_are_gone(self):
        for path in (
            "/admin/rest-auth/password/reset/",
            "/admin/rest-auth/password/reset/confirm/",
            "/admin/rest-auth/password/change/",
        ):
            response = self.client.post(path, {"email": "qgis@example.org"})
            self.assertEqual(response.status_code, 404, path)
        self.assertEqual(len(mail.outbox), 0)

    def test_rest_auth_login_still_works_for_the_qgis_plugin(self):
        response = self.client.post(
            "/admin/rest-auth/login/", {"username": "qgis", "password": "QgisPass123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("key", response.json())


class AdminSetsPasswordTests(TestCase):
    """The one mechanism that must keep working: admin sets the password."""

    def setUp(self):
        self.staff = User.objects.create_superuser("boss", "boss@example.org", "BossPass123")
        self.user = User.objects.create_user("alice", "alice@example.org", "AlicePass123")
        self.client.force_login(self.staff)

    def test_admin_set_password_form_is_reachable(self):
        url = reverse("admin:auth_user_password_change", args=[self.user.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_can_set_a_strong_password(self):
        url = reverse("admin:auth_user_password_change", args=[self.user.pk])
        self.client.post(url, {"password1": "Brindavan#Shelter42", "password2": "Brindavan#Shelter42"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brindavan#Shelter42"))


class PasswordValidatorTests(TestCase):
    """AUTH_PASSWORD_VALIDATORS now gate every password the admin types."""

    def setUp(self):
        self.user = User.objects.create_user("alice", "alice@example.org", "AlicePass123")

    def assertRejected(self, password):
        form = AdminPasswordChangeForm(self.user, {"password1": password, "password2": password})
        self.assertFalse(form.is_valid(), "expected %r to be rejected" % password)

    def test_short_password_is_rejected(self):
        self.assertRejected("1")

    def test_common_password_is_rejected(self):
        self.assertRejected("password")

    def test_entirely_numeric_password_is_rejected(self):
        self.assertRejected("29481759")

    def test_password_similar_to_the_username_is_rejected(self):
        self.assertRejected("alice1234")

    def test_a_strong_password_is_accepted(self):
        form = AdminPasswordChangeForm(
            self.user, {"password1": "Brindavan#Shelter42", "password2": "Brindavan#Shelter42"}
        )
        self.assertTrue(form.is_valid(), form.errors)
