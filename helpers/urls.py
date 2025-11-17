from django.conf.urls import include, url
from helpers.views import *
urlpatterns = [
    url(r'^digipin_generate/$',digipin_generate, name='digipin_generate'),
]