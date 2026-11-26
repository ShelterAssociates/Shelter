from django.conf.urls import include, url
from django.contrib import admin
from sponsor.views import *

urlpatterns = [
    url(
        r"^files/(?P<kind>document|image)/(?P<pk>\d+)/$",
        project_file,
        name="sponsor_project_file",
    ),
    url(r"^ffreport/(?P<pk>\d+)/$", ff_report_zip, name="sponsor_ff_report_zip"),
    url(r"^(?P<slumname>.*)/$", create_zip, name="create_zip"),
    url(r"^$", sponsors, name="sponsors"),
]
