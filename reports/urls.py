from django.conf.urls import url
from .views import *
from django.http import HttpResponse
app_name = 'reports'  

urlpatterns = [
    url(r'^api/rim_factsheet_generation/(?P<slum_id>[0-9]+)/$',rim_factsheet_pdf_generation,name='rim_factsheet_pdf_generating'),
    url(
        r'^api/rim_factsheet_pdf_fetch/(?P<slum_id>[0-9]+)/$',rim_factsheet_pdf_fetch,name='rim_factsheet_pdf_fetching'),
    url(r'^test/$', lambda r: HttpResponse("OK")),
    url(
        r'^rim_factsheet/html/(?P<slum_id>[0-9]+)/$',
        rim_factsheet_html_report,
        name='rim_factsheet_html'
    ),
    url(r'^rim/$', report_view, name='rim_report_home'),
    url(r'^preview-rim-factsheet/(?P<slum_id>[0-9]+)/$', rim_factsheet_preview, name='rim_factsheet_preview'),

    ## Donar report
    url(r'^donor/$', donor_report_home, name='donar_report_home'),
]
