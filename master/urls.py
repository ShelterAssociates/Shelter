#!/usr/bin/python
# -*- coding: utf-8 -*-

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

from master.views import index, SurveyListView, SurveyCreateView, \
    survey_delete_view, search

admin.autodiscover()

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^master/', include(admin.site.urls)),
    url(r'^surveymapping/', SurveyListView.as_view(),
        name='SurveyCreate'),
    url(r'^surveymapping/(?P<name>\w[a-zA-Z_0-9]+)/$',
        SurveyListView.as_view(), name="SurveyCreate"),
    url(r'AddSurveyMapping/$', SurveyCreateView.as_view(),
        name='survey-add'),
    url(r'^deletesurvey/(?P<survey>[0-9]+)/$', survey_delete_view,
        name='surveydelete'),
    url(r'Survey/(?P<survey>[0-9]+)/$', SurveyCreateView.as_view(),
        name='survey-update'),
    url(r'^search/(?P<survey>[0-9]+)/$', search, name='search'),
    ]


            