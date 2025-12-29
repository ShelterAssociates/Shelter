from django.conf.urls import include, url
from .views import rim_factsheet_html_view

urlpatterns = [
    url('^api/rim_factsheet/(?P<slum_id>[0-9]+)/$', rim_factsheet_html_view, name='rim_factsheet_api_base'),
]