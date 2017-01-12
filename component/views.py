from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages

from itertools import groupby
import json
from .forms import KMLUpload
from .kmlparser import KMLParser
from .models import Metadata, Component
from master.models import Slum

def kml_upload(request):
    if request.method == 'POST':
        form = KMLUpload(request.POST or None,request.FILES)
        if form.is_valid():
            docFile = request.FILES['kml_file'].read()
            print form.cleaned_data
            objKML = KMLParser(docFile, form.cleaned_data['slum_name'])
            messages.success(request,'Form submission successful')
    else:
        form = KMLUpload()
    return render(request, 'kml_upload.html', {'form': form})

def get_component(request, slum_id):
    slum = Slum.objects.get(pk=slum_id)
    metadata = Metadata.objects.filter(visible=True).order_by('type')
    lstcomponent = []
    for metad in metadata:
        component = {}
        component['name'] = metad.name
        component['level'] = metad.level
        component['section'] = metad.section.name
        component['type'] = metad.type
        component['order'] = metad.order
        component['blob'] = metad.blob
        component['child'] = []
        if metad.type == 'C':
            for comp in metad.component_set.filter(slum=slum):
                component['child'].append({'housenumber':comp.housenumber, 'shape':json.loads(comp.shape.json)})
        lstcomponent.append(component)

    dtcomponent = {}
    for key, comp in  groupby(lstcomponent, key=lambda x:x['section']):
        if key not in dtcomponent:
            dtcomponent[key] = {}
        for c in comp:
            dtcomponent[key][c['name']] = c

    return HttpResponse(json.dumps(dtcomponent),content_type='application/json')


def get_kobo_data(request, slum_id):
   pass
   