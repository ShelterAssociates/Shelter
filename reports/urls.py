from django.conf.urls import url
from .views import rim_factsheet_pdf_proxy , rim_factsheet_html_report
from django.http import HttpResponse

urlpatterns = [
    url(
        r'^api/rim_factsheet/(?P<slum_id>[0-9]+)/$',
        rim_factsheet_pdf_proxy,
        name='rim_factsheet_pdf'
    ),
    url(r'^test/$', lambda r: HttpResponse("OK")),
    url(
        r'^rim_factsheet/html/(?P<slum_id>[0-9]+)/$',
        rim_factsheet_html_report,
        name='rim_factsheet_html'
    ),
]
