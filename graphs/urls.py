from django.conf.urls import include, url
from graphs.views import *
from graphs.qol import *

urlpatterns = [
    url(r'^type/(?P<graph_type>\w+)/$',graphs_display, name='graphs_display'),
    url(r'^dashboard/(?P<key>[0-9]+)/$',get_dashboard_card, name='get_dashboard_card'),
    url(r'^card/(?P<key>[0-9]{1,2}|[all]+)/$',dashboard_all_cards, name='get_dashboard_card'),
    url(r'^covid_data/$',covid_data, name='covid_data'),
    url(r'^covid_report/$',give_report_covid_data, name='give_report_covid_data'), # url for coid data
    url(r'^factsheet_data/$',factsheetData, name='factsheetData'),
    url(r'^factsheet_data_download/$',factsheetDataDownload, name='factsheetDataDownload'),   #  url for family factsheet data
    url(r'^member_data/$',member_data, name='member_data'),
    url(r'^show/MemberData/$', MemberDataView, name='MemberDataView'),
]
