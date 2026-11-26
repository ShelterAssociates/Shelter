"""Brute-force protection for every password check (login page, rest-auth, API token, HTTP Basic) and the OTP form."""

import logging

from django.contrib.auth import get_user_model, user_logged_in, user_login_failed
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import caches
from django.core.exceptions import PermissionDenied, ValidationError
from django.dispatch import receiver

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 15 * 60
USER_LIMIT = 5
IP_LIMIT = 20
OTP_LIMIT = 5
TRUSTED_PROXIES = ("127.0.0.1", "::1")
LOCKED_MESSAGE = "Too many failed sign-in attempts. Please wait 15 minutes and try again."


def _cache():
    return caches["auth_throttle"]


def client_ip(request):
    """The address nginx saw (rightmost X-Forwarded-For entry) when the request came through the local proxy."""
    if request is None:
        return ""
    remote = request.META.get("REMOTE_ADDR", "")
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded and remote in TRUSTED_PROXIES:
        return forwarded.split(",")[-1].strip()
    return remote


def _keys(username, request):
    keys = []
    if username:
        keys.append(("user:" + str(username).strip().lower(), USER_LIMIT))
    ip = client_ip(request)
    if ip:
        keys.append(("ip:" + ip, IP_LIMIT))
    return keys


def failures(key):
    return _cache().get(key, 0)


def add_failure(key):
    count = failures(key) + 1
    _cache().set(key, count, WINDOW_SECONDS)
    return count


def is_locked(username, request):
    return any(failures(key) >= limit for key, limit in _keys(username, request))


def otp_blocked(email, task):
    return failures("otp:%s:%s" % (str(email).lower(), task)) >= OTP_LIMIT


def add_otp_failure(email, task):
    return add_failure("otp:%s:%s" % (str(email).lower(), task))


class ThrottledModelBackend(ModelBackend):
    """ModelBackend that refuses to check a password while the username or client IP is locked."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if is_locked(username, request):
            raise PermissionDenied(LOCKED_MESSAGE)
        return super().authenticate(request, username=username, password=password, **kwargs)


class ThrottledAuthenticationForm(AuthenticationForm):
    def clean(self):
        if is_locked(self.cleaned_data.get("username"), self.request):
            raise ValidationError(LOCKED_MESSAGE, code="locked")
        return super().clean()


@receiver(user_login_failed, dispatch_uid="count_failed_login")
def count_failed_login(sender, credentials, request=None, **kwargs):
    username = credentials.get("username")
    for key, limit in _keys(username, request):
        if add_failure(key) == limit:
            logger.warning("Sign-in locked for 15 minutes: %s reached %d failed attempts", key, limit)


@receiver(user_logged_in, dispatch_uid="clear_failed_logins")
def clear_failed_logins(sender, request, user, **kwargs):
    _cache().delete("user:" + user.get_username().strip().lower())
