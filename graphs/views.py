from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from master.models import *


@login_required(login_url='/accounts/login/')
def community_mobilization_graphs(request):
    custom_url = settings.GRAPHS_BUILD_URL % settings.GRAPH_DETAILS[0][1::-1]
    return render(request, 'community_mobilization.html', {'custom_url':custom_url})