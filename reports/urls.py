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
    url(r'^$', report_view, name='report_home'),
    url(r'^preview-rim-factsheet/(?P<slum_id>[0-9]+)/$', rim_factsheet_preview, name='rim_factsheet_preview'),

    ## Donar report
    url(r'^monthly-report/(?P<report_id>[0-9]+)/$', monthly_report_details, name='monthly_report_details'),
    url(r'^generate-donor-report/(?P<report_id>[0-9]+)/$', monthly_donor_report_pdf_generation, name='generate_donor_report'),
    url(r'^fetch-donor-report/(?P<report_id>[0-9]+)/$', monthly_donor_report_pdf_fetch, name='fetch_donor_report'),
    url(r'^api/donor-projects/$', donor_projects, name='donor_projects_api'),
    url(r'^api/project-months/(?P<project_id>[0-9]+)/$', project_months, name='monthly_report_api'),
]
