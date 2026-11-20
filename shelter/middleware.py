import hashlib
import logging
import secrets
import time

from django.conf import settings
from django.contrib.auth import logout, user_logged_in, user_logged_out
from django.contrib.auth.views import redirect_to_login
from django.dispatch import receiver

logger = logging.getLogger("request_logger")

SENSITIVE_KEYS = ("password", "otp", "token", "secret", "csrfmiddlewaretoken")


def redact(querydict):
    """Copy of the params with credential-like values masked."""
    return {
        k: "***" if any(part in k.lower() for part in SENSITIVE_KEYS) else v
        for k, v in dict(querydict).items()
    }


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        logger.info(
            "REQUEST: method=%s path=%s GET=%s POST=%s",
            request.method,
            request.path,
            redact(request.GET),
            redact(request.POST),
        )

        response = self.get_response(request)

        # request.user is only reliably set AFTER get_response runs,
        # since AuthenticationMiddleware executes deeper in the chain.
        user = getattr(request, "user", None)
        username = getattr(user, "username", "Anonymous") if user and user.is_authenticated else "Anonymous"

        duration = time.time() - start_time
        logger.info(
            "RESPONSE: method=%s path=%s status=%s duration=%.3fs user=%s",
            request.method,
            request.path,
            response.status_code,
            duration,
            username,
        )

        return response


SESSION_FINGERPRINT_KEY = "_client_fingerprint"
SESSION_DEVICE_KEY = "_device_binding"
DEVICE_COOKIE = "sa_device"


def client_fingerprint(request):
    return hashlib.sha256(request.META.get("HTTP_USER_AGENT", "").encode("utf-8")).hexdigest()


def _digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@receiver(user_logged_in, dispatch_uid="bind_session_to_client")
def bind_session_to_client(sender, request, user, **kwargs):
    if request is not None and hasattr(request, "session"):
        request.session[SESSION_FINGERPRINT_KEY] = client_fingerprint(request)
        # The device cookie is issued on the way out, so it lands in the same response as the new session.
        request.rebind_device = True


@receiver(user_logged_out, dispatch_uid="unbind_session_from_client")
def unbind_session_from_client(sender, request, user, **kwargs):
    if request is not None:
        request.unbind_device = True


class SessionBindingMiddleware:
    """Ties a logged-in session to its browser (User-Agent + a device cookie set at login); a mismatch ends it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            reason = self._rejection(request)
            if reason:
                logger.warning("Session for user=%s rejected: %s (path=%s)", user.username, reason, request.path)
                logout(request)
                response = redirect_to_login(request.get_full_path())
                response.delete_cookie(DEVICE_COOKIE)
                return response
        response = self.get_response(request)
        if getattr(request, "unbind_device", False):
            response.delete_cookie(DEVICE_COOKIE)
        if getattr(request, "rebind_device", False) and request.user.is_authenticated:
            token = secrets.token_urlsafe(32)
            request.session[SESSION_DEVICE_KEY] = _digest(token)
            response.set_cookie(
                DEVICE_COOKIE, token, httponly=True, secure=settings.SESSION_COOKIE_SECURE, samesite="Lax"
            )
        return response

    def _rejection(self, request):
        session = request.session
        fingerprint = session.get(SESSION_FINGERPRINT_KEY)
        if fingerprint is None:
            session[SESSION_FINGERPRINT_KEY] = client_fingerprint(request)
        elif fingerprint != client_fingerprint(request):
            return "browser fingerprint changed"
        device = session.get(SESSION_DEVICE_KEY)
        if device is None:
            request.rebind_device = True
        elif device != _digest(request.COOKIES.get(DEVICE_COOKIE, "")):
            return "device cookie missing or wrong"
        return None


class CookieFlagsMiddleware:
    """Every cookie the app sends, deletions included, is HttpOnly, SameSite=Lax and (outside DEBUG) Secure."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        secure = settings.SESSION_COOKIE_SECURE or not settings.DEBUG
        for morsel in response.cookies.values():
            morsel["httponly"] = True
            morsel["samesite"] = morsel["samesite"] or "Lax"
            if secure:
                morsel["secure"] = True
        return response


class ContentSecurityPolicyMiddleware:
    """Adds settings.CSP_POLICY, with a fresh script nonce, to responses that do not set their own policy."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(18)
        response = self.get_response(request)
        if "Content-Security-Policy" in response or "Content-Security-Policy-Report-Only" in response:
            return response
        directives = {name: list(values) for name, values in settings.CSP_POLICY.items()}
        directives.setdefault("script-src", ["'self'"]).append("'nonce-%s'" % request.csp_nonce)
        policy = "; ".join(" ".join([name] + values) for name, values in directives.items())
        if settings.CSP_REPORT_URI:
            policy += "; report-uri " + settings.CSP_REPORT_URI
        header = "Content-Security-Policy-Report-Only" if settings.CSP_REPORT_ONLY else "Content-Security-Policy"
        response[header] = policy
        return response
