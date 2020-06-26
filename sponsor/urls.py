from django.conf.urls import include, url
from django.contrib import admin
from sponsor.views import *

urlpatterns = [
	url(r'^(?P<slumname>.*)/$', create_zip, name = 'create_zip'),
    url(r'^$', sponsors, name='sponsors'),
]