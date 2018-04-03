
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from mastersheet.views import *

urlpatterns = [
    url(r'^delete_selected/$', delete_selected, name="delete_selected"),
    url(r'^files/$', file_ops, name="file_ops"),
    url(r'^columns/$', define_columns, name="define_columns"),
    url(r'^buttons/$', define_buttons, name="define_buttons"),
    url(r'^show/mastersheet/$', renderMastersheet, name="renderMastersheet"),
    url(r'^list/show/$', masterSheet, name="masterSheet"),
    #url(r'^$', masterSheet, name='masterSheet'),
    url(r'^sync/slum/(?P<slum_id>\d+)$', sync_kobo_data, name='sync_kobo_data')

]