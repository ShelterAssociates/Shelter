import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from shelter.auth_throttle import ThrottledAuthenticationForm

logger = logging.getLogger(__name__)


class SiteLoginView(LoginView):
    """Signed-in users never get the form. Only staff-only checks send them here, so non-staff with ?next= get a 403."""

    authentication_form = ThrottledAuthenticationForm

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().get(request, *args, **kwargs)
        requested = self.get_redirect_url()
        if not requested:
            return redirect(settings.LOGIN_REDIRECT_URL)
        if request.user.is_staff:
            return redirect(requested)
        return render(request, "403.html", {"requested": requested}, status=403)


class SiteLogoutView(LogoutView):
    """Signs out, then back to the login page with a thank-you note."""

    next_page = "login"

    def dispatch(self, request, *args, **kwargs):
        was_signed_in = request.user.is_authenticated
        response = super().dispatch(request, *args, **kwargs)
        if was_signed_in:
            messages.success(request, "You have been signed out. Thank you for using Shelter Associates.")
        return response


@csrf_exempt
@require_POST
def csp_report(request):
    """Browsers post Content-Security-Policy violations here; they are logged, nothing is stored."""
    try:
        report = json.loads(request.body[:4096].decode("utf-8", "replace")).get("csp-report", {})
    except (ValueError, AttributeError):
        report = {}
    directive = str(report.get("violated-directive") or report.get("effective-directive") or "")
    source = str(report.get("source-file") or "")
    logger.warning(
        "CSP violation: %r blocked %r on %r (source %r line %r sample %r)",
        directive[:100],
        str(report.get("blocked-uri") or "")[:200],
        str(report.get("document-uri") or "")[:200],
        source[:200],
        report.get("line-number"),
        str(report.get("script-sample") or "")[:80],
    )
    return HttpResponse(status=204)
