#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from . import views ,get_component_api

base64_pattern = r'(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$'
urlpatterns = [
    url(r'^$', views.kml_upload, name='kml_upload'),
    url(r'^get_component/(?P<slum_id>\d+)$', get_component_api.get_component_api, name='get_component'),
    url(r'^get_kobo_RIM_data/(?P<slum_id>\d+)$', views.get_kobo_RIM_data, name='get_kobo_RIM_data'),
    url(r'^get_kobo_RHS_list/(?P<slum_id>\d+)/(?P<house_num>\d+)$', views.get_kobo_RHS_data, name='get_kobo_RHS_data'),
    url(r'^get_kobo_RIM_report_data/(?P<slum_id>\d+)$', views.get_kobo_RIM_report_data, name='get_kobo_RIM_report_data'),
    url(r'^get_kobo_FF_report_data/(?P<key>{})'.format(base64_pattern), views.get_kobo_FF_report_data, name='get_kobo_FF_report_data'),
    url(r'^get_kobo_drainage_report_data/(?P<slum_id>\d+)$', views.get_kobo_drainage_report_data, name='get_kobo_drainage_report_data'),
]
