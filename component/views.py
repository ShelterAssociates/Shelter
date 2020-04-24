from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test, permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.contrib.auth.models import User

from itertools import groupby
import json
from collections import OrderedDict
from kobotoolbox import *

from .forms import KMLUpload
from .kmlparser import KMLParser
from .models import Metadata


from .cipher import *
from master.models import Slum, Rapid_Slum_Appraisal, drainage
from sponsor.models import SponsorProjectDetails
from utils.utils_permission import apply_permissions_ajax, access_right, deco_rhs_permission
from django.core.exceptions import PermissionDenied

#@staff_member_required
@permission_required('component.can_upload_KML', raise_exception=True)
def kml_upload(request):
    context_data = {}
    if request.method == 'POST':
        form = KMLUpload(request.POST or None,request.FILES)
        if form.is_valid():
            docFile = request.FILES['kml_file'].read()
            data = form.cleaned_data['slum_name']
            if form.cleaned_data['level'] == 'City':
                data = form.cleaned_data['City']
            objKML = KMLParser(docFile, data, form.cleaned_data['delete_flag'])
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
@access_right
def get_component(request, slum_id):
    '''Get component/filter/sponsor data for the selected slum.
       Here sponsor data is fetch according to user role access rights
    '''
    slum = get_object_or_404(Slum, pk=slum_id)
    sponsors=[]
    sponsor_slum_count = 0
    if not request.user.is_anonymous():
       sponsors = request.user.sponsor_set.all().values_list('id',flat=True)
       #sponsor_slum_count = SponsorProjectDetails.objects.filter(slum = slum).count()
    #Fetch filter and sponsor metadata
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
    sponsor_houses = []
    #Iterate through each filter and assign answers to child if available
    for metad in metadata:
        component = {}
        component['name'] = metad.name
        component['level'] = metad.level
        component['section'] = metad.section.name
        component['section_order'] = metad.section.order
        component['type'] = metad.type
        component['order'] = metad.order
        component['blob'] = metad.blob
        component['icon'] = str(metad.icon.url) if metad.icon else ""
        component['child'] = []
        #Component
        if metad.type == 'C':
            #Fetch component for selected filter and slum , assign it finally to child
            for comp in slum.components.filter(metadata=metad):
                component['child'].append({'housenumber':comp.housenumber, 'shape':json.loads(comp.shape.json)})
        #Filter
        elif metad.type == 'F' and metad.code != "":
            field = metad.code.split(':')
            if field[0] in rhs_analysis:
                options = []
                options = [rhs_analysis[field[0]][option] for option in field[1].split(',') if option in rhs_analysis[field[0]]]
                component['child'] = list(set(sum(options,[])))
        #Sponsor : Depending on superuser or sponsor render the data accordingly
        elif metad.type == 'S' and (metad.authenticate == False or not request.user.is_anonymous()) :
            if  metad.code!= "":
                sponsor_households = []
                sponsor_households = SponsorProjectDetails.objects.filter(slum = slum, sponsor__id = int(metad.code)).values_list('household_code', flat=True)
                if len(sponsor_households)>0:
                    try:
                        sponsor_households = sum(list(sponsor_households), [])
                    except Exception as e:
                        sponsor_households = sum(map(lambda x : json.loads(x),sponsor_households),[])
                if metad.section.name=="Sponsor":
                    sponsor_houses.extend(sponsor_households)
                if request.user.is_superuser or int(metad.code) in sponsors or metad.authenticate == False :
                    component['child'] = sponsor_households
            else:
                component['child'] = sponsor_houses
        if len(component['child']) > 0:
            component['count']=len(component['child'])
            lstcomponent.append(component)
    #sponsor_houses = sponsor_houses.pop(0)
    #lstcomponent = sorted(lstcomponent, key=lambda x:x['section_order'])
    dtcomponent = OrderedDict()
    #Ordering the filter/components/sponsors according to the section they below to.
    for key, comp in  groupby(lstcomponent, key=lambda x:x['section']):
        if key not in dtcomponent:
            dtcomponent[key] = OrderedDict()
        for c in comp:
            dtcomponent[key][c['name']] = c
    return HttpResponse(json.dumps(dtcomponent),content_type='application/json')

@deco_rhs_permission
def get_kobo_RHS_data(request, slum_id,house_num):
     output = {}
     slum = get_object_or_404(Slum, pk=slum_id)
     project_details = False
     if request.user.is_superuser or request.user.groups.filter(name='ulb').exists():
         project_details = True
         output = get_kobo_RHS_list(slum.electoral_ward.administrative_ward.city.id, slum.shelter_slum_code, house_num)
     elif request.user.groups.filter(name='sponsor').exists():
         project_details = SponsorProjectDetails.objects.filter(slum=slum, sponsor__user=request.user, household_code__contains=int(house_num)).exists()
     if request.user.groups.filter(name='ulb').exists():
         project_details = False
     #if 'admin_ward' in output:
     output['admin_ward'] = slum.electoral_ward.administrative_ward.name
     output['slum_name'] = slum.name
     output['house_no'] = house_num

     output['FFReport'] = project_details
     return HttpResponse(json.dumps(output),content_type='application/json')

#@user_passes_test(lambda u: u.is_superuser)
@access_right
def get_kobo_RIM_data(request, slum_id):

    slum = get_object_or_404(Slum, pk=slum_id)
    try:
        output = get_kobo_RIM_detail(slum.electoral_ward.administrative_ward.city.id, slum.shelter_slum_code)
    except:
        output = {}
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

#@user_passes_test(lambda u: u.is_superuser)
def get_kobo_FF_report_data(request, key):
     output = {"status":False}
     cipher = AESCipher()
     slum, user = None, None
     try:
         (slum_id, house_num, user_id) = cipher.decrypt(key).split('|')
         slum = Slum.objects.filter(shelter_slum_code=slum_id)
         user = User.objects.get(id=user_id)
     except:
         user = None
     if user and (user.is_superuser or user.groups.filter(name="sponsor").exists()) and slum and len(slum)>0:
         filter_data ={"slum":slum[0], "household_code__contains":str(house_num)}
         if user.groups.filter(name="sponsor").exists():
             filter_data["sponsor__user"] = user
         project_details = SponsorProjectDetails.objects.filter(**filter_data)
         output = get_kobo_FF_report_detail(slum[0].electoral_ward.administrative_ward.city.id, slum[0].shelter_slum_code, house_num)
         output["status"] = False
         if len(output.keys()) > 1:
             output['status'] = True
         output['admin_ward'] = slum[0].electoral_ward.administrative_ward.name
         output['slum_name'] = slum[0].name
         output['Household_number'] = house_num

         if len(project_details)>0:
             output['sponsor_logo'] = project_details[0].sponsor.logo.url if project_details[0].sponsor.logo else ""
     return HttpResponse(json.dumps(output),content_type='application/json')

#@user_passes_test(lambda u: u.is_superuser)
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
         drainage_image = Rapid_Slum_Appraisal.objects.filter(slum_name = slum[0]).values()
         if drainage_image and len(drainage_image) > 0:
             output.update(drainage_image[0])
             output["image"] = True
         output['admin_ward'] = slum[0].electoral_ward.administrative_ward.name
         output['electoral_ward'] = slum[0].electoral_ward.name
         output['slum_name'] = slum[0].name
     return HttpResponse(json.dumps(output),content_type='application/json')
