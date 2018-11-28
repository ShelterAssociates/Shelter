from django.conf.urls import include, url
from graphs.views import *

urlpatterns = [
    url(r'^type/(?P<graph_type>\w+)/$',graphs_display, name='graphs_display'),
]