from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings

from itertools import groupby
import json
from collections import OrderedDict
from kobotoolbox import *

from .forms import KMLUpload
from .kmlparser import KMLParser
from .models import Metadata, Component
from master.models import Slum, Rapid_Slum_Appraisal, drainage
from sponsor.models import SponsorProjectDetails

#@staff_member_required
@user_passes_test(lambda u: u.is_superuser)
def kml_upload(request):
    context_data = {}
    if request.method == 'POST':
        form = KMLUpload(request.POST or None,request.FILES)
        if form.is_valid():
            docFile = request.FILES['kml_file'].read()
            objKML = KMLParser(docFile, form.cleaned_data['slum_name'], form.cleaned_data['delete_flag'])
            try:
                parsed_data = objKML.other_components()
                context_data['parsed'] = [k for k,v in parsed_data.items() if v==True]
                context_data['unparsed'] = [k for k,v in parsed_data.items() if v==False]
                messages.success(request,'KML uploaded successfully')
            except Exception as e:
                messages.error(request, 'Some error occurred while parsing. KML file is not in the required format ('+str(e)+')')
    else:
        form = KMLUpload()
    metadata_component = Metadata.objects.filter(type='C').values_list('code', flat=True)
    context_data['component'] = metadata_component
    context_data['form'] = form
    return render(request, 'kml_upload.html', context_data)

#@user_passes_test(lambda u: u.is_superuser)
def get_component(request, slum_id):
    slum = get_object_or_404(Slum, pk=slum_id)
    metadata = Metadata.objects.filter(visible=True).order_by('section__order','order')
    rhs_analysis = {}
    try:
        #Fetch RHS data from kobotoolbox
        fields_code = metadata.filter(type='F').exclude(code="").values_list('code', flat=True)
        fields = list(set([str(x.split(':')[0]) for x in fields_code]))
        rhs_analysis = get_household_analysis_data(slum.electoral_ward.administrative_ward.city.id, slum.shelter_slum_code, fields)
    except Exception as e:
        pass

    lstcomponent = []
    for metad in metadata:
        component = {}
        component['name'] = metad.name
        component['level'] = metad.level
        component['section'] = metad.section.name
        component['section_order'] = metad.section.order
        component['type'] = metad.type
        component['order'] = metad.order
        component['blob'] = metad.blob
        component['child'] = []
        if metad.type == 'C':
            for comp in metad.component_set.filter(slum=slum):
                component['child'].append({'housenumber':comp.housenumber, 'shape':json.loads(comp.shape.json)})
        elif metad.type == 'F':
            if metad.code != "":
                field = metad.code.split(':')
                if field[0] in rhs_analysis and field[1] in rhs_analysis[field[0]]:
                    component['child'] = rhs_analysis[field[0]][field[1]]
            else:
                if slum_id + '_'+ metad.name in settings.SPONSOR:
                    component['child'] = settings.SPONSOR[slum_id + '_' + metad.name]
        if len(component['child']) > 0:
            component['count']=len(component['child'])
            lstcomponent.append(component)
    #lstcomponent = sorted(lstcomponent, key=lambda x:x['section_order'])
    dtcomponent = OrderedDict()
    for key, comp in  groupby(lstcomponent, key=lambda x:x['section']):
        if key not in dtcomponent:
            dtcomponent[key] = OrderedDict()
        for c in comp:
            dtcomponent[key][c['name']] = c
    return HttpResponse(json.dumps(dtcomponent),content_type='application/json')

@user_passes_test(lambda u: u.is_superuser)
def get_kobo_RHS_data(request, slum_id,house_num):
     slum = get_object_or_404(Slum, pk=slum_id)
     output = get_kobo_RHS_list(slum.electoral_ward.administrative_ward.city.id, slum.shelter_slum_code, house_num)
     if 'admin_ward' in output:
         output['admin_ward'] = slum.electoral_ward.administrative_ward.name
         output['slum_name'] = slum.name
     return HttpResponse(json.dumps(output),content_type='application/json')

#@user_passes_test(lambda u: u.is_superuser)
def get_kobo_RIM_data(request, slum_id):

    slum = get_object_or_404(Slum, pk=slum_id)
    output = get_kobo_RIM_detail(slum.electoral_ward.administrative_ward.city.id, slum.shelter_slum_code)
    return HttpResponse(json.dumps(output),content_type='application/json')

def get_kobo_RIM_report_data(request, slum_id):
    try:
        slum = Slum.objects.filter(shelter_slum_code=slum_id)
    except:
        slum = None
    try:
        rim_image = Rapid_Slum_Appraisal.objects.filter(slum_name=slum[0]).values()
    except:
        rim_image = []
    output = {"status":False, "image":False}
    if slum and len(slum)>0:
        output = get_kobo_RIM_report_detail(slum[0].electoral_ward.administrative_ward.city.id, slum[0].shelter_slum_code)
        output["status"] = False
        if len(output.keys()) > 1:
            output['status'] = True
        output['admin_ward'] = slum[0].electoral_ward.administrative_ward.name
        output['electoral_ward'] = slum[0].electoral_ward.name
        output['slum_name'] = slum[0].name
        if rim_image and len(rim_image) > 0:
            output.update(rim_image[0])
            output['image'] = True
    return HttpResponse(json.dumps(output),content_type='application/json')

@user_passes_test(lambda u: u.is_superuser)
def get_kobo_FF_report_data(request, slum_id,house_num):
     output = {"status":False}
     try:
         slum = Slum.objects.filter(shelter_slum_code=slum_id)
     except:
         slum = None
     if slum and len(slum)>0:
         output = get_kobo_FF_report_detail(slum[0].electoral_ward.administrative_ward.city.id, slum[0].shelter_slum_code, house_num)
         output["status"] = False
         if len(output.keys()) > 1:
             output['status'] = True
         output['admin_ward'] = slum[0].electoral_ward.administrative_ward.name
         output['slum_name'] = slum[0].name
     project_details = SponsorProjectDetails.objects.filter(slum=slum[0], household_code__contains=[int(house_num)])
     if len(project_details)>0:
         output['sponsor_logo'] = project_details[0].sponsor.logo.url if project_details[0].sponsor.logo else ""
     return HttpResponse(json.dumps(output),content_type='application/json')

@user_passes_test(lambda u: u.is_superuser)
def get_kobo_drainage_report_data(request, slum_id):
     output = {"status":False, "image":False}
     try:
         slum = Slum.objects.filter(shelter_slum_code=slum_id)
     except:
         slum = None
     if slum and len(slum)>0:
         output = get_kobo_RIM_report_detail(slum[0].electoral_ward.administrative_ward.city.id, slum[0].shelter_slum_code)
         output["status"] = False
         if len(output.keys()) > 1:
             output['status'] = True
         output["image"] = False
         drainage_image = drainage.objects.filter(slum_name = slum[0]).values()
         if drainage_image and len(drainage_image) > 0:
             output.update(drainage_image[0])
             output["image"] = True
         output['admin_ward'] = slum[0].electoral_ward.administrative_ward.name
         output['slum_name'] = slum[0].name
     return HttpResponse(json.dumps(output),content_type='application/json')
