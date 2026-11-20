from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security)
def allowed_hosts_are_explicit(app_configs, **kwargs):
    """VAPT #7: outside development the app answers only for its own hostnames."""
    if settings.DEBUG:
        return []
    hosts = list(settings.ALLOWED_HOSTS)
    if not hosts or "*" in hosts:
        return [Error(
            "ALLOWED_HOSTS is %r; with DEBUG off it must list this server's hostnames only." % hosts,
            hint="Set it in shelter/local_settings.py, e.g. ALLOWED_HOSTS = ['uat.shelter-associates.org'].",
            id="shelter.E001",
        )]
    base_host = urlparse(getattr(settings, "BASE_APP_URL", "") or "").hostname
    if not base_host or base_host not in hosts:
        return [Warning(
            "BASE_APP_URL (%r) is not one of ALLOWED_HOSTS; emailed links are built from it."
            % getattr(settings, "BASE_APP_URL", ""),
            hint="Set BASE_APP_URL to this server's https:// address in shelter/local_settings.py.",
            id="shelter.W001",
        )]
    return []
