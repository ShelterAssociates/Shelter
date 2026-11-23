import os
import shlex
from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security)
def allowed_hosts_are_explicit(app_configs, **kwargs):
    """Outside development the app answers only for its own hostnames."""
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


PROD_HOSTS = {"app.shelter-associates.org", "report.shelter-associates.org", "graphs.shelter-associates.org"}


@register(Tags.security)
def environment_is_not_mixed(app_configs, **kwargs):
    """A non-prod server must not send people to, or embed, prod's BIRT or Superset."""
    base_host = urlparse(getattr(settings, "BASE_APP_URL", "") or "").hostname
    if settings.DEBUG or not (base_host or "").endswith(".shelter-associates.org") or base_host in PROD_HOSTS:
        return []
    mixed = ["%s = %r" % (name, value) for name in ("BIRT_REPORT_URL", "GRAPHS_PUBLIC_URL")
             for value in [getattr(settings, name, "") or ""] if urlparse(value).hostname in PROD_HOSTS]
    if mixed:
        return [Warning(
            "This server is %s but points at prod: %s." % (base_host, ", ".join(mixed)),
            hint="Use this server's own BIRT/Superset addresses in shelter/local_settings.py "
                 "(UAT: https://uat-report.shelter-associates.org/, https://uat-graphs.shelter-associates.org/).",
            id="shelter.W002",
        )]
    return []


@register()
def birt_report_design_exists(app_configs, **kwargs):
    """The household factsheet ZIPs fail if BIRT_REPORT_CMD names a design file that is not there."""
    command = getattr(settings, "BIRT_REPORT_CMD", "") or ""
    if settings.DEBUG or not command:
        return []
    designs = [arg for arg in shlex.split(command) if arg.endswith(".rptdesign")]
    missing = [path for path in designs if not os.path.exists(path)]
    if missing:
        return [Warning(
            "BIRT_REPORT_CMD uses %s, which does not exist on this server." % ", ".join(missing),
            hint="Point it at the FFReport.rptdesign this server has, e.g. /var/lib/tomcat7/webapps/Birt/FFReport.rptdesign.",
            id="shelter.W003",
        )]
    return []
