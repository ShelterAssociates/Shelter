import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


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
