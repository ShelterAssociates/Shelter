#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^$', views.kml_upload, name='kml_upload'),
    url(r'^fetchcomponents/(?P<slumid>\w[a-zA-Z_0-9]+)/$', views.fetchcomponentdata, name='fetchcomponentdata'),
]
