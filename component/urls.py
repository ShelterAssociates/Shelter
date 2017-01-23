#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^$', views.kml_upload, name='kml_upload'),
    url(r'^get_component/(?P<slum_id>\d+)$', views.get_component, name='get_component'),
    url(r'^get_kobo_RIM_data/(?P<slum_id>\d+)$', views.get_kobo_RIM_data, name='get_kobo_RIM_data'),
    url(r'^get_kobo_FF_data/(?P<slum_id>\d+)/(?P<house_num>\d+)$', views.get_kobo_FF_data, name='get_kobo_FF_data'),


]
