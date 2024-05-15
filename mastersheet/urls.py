
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from mastersheet.views import *

urlpatterns = [
    url(r'^report_table_cm_activity_count/$', report_table_cm_activity_count, name="report_table_cm_activity_count"),
    url(r'^report_table_cm/$', report_table_cm, name="report_table_cm"),
	url(r'^report_table/$', give_report_table_numbers, name="give_report_table_numbers"),
    url(r'^report_table_accounts/$', give_report_table_numbers_accounts, name="give_report_table_numbers_accounts"),
	url(r'^details/$', give_details, name="give_details"),
	url(r'^report/$', render_report, name="render_report"),
	url(r'^show/report/$', create_report, name="create_report"),
    url(r'^delete_selected/$', delete_selected, name="delete_selected"),
    url(r'^files/$', file_ops, name="file_ops"),
    url(r'^columns/$', define_columns, name="define_columns"),
    url(r'^show/mastersheet/$', renderMastersheet, name="renderMastersheet"),
    url(r'^list/show/$', masterSheet, name="masterSheet"),
    url(r'^sync/slum/$', sync_kobo_data, name='sync_kobo_data'),
    url(r'^account/excel/$', accounts_excel_generation, name='accounts_excel_generation'),
    url(r'^show/summery/$', renderSummery, name="renderSummery"),
    url(r'^show/showSummery/$', ProcessShortView, name='ProcessShortView'),
    url(r'^gisDataDownload/$', gisDataDownload, name='gisDataDownload'),
    url(r'^addSponsor/$', addSponsor, name='gisDataDownload'),
    url(r'^sponsorprojectList/$', sponsorprojectList, name = 'sponsorprojectList'),
]