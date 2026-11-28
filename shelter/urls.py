"""Project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import include, url
from django.contrib import admin
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.conf import settings
from django.http import HttpResponseForbidden
from shelter.views import SiteLoginView, SiteLogoutView, csp_report
from .settings import *
from master.views import (
    slummap,
    city_wise_map,
    city_wise_map_base64,
    login_success,
    dashboard_view,
)
from rest_framework import urls
from master.api import CityViewset
from component.api import MetadataViewSet
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

admin.autodiscover()

router = routers.DefaultRouter()
router.register(r"metadata", MetadataViewSet)
router.register(r"city", CityViewset)

# Mirrors the nginx /media deny rules for runserver; in production nginx serves /media.
PRIVATE_MEDIA = (
    r"^media/(?:(?:FFReport|gis_exports|rim_exports|sponsor_project|photo_exports|shelter/attachments"
    r"|avni_bulk_updates|job_reports|slum_merges|plate_[^/]*|design_[^/]*)/.*|[^/]+\.zip)$"
)


def private_media(request):
    return HttpResponseForbidden()


base64_pattern = r"city::(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)"
urlpatterns = (
    [
        url(r"^$", slummap, name="slummap"),
        url(r"^home/", login_success, name="login_success"),
        # Self-service password reset and change are retired: both names render a
        # static page pointing at the administrator, and the token routes are
        # gone so links already emailed no longer work. The admin's own
        # set-password form (/accounts/auth/user/<id>/password/) is a separate
        # route and is unaffected -- that is how passwords get changed now.
        url(
            r"^accounts/login/$",
            SiteLoginView.as_view(),
            name="login",
        ),
        url(r"^accounts/logout/$", SiteLogoutView.as_view(), name="logout"),
        url(
            r"^accounts/password_reset/$",
            TemplateView.as_view(
                template_name="registration/password_reset_contact.html"
            ),
            name="password_reset",
        ),
        url(
            r"^accounts/password_change/$",
            TemplateView.as_view(
                template_name="registration/password_reset_contact.html"
            ),
            name="password_change",
        ),
        url(r"^accounts/", admin.site.urls),
        url(
            r"^(?P<key>{})$".format(base64_pattern),
            city_wise_map_base64,
            name="city_map_base64",
        ),
        url(
            r"^(?P<key>{})/(?P<slumname>.*)$".format(base64_pattern),
            city_wise_map_base64,
            name="city_map_base64",
        ),
        url(r"^(?P<key>city::([A-Za-z0-9 ]*)?)$", city_wise_map, name="city_map"),
        url(
            r"^(?P<key>city::([A-Za-z0-9 ]*)?)/(?P<slumname>.*)$",
            city_wise_map,
            name="city_mapp",
        ),
        url(
            r"^dashboard/(?P<key>city::([A-Za-z0-9 ]*)?)$",
            dashboard_view,
            name="dashboard_view",
        ),
        url(
            r"^admin/",
            include(("master.urls", "master"), namespace="master"),
            name="master",
        ),
        url(r"^component/", include("component.urls")),
        url(r"^sponsor/", include("sponsor.urls")),
        url(r"^mastersheet/", include("mastersheet.urls")),
        url(r"^graphs/", include("graphs.urls")),
        # Setting URL for Helper functions (Digipin Generation , Sync Data)
        url(r"^helpers/", include("helpers.urls")),
        ## setting up url for reprot generation
        url(r"^reports/", include("reports.urls")),
        # Internal-only browser for Avni household photos
        url(r"^photos/", include("photos.urls")),
        # Internal-only AVNI sync console (manual syncs, bulk updates into AVNI)
        url(r"^avni-console/", include("avni_console.urls")),
        url(r"^design-studio/", include("design_studio.urls")),
        # Old Plates address (links in emails already sent): same page under /design-studio/.
        url(r"^plates/(?P<rest>.*)$", RedirectView.as_view(url="/design-studio/%(rest)s", permanent=True, query_string=True)),
        # Internal-only, superusers: slum data versions, AVNI locations, per-slum sync
        url(r"^slum-versions/", include("survey.urls")),
        # Setting URL for QGIS plugin login
        url("api-token-auth/", obtain_auth_token, name="api_token_auth"),
        url("api/", include(router.urls)),
        url(r"^csp-report/$", csp_report, name="csp_report"),
        url(PRIVATE_MEDIA, private_media),
    ]
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
)

admin.site.site_header = settings.ADMIN_SITE_HEADER
# Tab titles read "SA | <page> | Shelter Associates" on Django admin pages (templates/admin/base.html adds "SA | ").
admin.site.site_title = "Shelter Associates"
