from django.conf.urls import include, url
from graphs.views import *

urlpatterns = [
    url(r'^community_mobilization/$',community_mobilization_graphs, name='community_mobilization_graphs'),
]