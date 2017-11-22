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
from django.views.generic.base import View
from master.views import index, SurveyListView, SurveyCreateView, \
    survey_delete_view, search, rimedit, rimdisplay, riminsert, report, \
    administrativewardList, electoralWardList, slumList, rimreportgenerate, \
    vulnerabilityreport,formList,slummapdisplay,slummap,citymapdisplay, \
    modelmapdisplay, drainageinsert, sluminformation, drainagedisplay , \
    drainageedit, cityList, drainagereportgenerate, modelList, \
    familyrportgenerate, user_login, iframeuser, user_login2

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import login, logout, password_reset, password_reset_done, password_reset_confirm
from django.contrib.auth import views as auth_views
admin.autodiscover()

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^master/', include(admin.site.urls)),
    url(r'^surveymapping/', SurveyListView.as_view(),name='SurveyCreate'),
    url(r'^surveymapping/(?P<name>\w[a-zA-Z_0-9]+)/$', SurveyListView.as_view(), name="SurveyCreate"),
    url(r'survey/$', SurveyCreateView.as_view(),name='survey-add'),
    url(r'^deletesurvey/(?P<survey>[0-9]+)/$', survey_delete_view, name='surveydelete'),
    url(r'survey/(?P<survey>[0-9]+)/$', SurveyCreateView.as_view(), name='survey-update'),
    url(r'^search/$', search, name="search"),
    url(r'^sluminformation/rim/edit/(?P<Rapid_Slum_Appraisal_id>\d+)$', rimedit, name='rimedit'),
    url(r'^sluminformation/rim/display/$', rimdisplay, name='rimdisplay'),
    url(r'^sluminformation/rim/insert/$', riminsert, name='riminsert'),
    url(r'^report/$', report, name='report'),
    url(r'^administrativewardList/$', administrativewardList, name='administrativewardList'),
    url(r'^electoralWardList/$',electoralWardList, name='electoralWardList'),
    url(r'^slumList/$',slumList, name='slumList'),
    url(r'^rimreportgenerate/$',rimreportgenerate, name='rimreportgenerate'),
    url(r'^vulnerabilityReport/$',vulnerabilityreport, name='vulnerabilityReport'),
    url(r'^formList/$',formList, name='formList'),
    url(r'^slummap/$',slummap, name='slummap'),
    url(r'^slummapdisplay/(?P<id>[0-9]+)/$',slummapdisplay, name='slummapdisplay'),
    url(r'^citymapdisplay/$',citymapdisplay, name='citymapdisplay'),
    url(r'^modelmapdisplay/$',modelmapdisplay, name='modelmapdisplay'),
     url(r'^sluminformation/$',sluminformation, name='sluminformation'),
    url(r'^sluminformation/drainage/display/$',drainagedisplay, name='drainagedisplay'),
    url(r'^sluminformation/drainage/insert/$',drainageinsert, name='drainageinsert'),
    url(r'^sluminformation/drainage/edit/(?P<drainage_id>\d+)$', drainageedit, name='drainageedit'),
    url(r'^cityList/$', cityList, name='cityList'),
    url(r'^drainagereportgenerate/$', drainagereportgenerate, name='drainagereportgenerate'),
    url(r'^modelList/$', modelList, name='modelList'),
    url(r'^familyrportgenerate/$', familyrportgenerate, name='familyrportgenerate'),
   # url(r'^slummap/component/fetchcomponents', include('component.urls')),
    url(r'^user_login/$',user_login, name='user_login'),
    #url(r'^user_logout/$',user_logout, name='user_logout'),
    url(r'^iframeuser/$',iframeuser, name='iframeuser'),
    url(r'^user_login2/$',user_login2, name='user_login2'),

  
    #url(r'^sponsors/$',sponsors, name='sponsors'),
    #url(r'^password_reset/$', auth_views.password_reset, name='password_reset'),
    #url(r'^password_reset/done/$', auth_views.password_reset_done, name='password_reset_done'),
    #url(r'^reset-password/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
    #    auth_views.password_reset_confirm, name='password_reset_confirm'),
    #url(r'^reset/done/$', auth_views.password_reset_complete, name='password_reset_complete'),     
    url('^', include('django.contrib.auth.urls')),
    url(r'^logout/$', 'django.contrib.auth.views.logout'),

]
    