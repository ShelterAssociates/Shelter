from django.conf.urls import url

from . import views

app_name = "avni_console"

urlpatterns = [
    url(r"^$", views.index, name="index"),
    url(r"^dry-run/rhs/$", views.dry_run_rhs, name="dry_run_rhs"),
    url(r"^queue/(?P<job_key>[a-z_]+)/$", views.queue_job, name="queue"),
    url(r"^runs/$", views.runs, name="runs"),
    url(r"^runs/(?P<pk>[0-9]+)/$", views.run_detail, name="run_detail"),
    url(r"^runs/(?P<pk>[0-9]+)/detail-file/$", views.run_detail_file, name="run_detail_file"),
    url(r"^runs/(?P<pk>[0-9]+)/changes\.csv$", views.run_changes_csv, name="run_changes_csv"),
    url(r"^forms/levels\.json$", views.levels_json, name="levels_json"),
    url(r"^forms/(?P<pk>[0-9]+)/questions\.json$", views.questions_json, name="questions_json"),
    url(r"^forms/(?P<pk>[0-9]+)/template\.xlsx$", views.template_xlsx, name="template_xlsx"),
    url(r"^bulk/new/$", views.bulk_new, name="bulk_new"),
    url(r"^bulk/(?P<pk>[0-9]+)/preview/$", views.bulk_preview, name="bulk_preview"),
    url(r"^bulk/(?P<pk>[0-9]+)/$", views.bulk_detail, name="bulk_detail"),
]
