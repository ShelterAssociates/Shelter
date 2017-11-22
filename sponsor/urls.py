from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from sponsor.views import *

urlpatterns = [

    url(r'^admin/password_reset/$',auth_views.password_reset,name="password_reset"),
    url(r'^user/password/reset/done/$', auth_views.password_reset_done ,name="password_reset_done" ),
    url(r'^user/password/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', auth_views.password_reset_confirm, name="password_reset_confirm"),
    url(r'^user/password/done/$', auth_views.password_reset_complete, name= "password_reset_complete"),
	url(r'^(?P<slumname>.*)/$', create_zip, name = 'create_zip'),
    url(r'^$', sponsors, name='sponsors'),

]