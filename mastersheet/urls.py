
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from mastersheet.views import *

urlpatterns = [
    url(r'^show/mastersheet/$', renderMastersheet, name="renderMastersheet"),
    url(r'^list/show/$', masterSheet, name="masterSheet"),
    #url(r'^$', masterSheet, name='masterSheet'),

]