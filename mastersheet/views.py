
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, JsonResponse
from mastersheet.forms import find_slum

from django import forms


from sponsor.models import *
from master.models import *
from django.views.decorators.csrf import csrf_exempt
import json

import urllib2


# Create your views here.
def masterSheet(request):
    print "In masterSheet view...."
    urlv = ''
    print ("Sending Request to", urlv)
    kobotoolbox_request = urllib2.Request(urlv)
    kobotoolbox_request.add_header('Authorization', "OAuth2 ")
    res = urllib2.urlopen(kobotoolbox_request)
    html = res.read()
    formdict = json.loads(html)
    return HttpResponse(json.dumps(formdict), content_type = "application/json")

def renderMastersheet(request):
    print "In renderMastersheet view"
    slum_search_field = find_slum()
    return render(request, 'masterSheet.html', {'form':slum_search_field})







