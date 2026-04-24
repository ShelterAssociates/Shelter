from django.conf.urls import include, url
from helpers.views import *
urlpatterns = [
    url(r'^digipin_generate/$',digipin_generate, name='digipin_generate'),
    url(r'^photo-upload/$',photo_upload_page, name='photo_upload_page'),
    url(r'^api/send-otp/$',send_otp, name='send_otp'),
    url(r'^api/verify-otp/$',verify_otp, name='verify_otp'),
    url(r'^api/upload-slum-photos-to-drive/$',upload_slum_photos_to_drive, name='upload_slum_photos_to_drive')
]
