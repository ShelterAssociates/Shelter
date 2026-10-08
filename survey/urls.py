from django.conf.urls import url

from . import views

app_name = "survey"

urlpatterns = [
    url(r"^$", views.slum_versions, name="slum_versions"),
    url(r"^(?P<slum_id>[0-9]+)/$", views.slum_versions, name="slum_detail"),
    url(r"^(?P<slum_id>[0-9]+)/settings/$", views.save_settings, name="save_settings"),
    url(r"^(?P<slum_id>[0-9]+)/locations/add/$", views.add_location, name="add_location"),
    url(r"^(?P<slum_id>[0-9]+)/locations/remove/$", views.remove_location, name="remove_location"),
    url(r"^(?P<slum_id>[0-9]+)/locations/primary/$", views.make_primary, name="make_primary"),
    url(r"^(?P<slum_id>[0-9]+)/version/start/$", views.start_version, name="start_version"),
    url(r"^(?P<slum_id>[0-9]+)/version/backfill/$", views.backfill_backup, name="backfill_backup"),
    url(r"^(?P<slum_id>[0-9]+)/merge/$", views.merge_slum, name="merge_slum"),
]
