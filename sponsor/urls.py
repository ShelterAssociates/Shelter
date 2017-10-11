from django.conf.urls import include, url
from django.contrib import admin


from sponsor.views import sponsors

urlpatterns = [
    url(r'^$', sponsors, name='sponsors'),
]