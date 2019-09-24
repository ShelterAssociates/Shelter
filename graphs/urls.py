from django.conf.urls import include, url
from graphs.views import *

urlpatterns = [
    url(r'^type/(?P<graph_type>\w+)/$',graphs_display, name='graphs_display'),
    url(r'^dashboard/(?P<key>[0-9]+)/$',get_dashboard_card, name='get_dashboard_card'),
    url(r'^card/(?P<key>[0-9]{1,2}|[all]+)/$',dashboard_all_cards, name='get_dashboard_card'),
]
