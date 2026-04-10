from django.conf.urls import include, url
from helpers.views import *
urlpatterns = [
    url(r'^digipin_generate/$',digipin_generate, name='digipin_generate'),
    url(r'^api/send-otp/$',send_otp, name='send_otp'),
    url(r'^api/verify-otp/$',verify_otp, name='verify_otp')
]