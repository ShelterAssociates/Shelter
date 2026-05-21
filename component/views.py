from urllib import request

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, permission_required
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.contrib.auth.models import User
from itertools import groupby
from collections import OrderedDict
import json
import os
import subprocess
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from calendar import monthrange
from datetime import date
from django.contrib.auth.decorators import login_required
from .kobotoolbox import *
from .forms import KMLUpload
from .kmlparser import KMLParser
from .models import Metadata
from .cipher import *
from master.models import Slum, Rapid_Slum_Appraisal, drainage
from sponsor.models import SponsorProject, SponsorProjectDetails
from graphs.sync_avni_data import *
from utils.utils_permission import apply_permissions_ajax, access_right, deco_rhs_permission
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.db.models import Q
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_POST
from django.utils.text import slugify
from mastersheet.models import ToiletConstruction
from xml.sax.saxutils import escape

from graphs.models import HouseholdData

slum_list = ['223', '1925', '1923', '1927', '1062', '1050', '1061', '1061', '1914', '763', '29', '672', '525', '686', '546', '547', '572', '529', '1363', '175', '514', '760', '639', '672', '820', '1026', '1008', '1169', '1639', '1644', '1647', '1171', '1645', '1170', '1640', '1641', '1136', '1164', '1137', '1642', '1142', '1069', '1026', '1034', '1012', '1048', '1050', '1054', '1057', '1119', '1020', '1030', '1028', '1057', '1652', '1283', '1288', '1095', '1096', '1097', '1099', '1100', '1101', '1098', '1104', '1107', '1111', '1079', '1080', '1342', '1083', '1672', '1673', '1085', '1086', '1087', '1077', '1091', '1092', '1665', '1081', '1082', '1338', '1084', '1074', '1340', '1350', '1088', '1089', '1075', '1076', '1090', '1093', '1344', '1094', '1349', '1102', '1103', '1666', '1105', '1106', '1343', '1108', '1109', '1346', '1078', '1112', '1115', '1116', '1113', '1341', '1117', '1339', '1110', '1375', '1259', '1198', '1293', '1200', '1288', '1283', '1971','1929','2019','2020','2021']

@staff_member_required
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
# @access_right
def get_component(request, slum_id):
    '''Get component/filter/sponsor data for the selected slum.
       Here sponsor data is fetch according to user role access rights
    '''
    slum = get_object_or_404(Slum, pk=slum_id)
    if slum.current_status == 'sra': return JsonResponse({"status": "sra", "data": None})
    if slum.current_status == 'road_widening': return JsonResponse({"status": "road_widening", "data": None})
    city_name = list(Slum.objects.filter(id = slum.id).values_list('electoral_ward__administrative_ward__city__name__city_name', flat = True))[0]
    sponsor_slum_count = 0
    sponsors = []
    sponsor_project_detail_ids = []
    
    if not request.user.is_anonymous:
        # Exclude sponsor ID 10 (Toilet Facilitation under SBM Toilets)
        sponsors = list(
            request.user.sponsor_set
            .exclude(id=10)
            .values_list("id", flat=True)
        )
    
        sponsor_project_detail_ids = (
            SponsorProject.objects
            .filter(sponsor_id__in=sponsors)
            .values_list("id", flat=True)
        )
       #sponsor_slum_count = SponsorProjectDetails.objects.filter(slum = slum).count()
    #Fetch filter and sponsor metadata
    # if slum in slum_list we fetch Shop data from mastersheet else we fetch Shops data from kml data.
    if slum_id in slum_list:
        metadata = Metadata.objects.filter(visible=True).exclude(name='Shops').order_by('section__order','order')
    else:
        metadata = Metadata.objects.filter(visible=True).exclude(name='Shop').order_by('section__order','order')
    rhs_analysis = {}

    fields_code = metadata.filter(type='F').exclude(code="").values_list('code', flat=True)
    fields = list(set([str(x.split(':')[0]) for x in fields_code]))
    rhs_analysis = get_household_analysis_data(slum.electoral_ward.administrative_ward.city.id,slum.id, fields)

    lstcomponent = [] 
    sponsor_houses = []
    #Iterate through each filter and assign answers to child if available
    for metad in metadata:
        component = {}
        component['name'] = metad.name
        if component['name'] == 'Slum boundary' and slum_id in ['1971','1972']:
            component['name'] = 'Town boundary'
        component['level'] = metad.level
        component['section'] = metad.section.name
        component['section_order'] = metad.section.order
        component['type'] = metad.type
        component['order'] = metad.order
        component['blob'] = metad.blob
        component['icon'] = str(metad.icon.url) if metad.icon else ""
        component['child'] = []
        com_list =[]
        #Component
        if metad.type == 'C':
            if metad.name == 'Shops':
                for comp in slum.components.filter(metadata=metad):
                    com_list.append(comp.housenumber)
            #Fetch component for selected filter and slum , assign it finally to child
            for comp in slum.components.filter(metadata=metad):
                component['child'].append({'housenumber':comp.housenumber, 'shape':json.loads(comp.shape.json)})
        #Filter
        elif metad.type == 'F' and metad.code != "":
            field = metad.code.split(':')

            
            if city_name != 'Kolhapur' and field[0] == 'If individual water connection, type of water meter?':
                pass
            else:
                if field[0] in rhs_analysis:
                    options = []
                    options = [rhs_analysis[field[0]][option] for option in field[1].split('|,|') if option in rhs_analysis[field[0]]]
                    component['child'] = list(set(sum(options,[])))
        # # Sponsor : Depending on superuser or sponsor render the data accordingly
        elif metad.type == 'S' and (metad.authenticate == False or not request.user.is_anonymous):
            if  metad.code!= "":
                sponsor_households = []
                sponsor_households = SponsorProjectDetails.objects.filter(sponsor_project__id=int(metad.code),slum=slum).values_list("household_code", flat=True)
                if len(sponsor_households)>0:
                    try:
                        sponsor_households = sum(list(sponsor_households), [])
                    except Exception as e:
                        sponsor_households = sum(map(lambda x : json.loads(x),sponsor_households),[])
                if metad.section.name=="Sponsor":
                    sponsor_houses.extend(sponsor_households)
                if request.user.is_superuser or int(metad.code) in sponsor_project_detail_ids or metad.authenticate == False :
                    component['child'] = sponsor_households
            else:
                component['child'] = sponsor_houses
        if len(component['child']) > 0:
            component['count']=len(component['child'])
            lstcomponent.append(component)
    # sponsor_houses = sponsor_houses.pop(0)
    lstcomponent = sorted(lstcomponent, key=lambda x:x['section_order'])
    dtcomponent = OrderedDict()
    #Ordering the filter/components/sponsors according to the section they below to.
    for key, comp in  groupby(lstcomponent, key=lambda x:x['section']):
        if key not in dtcomponent:
            dtcomponent[key] = OrderedDict()
        for c in comp:
            dtcomponent[key][c['name']] = c

    # with open('/home/shelter/Desktop/Shelter_New/component/dtcomponent.json', 'w') as f:
    #     json.dump(dtcomponent, f, indent=4)
    return HttpResponse(json.dumps(dtcomponent),content_type='application/json')

def format_data(rhs_data):
    new_rhs = {}
    remove_list = ['Name_s_of_the_surveyor_s', 'Date_of_survey', '_xform_id_string', 'meta/instanceID', 'end', 'start',
    'Enter_household_number_again','_geolocation', 'meta/deprecatedID', '_uuid', '_submitted_by', 'admin_ward', '_status',
    'formhub/uuid', '__version__','_submission_time', '_id', '_notes', '_bamboo_dataset_id', '_tags', 'slum_name', '_attachments',
    'OD1', 'C1', 'C2', 'C3','Household_number', '_validation_status']

    seq = {'group_el9cl08/Number_of_household_members': 'Number of household members',
     'group_oi8ts04/Have_you_applied_for_individua': 'Have you applied for an individual toilet under SBM?',
     'group_oi8ts04/Current_place_of_defecation': 'Current place of defecation',
     'group_el9cl08/Type_of_structure_of_the_house': 'Type of structure of the house',
     'group_oi8ts04/What_is_the_toilet_connected_to': 'What is the toilet connected to',
     'Household_number': 'Household number',
     'group_el9cl08/Type_of_water_connection': 'Type of water connection',
     'group_el9cl08/Facility_of_solid_waste_collection': 'Facility of solid waste collection',
     'group_el9cl08/Ownership_status_of_the_house': 'Ownership status of the house',
     'group_el9cl08/Does_any_household_m_n_skills_given_below': 'Does any household member have any of the construction skills given below?',
     'group_el9cl08/Enter_the_10_digit_mobile_number':'Mobile number',
     'group_el9cl08/House_area_in_sq_ft': 'House area in sq. ft.','group_og5bx85/Type_of_survey': 'Type of survey',
     'group_og5bx85/Full_name_of_the_head_of_the_household': 'Full name of the head of the household',
     'group_el9cl08/Do_you_have_any_girl_child_chi': 'Do you have any girl child/children under the age of 18?',
     'Type_of_structure_occupancy': 'Type of structure of the house',
     'group_oi8ts04/Are_you_interested_in_an_indiv': 'Are you interested in an individual toilet?'
     }
    for i in remove_list:
        if i in rhs_data:
            rhs_data.pop(i)
    for k, v in seq.items():
        try:
            new_rhs[v] = rhs_data[k]
        except Exception as e:pass
    return new_rhs

# @deco_rhs_permission
def get_kobo_RHS_data(request, slum_id,house_num):
     output = OrderedDict()
     slum = get_object_or_404(Slum, id=slum_id)
     project_details = False
     if slum_id != '1971':
         output['admin_ward'] = slum.electoral_ward.administrative_ward.name
     output['slum_name'] = slum.name
     output['house_no'] = house_num         

     if request.user.is_superuser or request.user.groups.filter(name__in=['ulb']).exists():
         project_details = True
         output.update(get_kobo_RHS_list(slum.electoral_ward.administrative_ward.city.id, slum,slum_id ,house_num))
     elif (request.user.is_superuser or request.user.groups.filter(name='MLG').exists()) and slum_id=='1971':
         project_details = True
         output.update(get_kobo_RHS_list(slum.electoral_ward.administrative_ward.city.id, slum, slum_id,house_num))
     elif request.user.groups.filter(name='sponsor').exists():
         project_details = SponsorProjectDetails.objects.filter(slum=slum, sponsor__user=request.user, household_code__contains=int(house_num)).exists()
     if request.user.groups.filter(name='ulb').exists():
         project_details = False
     
     if project_details:
          project_details = project_details = SponsorProjectDetails.objects.filter(slum=slum,  household_code__contains=int(house_num)).exists()

     #Adding code fetch pluscode from RHS data.
     if slum_id != '1971':   
        plus_code = getPlusCodeDetails(slum_id, house_num)
        if plus_code:
            output['PlusCode'] = plus_code
     # output['Household_details']= json.dumps(rhs_data)
     output['FFReport'] = project_details
     return HttpResponse(json.dumps(output),content_type='application/json')

#@user_passes_test(lambda u: u.is_superuser)
# @access_right
def get_kobo_RIM_data(request, slum_id):
    try:
        slum = Slum.objects.get(pk=slum_id)
    except Slum.DoesNotExist:
        return HttpResponse(f"<h1>Slum with ID {slum_id} not found</h1>", content_type='text/html')
    if slum.current_status == 'sra': return JsonResponse({"status": "sra", "data": None})
    if slum.current_status == 'road_widening': return JsonResponse({"status": "road_widening", "data": None})
    try:
        output = get_kobo_RIM_detail(
            slum.electoral_ward.administrative_ward.city.id, 
            slum.shelter_slum_code
        )
    except:
        output = {}

    return HttpResponse(json.dumps(output), content_type='application/json')

def get_image(image_name, image_link, cognito_token):
    path = 'https://app.avniproject.org/media/signedUrl?url='
    request_1 = requests.get(path + image_link, headers={'AUTH-TOKEN': cognito_token})
    return image_name, request_1.text

def fetch_images_and_update_urls(image_dict, cognito_token):
    with ThreadPoolExecutor() as executor:
        # Submit tasks with Cognito token included
        tasks = [executor.submit(get_image, name, link, cognito_token) for name, link in image_dict.items()]
        updated_dict = {task.result()[0]: task.result()[1] for task in tasks}
    return updated_dict


def get_avni_image_urls(rim_obj):
    fields_to_modify= ['toilet_image_bottomdown1', 'toilet_image_bottomdown2', 'water_image_bottomdown1', 'water_image_bottomdown2', 'waste_management_image_bottomdown1', 'waste_management_image_bottomdown2', 'drainage_image_bottomdown1', 'drainage_image_bottomdown2', 'gutter_image_bottomdown1', 'gutter_image_bottomdown2', 'roads_image_bottomdown1', 'road_image_bottomdown2', 'general_image_bottomdown1', 'general_image_bottomdown2', 'general_info_left_image', 'toilet_info_left_image', 'waste_management_info_left_image', 'water_info_left_image', 'roads_and_access_info_left_image', 'drainage_info_left_image', 'gutter_info_left_image', 'drainage_report_image']
    image_dict = {}
    a = avni_sync()
    for field in fields_to_modify:
        if field in rim_obj:
            old_link = str(rim_obj[field])
            if "https://s3.ap-south-1.amazonaws.com/" in old_link:
                image_dict[field] = old_link
            elif "ShelterPhotos" in old_link:
                prefix = 'https://app.shelter-associates.org/media/'
                rim_obj[field] = prefix + old_link
            else:
                continue
    # Process images with Cognito token
    cognito_token = a.get_cognito_token()
    updated_image_dict = fetch_images_and_update_urls(image_dict, cognito_token)
    rim_obj.update(updated_image_dict)
    return rim_obj

def get_kobo_RIM_report_data(request, slum_id,rawa=False):
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
            """Handling the Scenario where Slums Lack Community Toilet Block Availability: 
                Removing CTB Information from RIM Additional Info."""
            if 'number_of_community_toilet_blo' in output and output['number_of_community_toilet_blo'] == 0:
                del_keys = ['toilet_seat_to_persons_ratio', 'toilet_cost']
                for key in del_keys:
                    if key in rim_image[0]:
                        del rim_image[0][key]
            # Check if there are avni images available.
            rim_image_updated = get_avni_image_urls(rim_image[0])
            output.update(rim_image_updated)
            output['image'] = True
    if rawa:
        return output
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
         filter_data ={"slum":slum[0], "household_code__contains":int(house_num)}
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

def get_component_list(request):
    """Get unique component names from Metadata for a given object_id, with count numbers."""
    object_id = request.GET.get('object_id')
    components = Component.objects.filter(object_id=object_id).values_list('metadata__name', flat=True)
    unique_names = sorted(set(components))
    data = [{'id': i + 1, 'name': name} for i, name in enumerate(unique_names)]
    return JsonResponse(data, safe=False)

def delete_component(request):

    if request.method == "POST":  # or "DELETE"
        object_id = request.POST.get("object_id")
        comp_name = request.POST.get("comp_name")
        if not object_id or not comp_name:
            return JsonResponse({"success": False, "message": "Missing object_id or comp_name"}, status=400)

        # Try to delete the component
        try:
            comp = Component.objects.filter(object_id=object_id, metadata__name=comp_name)
            comp.delete()
            return JsonResponse({"success": True, "message": f'Component "{comp_name}" deleted successfully'})
        except Component.DoesNotExist:
            return JsonResponse({"success": False, "message": "Component not found"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    else:
        return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)

# ================== New API for Sponsor Toilet Household Month End Dates ==================
def extract_household_codes(qs):
	all_codes = set()

	for codes in qs:
		if not codes:
			continue

		try:
			if isinstance(codes, list):
				all_codes.update(str(c) for c in codes)
			else:
				all_codes.update(str(c) for c in json.loads(codes))
		except Exception:
			continue

	return all_codes


def get_toilets_queryset(slum_id, household_codes=None):
	filters = {
		'completion_date__isnull': False,
		'slum_id': slum_id
	}

	if household_codes:
		filters['household_number__in'] = household_codes

	return ToiletConstruction.objects.filter(**filters)


def get_household_month_end_dates(request):
	slum_id = request.GET.get('slum_id')

	if not slum_id:
		return JsonResponse({"error": "slum_id is required"}, status=400)

	user = request.user

	# ------------------------------------------------------------
	# CASE 1: Admin / Staff
	# ------------------------------------------------------------
	if user.is_superuser or user.is_staff:

		household_qs = SponsorProjectDetails.objects.filter(
			slum_id=slum_id
		).values_list("household_code", flat=True)

		household_codes = extract_household_codes(household_qs)

		if not household_codes:
			return JsonResponse({"error": "No sponsor-linked households found for this slum"}, status=404)

		toilets = get_toilets_queryset(slum_id, household_codes)

		return build_response(toilets, scope='superuser', slum_id=slum_id)

	# ------------------------------------------------------------
	# CASE 2: Sponsor user
	# ------------------------------------------------------------
	elif user.groups.filter(name='sponsor').exists():

		sponsor_name = request.GET.get('sponsor_name')

		sponsor_qs = user.sponsor_set.all()
		if sponsor_name:
			sponsor_qs = sponsor_qs.filter(organization_name=sponsor_name)

		sponsor_ids = sponsor_qs.values_list('id', flat=True)

		if not sponsor_ids:
			return JsonResponse({"error": "No sponsor linked to this user"}, status=403)

		sponsor_project_ids = SponsorProject.objects.filter(
			sponsor_id__in=sponsor_ids
		).values_list("id", flat=True)

		household_qs = SponsorProjectDetails.objects.filter(
			sponsor_project_id__in=sponsor_project_ids,
			slum_id=slum_id
		).values_list("household_code", flat=True)

		household_codes = extract_household_codes(household_qs)

		if not household_codes:
			return JsonResponse({"error": "No households found for this sponsor in the given slum"}, status=404)

		toilets = get_toilets_queryset(slum_id, household_codes)

		return build_response(toilets, scope='sponsor', slum_id=slum_id, user=user)

	# ------------------------------------------------------------
	# CASE 3: Public / Others
	# ------------------------------------------------------------
	else:
		toilets = get_toilets_queryset(slum_id)

		if not toilets.exists():
			return JsonResponse({
				"message": "No toilets found in this slum",
				"data": []
			})

		return build_response(toilets, scope='all', slum_id=slum_id)


def build_response(toilets, scope, slum_id, user=None):
    grouped = {}
    for t in toilets:
        comp_date = t.completion_date
        last_day = monthrange(comp_date.year, comp_date.month)[1]
        month_end = date(comp_date.year, comp_date.month, last_day)
        month_key = month_end.strftime("%b %Y")
        month_end_str = month_end.strftime("%Y-%m-%d")

        if month_key not in grouped:
            grouped[month_key] = {
                "month_end_date": month_end_str,
                "house_numbers": [],
                "total": 0
            }
        grouped[month_key]["house_numbers"].append(t.household_number)
        grouped[month_key]["total"] += 1

    sorted_months = sorted(grouped.items(), key=lambda x: x[1]["month_end_date"])

    response = {
        "slum_id": slum_id,
        "scope": scope,
        "grand_total": sum(v["total"] for _, v in sorted_months),
        "monthly_data": [
            {
                "month": month,
                "month_end_date": data["month_end_date"],
                "house_numbers": sorted(data["house_numbers"]),
                "total": data["total"]
            }
            for month, data in sorted_months
        ]
    }

    if user and scope == 'sponsor':
        response["sponsors"] = list(user.sponsor_set.all().values_list('organization_name', flat=True))

    return JsonResponse(response)


def _base_household_number(value):
    return str(value).split('.')[0].strip()


def _flatten_export_data(value, prefix=""):
    flattened = {}

    if isinstance(value, dict):
        for key, item in value.items():
            safe_key = str(key).replace("/", "_").replace(" ", "_")
            next_prefix = "{}{}".format(prefix, safe_key) if prefix else safe_key
            flattened.update(_flatten_export_data(item, next_prefix))
    elif isinstance(value, list):
        flattened[prefix] = json.dumps(value, ensure_ascii=False)
    elif value is None:
        flattened[prefix] = ""
    else:
        flattened[prefix] = str(value)

    return flattened


def _shape_safe_properties(data):
    properties = {}

    for key, value in data.items():
        safe_key = slugify(str(key).replace("/", "_")).replace("-", "_").upper()[:10] or "FIELD"
        original_key = safe_key
        index = 1
        while safe_key in properties:
            suffix = str(index)
            safe_key = (original_key[: max(1, 10 - len(suffix))] + suffix)[:10]
            index += 1

        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        if value is None:
            value = ""

        properties[safe_key] = str(value)[:254]

    return properties


def _safe_file_name(value):
    return slugify(str(value)) or "layer"


def _kml_coordinates(coords):
    return " ".join("{},{},0".format(coord[0], coord[1]) for coord in coords)


def _hex_to_kml_color(hex_color, alpha="ff"):
    if not hex_color:
        hex_color = "#ffffff"

    color = str(hex_color).strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6:
        color = "ffffff"

    return "{}{}{}{}".format(alpha, color[4:6], color[2:4], color[0:2])


def _kml_style(style_data):
    if not style_data:
        return ""

    line_color = _hex_to_kml_color(style_data.get("linecolor"), "ff")
    fill_alpha = "aa" if style_data.get("fillflag", True) else "00"
    fill_color = _hex_to_kml_color(style_data.get("polycolor"), fill_alpha)
    line_width = str(style_data.get("linewidth") or 1)

    return (
        "<Style>"
        "<LineStyle><color>{line_color}</color><width>{line_width}</width></LineStyle>"
        "<PolyStyle><color>{fill_color}</color><fill>{fill}</fill><outline>1</outline></PolyStyle>"
        "</Style>"
    ).format(
        line_color=line_color,
        line_width=escape(line_width),
        fill_color=fill_color,
        fill="1" if style_data.get("fillflag", True) else "0"
    )


def _normalize_hex_color(hex_color, fallback="#ffffff"):
    color = str(hex_color or fallback).strip()
    if not color.startswith("#"):
        color = "#" + color.lstrip("#")

    raw = color.lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return fallback

    return "#" + raw.lower()


def _csv_escape(value):
    return '"{}"'.format(str(value if value is not None else "").replace('"', '""'))


def _geometry_family(geometry_type):
    if geometry_type in ["Point", "MultiPoint"]:
        return "point"
    if geometry_type in ["LineString", "MultiLineString"]:
        return "line"
    return "polygon"


def _build_filter_summary_csv_rows(export_rows):
    section_columns = sorted({
        row.get("section_name", "")
        for row in export_rows
        if row.get("household_number") and row.get("section_name")
    })

    rows_by_household = OrderedDict()
    for row in export_rows:
        household_number = row.get("household_number")
        if not household_number:
            continue

        section_name = row.get("section_name", "")
        metadata_name = row.get("layer_name", "")
        data = row.get("extended_data", {})

        if household_number not in rows_by_household:
            rows_by_household[household_number] = {
                "household_number": household_number,
                "slum_name": data.get("slum_name", ""),
                "city_name": data.get("city_name", "")
            }
            for column in section_columns:
                rows_by_household[household_number][column] = []

        if section_name and metadata_name:
            rows_by_household[household_number][section_name].append(metadata_name)

    final_rows = []
    for _, row in rows_by_household.items():
        final_row = {
            "household_number": row["household_number"],
            "slum_name": row["slum_name"],
            "city_name": row["city_name"]
        }
        for column in section_columns:
            values = row[column]
            final_row[column] = ", ".join(sorted(set(values), key=lambda x: x.lower())) if values else ""
        final_rows.append(final_row)

    return final_rows


def _geometry_to_kml(shape):
    geometry = json.loads(shape.geojson)
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "Point":
        return "<Point><coordinates>{}</coordinates></Point>".format(
            _kml_coordinates([coordinates])
        )

    if geometry_type == "LineString":
        return "<LineString><coordinates>{}</coordinates></LineString>".format(
            _kml_coordinates(coordinates)
        )

    if geometry_type == "Polygon":
        boundaries = []
        for ring in coordinates:
            boundaries.append(
                "<LinearRing><coordinates>{}</coordinates></LinearRing>".format(
                    _kml_coordinates(ring)
                )
            )

        outer = "<outerBoundaryIs>{}</outerBoundaryIs>".format(boundaries[0]) if boundaries else ""
        inner = "".join(
            "<innerBoundaryIs>{}</innerBoundaryIs>".format(ring)
            for ring in boundaries[1:]
        )
        return "<Polygon>{}{}</Polygon>".format(outer, inner)

    if geometry_type == "MultiPolygon":
        polygons = []
        for polygon in coordinates:
            boundaries = []
            for ring in polygon:
                boundaries.append(
                    "<LinearRing><coordinates>{}</coordinates></LinearRing>".format(
                        _kml_coordinates(ring)
                    )
                )
            outer = "<outerBoundaryIs>{}</outerBoundaryIs>".format(boundaries[0]) if boundaries else ""
            inner = "".join(
                "<innerBoundaryIs>{}</innerBoundaryIs>".format(ring)
                for ring in boundaries[1:]
            )
            polygons.append("<Polygon>{}{}</Polygon>".format(outer, inner))
        return "<MultiGeometry>{}</MultiGeometry>".format("".join(polygons))

    if geometry_type == "MultiLineString":
        lines = []
        for line in coordinates:
            lines.append(
                "<LineString><coordinates>{}</coordinates></LineString>".format(
                    _kml_coordinates(line)
                )
            )
        return "<MultiGeometry>{}</MultiGeometry>".format("".join(lines))

    if geometry_type == "MultiPoint":
        points = []
        for point in coordinates:
            points.append(
                "<Point><coordinates>{}</coordinates></Point>".format(
                    _kml_coordinates([point])
                )
            )
        return "<MultiGeometry>{}</MultiGeometry>".format("".join(points))

    return ""


def _extended_data_kml(data):
    data_rows = []

    for key, value in data.items():
        if value in [None, ""]:
            continue
        data_rows.append(
            '<Data name="{key}"><value>{value}</value></Data>'.format(
                key=escape(str(key)),
                value=escape(str(value))
            )
        )

    if not data_rows:
        return ""

    return "<ExtendedData>{}</ExtendedData>".format("".join(data_rows))


def _build_export_rows(structure_components, slum, selected_filters, style_map, fallback_style):
    household_numbers = sorted({
        _base_household_number(component.housenumber)
        for component in structure_components
    })
    household_map = {
        household.household_number: household
        for household in HouseholdData.objects.filter(
            slum=slum,
            household_number__in=household_numbers
        )
    }

    export_rows = []
    for component in structure_components:
        base_household = _base_household_number(component.housenumber)
        household = household_map.get(base_household)
        extended_data = {
            "structure_number": component.housenumber,
            "household_number": base_household,
            "slum_name": slum.name,
            "city_name": slum.electoral_ward.administrative_ward.city.name.city_name,
            "administrative_ward": slum.electoral_ward.administrative_ward.name,
            "electoral_ward": slum.electoral_ward.name,
            "selected_filters": ", ".join(selected_filters),
            "has_household_data": "Yes" if household else "No",
        }

        if household:
            extended_data["submission_date"] = household.submission_date
            extended_data["created_date"] = household.created_date
            extended_data.update(_flatten_export_data(household.rhs_data or {}, "rhs_"))
            extended_data.update(_flatten_export_data(household.ff_data or {}, "ff_"))

        style_data = style_map.get(base_household) or fallback_style or {}
        export_rows.append({
            "component": component,
            "household_number": base_household,
            "extended_data": extended_data,
            "style": style_data
        })

    return export_rows


def _build_export_rows_from_layers(layers, slum, selected_filters):
    household_numbers = sorted({
        _base_household_number(feature.get("household_number") or feature.get("structure_number"))
        for layer in layers
        for feature in (layer.get("features") or [])
        if feature.get("household_number") or feature.get("structure_number")
    })
    household_map = {
        household.household_number: household
        for household in HouseholdData.objects.filter(
            slum=slum,
            household_number__in=household_numbers
        )
    }

    export_rows = []
    for layer in layers:
        metadata_name = layer.get("metadata_name") or "Layer"
        section_name = layer.get("section_name") or ""
        metadata_type = layer.get("metadata_type") or ""
        style_data = layer.get("style") or {}

        for feature in layer.get("features") or []:
            geometry = feature.get("geometry")
            if not geometry:
                continue

            structure_number = str(feature.get("structure_number") or feature.get("household_number") or metadata_name)
            household_number = _base_household_number(feature.get("household_number") or structure_number)
            household = household_map.get(household_number)

            extended_data = {
                "metadata_name": metadata_name,
                "section_name": section_name,
                "metadata_type": metadata_type,
                "structure_number": structure_number,
                "household_number": household_number,
                "slum_name": slum.name,
                "city_name": slum.electoral_ward.administrative_ward.city.name.city_name,
                "administrative_ward": slum.electoral_ward.administrative_ward.name,
                "electoral_ward": slum.electoral_ward.name,
                "selected_filters": ", ".join(selected_filters),
                "has_household_data": "Yes" if household else "No",
            }

            if household:
                extended_data["submission_date"] = household.submission_date
                extended_data["created_date"] = household.created_date
                extended_data.update(_flatten_export_data(household.rhs_data or {}, "rhs_"))
                extended_data.update(_flatten_export_data(household.ff_data or {}, "ff_"))

            export_rows.append({
                "component": None,
                "geometry": geometry,
                "layer_name": metadata_name,
                "section_name": section_name,
                "household_number": household_number,
                "extended_data": extended_data,
                "style": style_data
            })

    return export_rows


def _build_component_data_from_db(slum, slum_id, export_selection, selected_sections):
    selected_sections = {
        str(section_name).strip()
        for section_name in (selected_sections or [])
        if str(section_name).strip()
    }
    selected_names = {
        (item.get("metadata_name") or item.get("item_name") or "").strip()
        for item in (export_selection or [])
        if (item.get("metadata_name") or item.get("item_name") or "").strip()
    }
    query_names = set(selected_names)

    if slum_id in ["1971", "1972"] and "Town boundary" in query_names:
        query_names.add("Slum boundary")

    if not selected_sections and not selected_names:
        return OrderedDict()

    metadata_qs = Metadata.objects.filter(visible=True)
    if slum_id in slum_list:
        metadata_qs = metadata_qs.exclude(name="Shops")
    else:
        metadata_qs = metadata_qs.exclude(name="Shop")

    metadata_qs = metadata_qs.filter(
        Q(section__name__in=selected_sections) | Q(name__in=query_names)
    ).select_related("section").order_by("section__order", "order")

    components = (
        slum.components.filter(metadata__in=metadata_qs)
        .select_related("metadata", "metadata__section")
        .order_by("metadata__section__order", "metadata__order", "housenumber")
    )

    component_data = OrderedDict()
    for component in components:
        metadata = component.metadata
        section_name = metadata.section.name
        item_name = "Town boundary" if metadata.name == "Slum boundary" and slum_id in ["1971", "1972"] else metadata.name

        section_bucket = component_data.setdefault(section_name, OrderedDict())
        item = section_bucket.get(item_name)
        if item is None:
            item = {
                "name": item_name,
                "level": metadata.level,
                "section": section_name,
                "section_order": metadata.section.order,
                "type": metadata.type,
                "order": metadata.order,
                "blob": metadata.blob,
                "icon": str(metadata.icon.url) if metadata.icon else "",
                "child": [],
            }
            section_bucket[item_name] = item

        item["child"].append({
            "housenumber": component.housenumber,
            "shape": json.loads(component.shape.json),
        })

    return component_data


def _build_export_rows_from_component_selection(component_data, slum, selected_filters, selected_sections, export_selection):
    selected_sections = set(selected_sections or [])
    selected_names = {
        (item.get("metadata_name") or item.get("item_name") or "").strip(): item
        for item in (export_selection or [])
        if (item.get("metadata_name") or item.get("item_name") or "").strip()
    }

    if not selected_sections and not selected_names:
        return []

    houses_map = {}
    for _, section_items in (component_data or {}).items():
        for item_name, item_data in (section_items or {}).items():
            if not item_data or item_data.get("type") != "C":
                continue
            for child in item_data.get("child") or []:
                if child.get("housenumber") is not None and child.get("shape") is not None:
                    key = str(child["housenumber"]).split(".")[0].strip()
                    if key and key not in houses_map:
                        houses_map[key] = child["shape"]

    household_numbers = set()
    selected_layers = []

    for section_name, section_items in (component_data or {}).items():
        section_selected = section_name in selected_sections
        for item_name, item_data in (section_items or {}).items():
            selection_info = selected_names.get(item_name)
            if not section_selected and not selection_info:
                continue
            if not item_data:
                continue

            style_data = (selection_info or {}).get("style") or {
                "name": item_name,
                "polycolor": ((item_data.get("blob") or {}).get("polycolor")) or "#FFA3A3",
                "linecolor": ((item_data.get("blob") or {}).get("linecolor")) or "#ff0000",
                "linewidth": ((item_data.get("blob") or {}).get("linewidth")) or 1,
                "fillflag": not (((item_data.get("blob") or {}).get("fillflag")) is False)
            }

            features = []
            if item_data.get("type") == "C":
                for child in item_data.get("child") or []:
                    shape = child.get("shape")
                    if not shape:
                        continue
                    structure_number = str(child.get("housenumber") or item_name)
                    household_number = _base_household_number(structure_number)
                    features.append({
                        "structure_number": structure_number,
                        "household_number": household_number,
                        "geometry": shape
                    })
                    if household_number:
                        household_numbers.add(household_number)
            else:
                for house_no in item_data.get("child") or []:
                    household_number = _base_household_number(house_no)
                    shape = houses_map.get(household_number)
                    if not shape:
                        continue
                    features.append({
                        "structure_number": household_number,
                        "household_number": household_number,
                        "geometry": shape
                    })
                    if household_number:
                        household_numbers.add(household_number)

            if features:
                selected_layers.append({
                    "metadata_name": item_name,
                    "section_name": section_name,
                    "metadata_type": item_data.get("type") or "",
                    "style": style_data,
                    "features": features
                })

    household_map = {
        household.household_number: household
        for household in HouseholdData.objects.filter(
            slum=slum,
            household_number__in=sorted(household_numbers)
        )
    }

    export_rows = []
    for layer in selected_layers:
        metadata_name = layer["metadata_name"]
        section_name = layer["section_name"]
        metadata_type = layer["metadata_type"]
        style_data = layer["style"]

        for feature in layer["features"]:
            geometry = feature.get("geometry")
            if not geometry:
                continue

            structure_number = str(feature.get("structure_number") or metadata_name)
            household_number = _base_household_number(feature.get("household_number") or structure_number)
            household = household_map.get(household_number)

            extended_data = {
                "metadata_name": metadata_name,
                "section_name": section_name,
                "metadata_type": metadata_type,
                "structure_number": structure_number,
                "household_number": household_number,
                "slum_name": slum.name,
                "city_name": slum.electoral_ward.administrative_ward.city.name.city_name,
                "administrative_ward": slum.electoral_ward.administrative_ward.name,
                "electoral_ward": slum.electoral_ward.name,
                "selected_filters": ", ".join(selected_filters),
                "has_household_data": "Yes" if household else "No",
            }

            if household:
                extended_data["submission_date"] = household.submission_date
                extended_data["created_date"] = household.created_date
                extended_data.update(_flatten_export_data(household.rhs_data or {}, "rhs_"))
                extended_data.update(_flatten_export_data(household.ff_data or {}, "ff_"))

            export_rows.append({
                "component": None,
                "geometry": geometry,
                "layer_name": metadata_name,
                "section_name": section_name,
                "household_number": household_number,
                "extended_data": extended_data,
                "style": style_data
            })

    return export_rows


def _build_kml_response(export_rows, slum, selected_filters):
    placemarks = []

    for row in export_rows:
        component = row["component"]
        placemarks.append(
            "<Placemark>"
            "<name>{name}</name>"
            "{style}"
            "{extended_data}"
            "{geometry}"
            "</Placemark>".format(
                name=escape(str(component.housenumber)),
                style=_kml_style(row["style"]),
                extended_data=_extended_data_kml(row["extended_data"]),
                geometry=_geometry_to_kml(component.shape)
            )
        )

    document_name = "{} Structure Export".format(slum.name)
    filename_parts = [slugify(slum.name) or "slum", "structure-export"]
    if selected_filters:
        filename_parts.append("filtered")
    filename = "-".join(filename_parts) + ".kml"

    kml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2">'
        '<Document>'
        '<name>{name}</name>'
        '<description>{description}</description>'
        '{placemarks}'
        '</Document>'
        '</kml>'
    ).format(
        name=escape(document_name),
        description=escape(
            "Filtered KML export for {}{}".format(
                slum.name,
                " | Filters: {}".format(", ".join(selected_filters)) if selected_filters else ""
            )
        ),
        placemarks="".join(placemarks)
    )

    response = HttpResponse(kml, content_type="application/vnd.google-earth.kml+xml")
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
    return response


def _kml_document_from_rows(rows, document_name, description):
    placemarks = []
    style_defs = []
    style_ids = {}

    for index, row in enumerate(rows):
        style_key = json.dumps(row.get("style") or {}, sort_keys=True)
        if style_key not in style_ids:
            style_id = "style_{}".format(index)
            style_ids[style_key] = style_id
            style_defs.append(
                '<Style id="{style_id}">{style_body}</Style>'.format(
                    style_id=style_id,
                    style_body=_kml_style(row["style"]).replace("<Style>", "").replace("</Style>", "")
                )
            )

    for row in rows:
        geometry = row.get("geometry")
        if geometry is None and row.get("component") is not None:
            geometry = json.loads(row["component"].shape.geojson)
        if not geometry:
            continue

        feature_name = row["extended_data"].get("structure_number") or row["layer_name"]
        style_key = json.dumps(row.get("style") or {}, sort_keys=True)
        placemarks.append(
            "<Placemark>"
            "<name>{name}</name>"
            "<styleUrl>#{style_id}</styleUrl>"
            "{extended_data}"
            "{geometry}"
            "</Placemark>".format(
                name=escape(str(feature_name)),
                style_id=style_ids[style_key],
                extended_data=_extended_data_kml(row["extended_data"]),
                geometry=_geometry_to_kml(type("G", (), {"geojson": json.dumps(geometry)})())
            )
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2">'
        '<Document>'
        '<name>{name}</name>'
        '<description>{description}</description>'
        '{styles}'
        '{placemarks}'
        '</Document>'
        '</kml>'
    ).format(
        name=escape(document_name),
        description=escape(description),
        styles="".join(style_defs),
        placemarks="".join(placemarks)
    )


def _build_kml_zip_response(export_rows, slum, selected_filters, include_csv=False):
    prefix = "{}-layer-export".format(slugify(slum.name) or "slum")
    with tempfile.TemporaryDirectory() as tmp_dir:
        merged_name = prefix + "-merged.kml"
        merged_description = "Merged KML export for {}{}".format(
            slum.name,
            " | Filters: {}".format(", ".join(selected_filters)) if selected_filters else ""
        )
        with open(os.path.join(tmp_dir, merged_name), "w", encoding="utf-8") as merged_file:
            merged_file.write(_kml_document_from_rows(export_rows, "{} Merged Export".format(slum.name), merged_description))

        layer_groups = OrderedDict()
        for row in export_rows:
            layer_groups.setdefault(row["layer_name"], []).append(row)

        for layer_name, rows in layer_groups.items():
            file_name = "{}.kml".format(_safe_file_name(layer_name))
            with open(os.path.join(tmp_dir, file_name), "w", encoding="utf-8") as layer_file:
                layer_file.write(
                    _kml_document_from_rows(
                        rows,
                        "{} - {}".format(slum.name, layer_name),
                        "Layer export for {}".format(layer_name)
                    )
                )

        summary_csv_rows = _build_filter_summary_csv_rows(export_rows)
        if summary_csv_rows:
            summary_columns = list(summary_csv_rows[0].keys())
            summary_csv_path = os.path.join(tmp_dir, prefix + "_filter_summary.csv")
            with open(summary_csv_path, "w", encoding="utf-8") as csv_file:
                csv_file.write(",".join(_csv_escape(col) for col in summary_columns) + "\n")
                for row in summary_csv_rows:
                    csv_file.write(",".join(_csv_escape(row.get(col, "")) for col in summary_columns) + "\n")

        csv_rows = [dict(row["extended_data"]) for row in export_rows]
        if include_csv and csv_rows:
            csv_columns = sorted({key for row in csv_rows for key in row.keys()})
            csv_path = os.path.join(tmp_dir, prefix + "_detailed_hh_ff_data.csv")
            with open(csv_path, "w", encoding="utf-8") as csv_file:
                csv_file.write(",".join(_csv_escape(col) for col in csv_columns) + "\n")
                for row in csv_rows:
                    csv_file.write(",".join(_csv_escape(row.get(col, "")) for col in csv_columns) + "\n")

        qml_dir = os.path.join(tmp_dir, "qml")
        os.makedirs(qml_dir, exist_ok=True)
        merged_layer_styles = OrderedDict()
        for row in export_rows:
            merged_layer_styles[row["layer_name"]] = row["style"]

        with open(os.path.join(qml_dir, prefix + "-merged.qml"), "w", encoding="utf-8") as qml_file:
            qml_file.write(_qml_content_for_merged(merged_layer_styles, "polygon"))

        for layer_name, rows in layer_groups.items():
            geometry_type = rows[0].get("geometry", {}).get("type", "Polygon") if rows else "Polygon"
            with open(os.path.join(qml_dir, "{}.qml".format(_safe_file_name(layer_name))), "w", encoding="utf-8") as qml_file:
                qml_file.write(_qml_content_for_layer(layer_name, rows[0]["style"], geometry_type))

        zip_path = os.path.join(tmp_dir, prefix + ".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_name in os.listdir(tmp_dir):
                if file_name.endswith(".kml"):
                    zip_file.write(os.path.join(tmp_dir, file_name), arcname=file_name)
                elif file_name.endswith(".csv"):
                    zip_file.write(os.path.join(tmp_dir, file_name), arcname=file_name)
            for file_name in os.listdir(qml_dir):
                zip_file.write(os.path.join(qml_dir, file_name), arcname=os.path.join("qml", file_name))

        with open(zip_path, "rb") as zip_file:
            response = HttpResponse(zip_file.read(), content_type="application/zip")
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(prefix + ".zip")
            return response


def _sld_content_for_layer(layer_name, style_data, geometry_type):
    polycolor = _normalize_hex_color(style_data.get("polycolor"), "#de81ff")
    linecolor = _normalize_hex_color(style_data.get("linecolor"), "#000000")
    linewidth = str(style_data.get("linewidth") or 0.25)

    if geometry_type in ["Point", "MultiPoint"]:
        symbolizer = (
            "<PointSymbolizer>"
            "<Graphic>"
            "<Mark>"
            "<WellKnownName>circle</WellKnownName>"
            "<Fill><CssParameter name=\"fill\">{fill}</CssParameter></Fill>"
            "<Stroke><CssParameter name=\"stroke\">{stroke}</CssParameter><CssParameter name=\"stroke-width\">{width}</CssParameter></Stroke>"
            "</Mark>"
            "<Size>10</Size>"
            "</Graphic>"
            "</PointSymbolizer>"
        ).format(fill=polycolor, stroke=linecolor, width=linewidth)
    elif geometry_type in ["LineString", "MultiLineString"]:
        symbolizer = (
            "<LineSymbolizer>"
            "<Stroke>"
            "<CssParameter name=\"stroke\">{stroke}</CssParameter>"
            "<CssParameter name=\"stroke-width\">{width}</CssParameter>"
            "</Stroke>"
            "</LineSymbolizer>"
        ).format(stroke=linecolor, width=linewidth)
    else:
        symbolizer = (
            "<PolygonSymbolizer>"
            "<Fill><CssParameter name=\"fill\">{fill}</CssParameter></Fill>"
            "<Stroke>"
            "<CssParameter name=\"stroke\">{stroke}</CssParameter>"
            "<CssParameter name=\"stroke-width\">{width}</CssParameter>"
            "</Stroke>"
            "</PolygonSymbolizer>"
        ).format(fill=polycolor, stroke=linecolor, width=linewidth)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" '
        'xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<NamedLayer><Name>{name}</Name><UserStyle><Title>{name}</Title><FeatureTypeStyle>'
        '<Rule><Title>{name}</Title>{symbolizer}</Rule>'
        '</FeatureTypeStyle></UserStyle></NamedLayer>'
        '</StyledLayerDescriptor>'
    ).format(name=escape(layer_name), symbolizer=symbolizer)


def _sld_content_for_merged(layer_styles, geometry_type):
    rules = []
    for layer_name, style_data in layer_styles.items():
        polycolor = _normalize_hex_color(style_data.get("polycolor"), "#de81ff")
        linecolor = _normalize_hex_color(style_data.get("linecolor"), "#000000")
        linewidth = str(style_data.get("linewidth") or 0.25)

        if geometry_type in ["Point", "MultiPoint"]:
            symbolizer = (
                "<PointSymbolizer>"
                "<Graphic><Mark><WellKnownName>circle</WellKnownName>"
                "<Fill><CssParameter name=\"fill\">{fill}</CssParameter></Fill>"
                "<Stroke><CssParameter name=\"stroke\">{stroke}</CssParameter><CssParameter name=\"stroke-width\">{width}</CssParameter></Stroke>"
                "</Mark><Size>10</Size></Graphic>"
                "</PointSymbolizer>"
            ).format(fill=polycolor, stroke=linecolor, width=linewidth)
        elif geometry_type in ["LineString", "MultiLineString"]:
            symbolizer = (
                "<LineSymbolizer><Stroke>"
                "<CssParameter name=\"stroke\">{stroke}</CssParameter>"
                "<CssParameter name=\"stroke-width\">{width}</CssParameter>"
                "</Stroke></LineSymbolizer>"
            ).format(stroke=linecolor, width=linewidth)
        else:
            symbolizer = (
                "<PolygonSymbolizer>"
                "<Fill><CssParameter name=\"fill\">{fill}</CssParameter></Fill>"
                "<Stroke><CssParameter name=\"stroke\">{stroke}</CssParameter><CssParameter name=\"stroke-width\">{width}</CssParameter></Stroke>"
                "</PolygonSymbolizer>"
            ).format(fill=polycolor, stroke=linecolor, width=linewidth)

        rules.append(
            "<Rule><Title>{name}</Title>"
            "<ogc:Filter><ogc:PropertyIsEqualTo><ogc:PropertyName>META_NAME</ogc:PropertyName><ogc:Literal>{name}</ogc:Literal></ogc:PropertyIsEqualTo></ogc:Filter>"
            "{symbolizer}</Rule>".format(name=escape(layer_name), symbolizer=symbolizer)
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld" '
        'xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<NamedLayer><Name>all_layers_merged</Name><UserStyle><Title>all_layers_merged</Title><FeatureTypeStyle>'
        '{rules}'
        '</FeatureTypeStyle></UserStyle></NamedLayer>'
        '</StyledLayerDescriptor>'
    ).format(rules="".join(rules))


def _qml_color_components(hex_color):
    color = _normalize_hex_color(hex_color, "#de81ff").lstrip("#")
    return int(color[0:2], 16), int(color[1*2:2*2], 16), int(color[2*2:3*2], 16)


def _qml_content_for_layer(layer_name, style_data, geometry_type):
    r_fill, g_fill, b_fill = _qml_color_components(style_data.get("polycolor", "#de81ff"))
    r_line, g_line, b_line = _qml_color_components(style_data.get("linecolor", "#000000"))
    width = str(style_data.get("linewidth") or 0.25)
    family = _geometry_family(geometry_type)

    if family == "point":
        symbol_layer = (
            '<symbol alpha="1" clip_to_extent="1" type="marker" name="0">'
            '<layer class="SimpleMarker" enabled="1" locked="0" pass="0">'
            '<Option type="Map"><Option name="color" type="QString" value="{fill_r},{fill_g},{fill_b},255"/>'
            '<Option name="outline_color" type="QString" value="{line_r},{line_g},{line_b},255"/>'
            '<Option name="outline_width" type="QString" value="{width}"/>'
            '<Option name="size" type="QString" value="2.5"/></Option>'
            '</layer></symbol>'
        ).format(fill_r=r_fill, fill_g=g_fill, fill_b=b_fill, line_r=r_line, line_g=g_line, line_b=b_line, width=width)
        renderer = '<renderer-v2 type="singleSymbol" symbollevels="0">{symbol}</renderer-v2>'.format(symbol=symbol_layer)
    elif family == "line":
        symbol_layer = (
            '<symbol alpha="1" clip_to_extent="1" type="line" name="0">'
            '<layer class="SimpleLine" enabled="1" locked="0" pass="0">'
            '<Option type="Map"><Option name="line_color" type="QString" value="{line_r},{line_g},{line_b},255"/>'
            '<Option name="line_width" type="QString" value="{width}"/></Option>'
            '</layer></symbol>'
        ).format(line_r=r_line, line_g=g_line, line_b=b_line, width=width)
        renderer = '<renderer-v2 type="singleSymbol" symbollevels="0">{symbol}</renderer-v2>'.format(symbol=symbol_layer)
    else:
        symbol_layer = (
            '<symbol alpha="1" clip_to_extent="1" type="fill" name="0">'
            '<layer class="SimpleFill" enabled="1" locked="0" pass="0">'
            '<Option type="Map"><Option name="color" type="QString" value="{fill_r},{fill_g},{fill_b},170"/>'
            '<Option name="outline_color" type="QString" value="{line_r},{line_g},{line_b},255"/>'
            '<Option name="outline_width" type="QString" value="{width}"/></Option>'
            '</layer></symbol>'
        ).format(fill_r=r_fill, fill_g=g_fill, fill_b=b_fill, line_r=r_line, line_g=g_line, line_b=b_line, width=width)
        renderer = '<renderer-v2 type="singleSymbol" symbollevels="0">{symbol}</renderer-v2>'.format(symbol=symbol_layer)

    return (
        '<!DOCTYPE qgis PUBLIC \'http://mrcc.com/qgis.dtd\' \'SYSTEM\'>'
        '<qgis version="3.34.0" styleCategories="Symbology">'
        '{renderer}'
        '<layerGeometryType>{geom_type}</layerGeometryType>'
        '</qgis>'
    ).format(renderer=renderer, geom_type="0" if family == "point" else "1" if family == "line" else "2")


def _qml_content_for_merged(layer_styles, geometry_family):
    categories = []
    symbols = []

    for idx, (layer_name, style_data) in enumerate(layer_styles.items()):
        r_fill, g_fill, b_fill = _qml_color_components(style_data.get("polycolor", "#de81ff"))
        r_line, g_line, b_line = _qml_color_components(style_data.get("linecolor", "#000000"))
        width = str(style_data.get("linewidth") or 0.25)
        symbol_name = str(idx)

        if geometry_family == "point":
            symbol = (
                '<symbol alpha="1" clip_to_extent="1" type="marker" name="{name}">'
                '<layer class="SimpleMarker" enabled="1" locked="0" pass="0">'
                '<Option type="Map"><Option name="color" type="QString" value="{fill_r},{fill_g},{fill_b},255"/>'
                '<Option name="outline_color" type="QString" value="{line_r},{line_g},{line_b},255"/>'
                '<Option name="outline_width" type="QString" value="{width}"/>'
                '<Option name="size" type="QString" value="2.5"/></Option>'
                '</layer></symbol>'
            ).format(name=symbol_name, fill_r=r_fill, fill_g=g_fill, fill_b=b_fill, line_r=r_line, line_g=g_line, line_b=b_line, width=width)
        elif geometry_family == "line":
            symbol = (
                '<symbol alpha="1" clip_to_extent="1" type="line" name="{name}">'
                '<layer class="SimpleLine" enabled="1" locked="0" pass="0">'
                '<Option type="Map"><Option name="line_color" type="QString" value="{line_r},{line_g},{line_b},255"/>'
                '<Option name="line_width" type="QString" value="{width}"/></Option>'
                '</layer></symbol>'
            ).format(name=symbol_name, line_r=r_line, line_g=g_line, line_b=b_line, width=width)
        else:
            symbol = (
                '<symbol alpha="1" clip_to_extent="1" type="fill" name="{name}">'
                '<layer class="SimpleFill" enabled="1" locked="0" pass="0">'
                '<Option type="Map"><Option name="color" type="QString" value="{fill_r},{fill_g},{fill_b},170"/>'
                '<Option name="outline_color" type="QString" value="{line_r},{line_g},{line_b},255"/>'
                '<Option name="outline_width" type="QString" value="{width}"/></Option>'
                '</layer></symbol>'
            ).format(name=symbol_name, fill_r=r_fill, fill_g=g_fill, fill_b=b_fill, line_r=r_line, line_g=g_line, line_b=b_line, width=width)

        categories.append('<category value="{value}" type="string" label="{label}" symbol="{symbol}"/>'.format(
            value=escape(layer_name), label=escape(layer_name), symbol=symbol_name
        ))
        symbols.append(symbol)

    renderer = (
        '<renderer-v2 type="categorizedSymbol" attr="META_NAME" symbollevels="0">'
        '<categories>{categories}</categories>'
        '<symbols>{symbols}</symbols>'
        '</renderer-v2>'
    ).format(categories="".join(categories), symbols="".join(symbols))

    return (
        '<!DOCTYPE qgis PUBLIC \'http://mrcc.com/qgis.dtd\' \'SYSTEM\'>'
        '<qgis version="3.34.0" styleCategories="Symbology">'
        '{renderer}'
        '<layerGeometryType>{geom_type}</layerGeometryType>'
        '</qgis>'
    ).format(renderer=renderer, geom_type="0" if geometry_family == "point" else "1" if geometry_family == "line" else "2")


def _build_shapefile_response(export_rows, slum, selected_filters, include_csv=False):
    prefix = "{}-layer-export".format(slugify(slum.name) or "slum")

    with tempfile.TemporaryDirectory() as tmp_dir:
        shp_dir = os.path.join(tmp_dir, "shp")
        os.makedirs(shp_dir, exist_ok=True)

        layer_groups = OrderedDict()
        for row in export_rows:
            geometry = row.get("geometry")
            if geometry is None and row.get("component") is not None:
                geometry = json.loads(row["component"].shape.geojson)
            geometry_type = geometry.get("type", "Polygon") if geometry else "Polygon"
            family = _geometry_family(geometry_type)
            key = "{}__{}".format(_safe_file_name(row["layer_name"]), family)
            if key not in layer_groups:
                layer_groups[key] = {
                    "display_name": row["layer_name"],
                    "family": family,
                    "rows": []
                }
            layer_groups[key]["rows"].append(row)

        merged_groups = OrderedDict()
        for row in export_rows:
            geometry = row.get("geometry")
            if geometry is None and row.get("component") is not None:
                geometry = json.loads(row["component"].shape.geojson)
            geometry_type = geometry.get("type", "Polygon") if geometry else "Polygon"
            family = _geometry_family(geometry_type)
            merged_groups.setdefault(family, []).append(row)

        csv_rows = []
        for group_key, group_data in layer_groups.items():
            layer_name = group_data["display_name"]
            rows = group_data["rows"]
            family = group_data["family"]
            layer_prefix = group_key
            layer_geojson = os.path.join(tmp_dir, layer_prefix + ".geojson")
            features = []
            layer_style = rows[0]["style"] if rows else {}

            for row in rows:
                feature_properties = dict(row["extended_data"])
                feature_properties["style_name"] = row["style"].get("name", "")
                feature_properties["polycolor"] = row["style"].get("polycolor", "")
                feature_properties["linecolor"] = row["style"].get("linecolor", "")
                feature_properties["section_name"] = row.get("section_name", "")
                feature_properties["META_NAME"] = row.get("layer_name", "")
                feature_properties["P_COLOR"] = _normalize_hex_color(row["style"].get("polycolor", "#de81ff"))
                feature_properties["L_COLOR"] = _normalize_hex_color(row["style"].get("linecolor", "#000000"))
                feature_properties["L_WIDTH"] = str(row["style"].get("linewidth") or 0.25)

                geometry = row.get("geometry")
                if geometry is None and row.get("component") is not None:
                    geometry = json.loads(row["component"].shape.geojson)

                features.append({
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": _shape_safe_properties(feature_properties)
                })

                csv_rows.append(feature_properties)

            with open(layer_geojson, "w", encoding="utf-8") as geojson_file:
                json.dump({
                    "type": "FeatureCollection",
                    "features": features
                }, geojson_file, ensure_ascii=False)

            layer_dir = os.path.join(shp_dir, layer_prefix)
            os.makedirs(layer_dir, exist_ok=True)
            output_shp = os.path.join(layer_dir, layer_prefix + ".shp")
            subprocess.run(
                ["ogr2ogr", "-f", "ESRI Shapefile", output_shp, layer_geojson],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            sld_path = os.path.join(layer_dir, layer_prefix + ".sld")
            sld_content = _sld_content_for_layer(layer_name, layer_style, "Point" if family == "point" else "LineString" if family == "line" else "Polygon")
            with open(sld_path, "w", encoding="utf-8") as sld_file:
                sld_file.write(sld_content)

            qml_path = os.path.join(layer_dir, layer_prefix + ".qml")
            with open(qml_path, "w", encoding="utf-8") as qml_file:
                qml_file.write(_qml_content_for_layer(layer_name, layer_style, "Point" if family == "point" else "LineString" if family == "line" else "Polygon"))

        for family, rows in merged_groups.items():
            layer_prefix = "all_layers_merged_{}".format(family)
            layer_geojson = os.path.join(tmp_dir, layer_prefix + ".geojson")
            features = []
            merged_layer_styles = OrderedDict()

            for row in rows:
                feature_properties = dict(row["extended_data"])
                feature_properties["style_name"] = row["style"].get("name", "")
                feature_properties["polycolor"] = row["style"].get("polycolor", "")
                feature_properties["linecolor"] = row["style"].get("linecolor", "")
                feature_properties["section_name"] = row.get("section_name", "")
                feature_properties["META_NAME"] = row.get("layer_name", "")
                feature_properties["P_COLOR"] = _normalize_hex_color(row["style"].get("polycolor", "#de81ff"))
                feature_properties["L_COLOR"] = _normalize_hex_color(row["style"].get("linecolor", "#000000"))
                feature_properties["L_WIDTH"] = str(row["style"].get("linewidth") or 0.25)

                geometry = row.get("geometry")
                if geometry is None and row.get("component") is not None:
                    geometry = json.loads(row["component"].shape.geojson)

                features.append({
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": _shape_safe_properties(feature_properties)
                })
                merged_layer_styles[row.get("layer_name", "")] = row["style"]

            with open(layer_geojson, "w", encoding="utf-8") as geojson_file:
                json.dump({
                    "type": "FeatureCollection",
                    "features": features
                }, geojson_file, ensure_ascii=False)

            layer_dir = os.path.join(shp_dir, layer_prefix)
            os.makedirs(layer_dir, exist_ok=True)
            output_shp = os.path.join(layer_dir, layer_prefix + ".shp")
            subprocess.run(
                ["ogr2ogr", "-f", "ESRI Shapefile", output_shp, layer_geojson],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            sld_path = os.path.join(layer_dir, layer_prefix + ".sld")
            with open(sld_path, "w", encoding="utf-8") as sld_file:
                sld_file.write(_sld_content_for_merged(merged_layer_styles, "Point" if family == "point" else "LineString" if family == "line" else "Polygon"))

            qml_path = os.path.join(layer_dir, layer_prefix + ".qml")
            with open(qml_path, "w", encoding="utf-8") as qml_file:
                qml_file.write(_qml_content_for_merged(merged_layer_styles, family))

        summary_csv_rows = _build_filter_summary_csv_rows(export_rows)
        summary_csv_path = os.path.join(shp_dir, prefix + "_filter_summary.csv")
        if summary_csv_rows:
            summary_columns = list(summary_csv_rows[0].keys())
            with open(summary_csv_path, "w", encoding="utf-8") as csv_file:
                csv_file.write(",".join(_csv_escape(col) for col in summary_columns) + "\n")
                for row in summary_csv_rows:
                    csv_file.write(",".join(_csv_escape(row.get(col, "")) for col in summary_columns) + "\n")

        csv_path = os.path.join(shp_dir, prefix + "_detailed_hh_ff_data.csv")
        if include_csv and csv_rows:
            csv_columns = sorted({key for row in csv_rows for key in row.keys()})
            with open(csv_path, "w", encoding="utf-8") as csv_file:
                csv_file.write(",".join(_csv_escape(col) for col in csv_columns) + "\n")
                for row in csv_rows:
                    csv_file.write(",".join(_csv_escape(row.get(col, "")) for col in csv_columns) + "\n")

        zip_path = os.path.join(tmp_dir, prefix + ".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, _, files in os.walk(shp_dir):
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                    arcname = os.path.relpath(full_path, shp_dir)
                    zip_file.write(full_path, arcname=arcname)

        with open(zip_path, "rb") as zip_file:
            response = HttpResponse(zip_file.read(), content_type="application/zip")
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(prefix + ".zip")
            return response


@require_POST
def export_filtered_kml(request):
    if not (request.user.is_superuser or request.user.username == "GIS"):
        return JsonResponse({"error": "You do not have permission to download GIS exports."}, status=403)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    slum_id = payload.get("slum_id")
    selected_households = payload.get("house_numbers") or []
    selected_filters = payload.get("selected_filters") or []
    selected_sections = payload.get("selected_sections") or []
    export_selection = payload.get("export_selection") or []
    include_csv = bool(payload.get("include_csv"))
    export_format = str(payload.get("export_format") or "kml").lower()
    style_map = payload.get("style_map") or {}
    fallback_style = payload.get("fallback_style") or {}

    if not slum_id:
        return JsonResponse({"error": "slum_id is required"}, status=400)

    slum = get_object_or_404(Slum, pk=slum_id)

    if export_selection:
        component_data = _build_component_data_from_db(slum, str(slum_id), export_selection, selected_sections)
        export_rows = _build_export_rows_from_component_selection(
            component_data=component_data,
            slum=slum,
            selected_filters=selected_filters,
            selected_sections=selected_sections,
            export_selection=export_selection
        )
    else:
        structure_components = list(
            slum.components.filter(metadata__name="Structure").order_by("housenumber")
        )
        if not structure_components:
            structure_components = list(
                slum.components.filter(metadata__code="HouseBaseLayer").order_by("housenumber")
            )

        if not structure_components:
            return JsonResponse({"error": "No structure KML data found for this slum."}, status=404)

        selected_households = {
            _base_household_number(house_no)
            for house_no in selected_households
            if str(house_no).strip()
        }

        if selected_households:
            structure_components = [
                component for component in structure_components
                if _base_household_number(component.housenumber) in selected_households
            ]

        if not structure_components:
            return JsonResponse({"error": "No matching structures found for the selected filters."}, status=404)

        export_rows = _build_export_rows(
            structure_components=structure_components,
            slum=slum,
            selected_filters=selected_filters,
            style_map=style_map,
            fallback_style=fallback_style
        )

    if not export_rows:
        return JsonResponse({"error": "No selected layers available to export."}, status=404)

    if export_format == "shp":
        try:
            return _build_shapefile_response(export_rows, slum, selected_filters, include_csv=include_csv)
        except subprocess.CalledProcessError as exc:
            return JsonResponse({
                "error": exc.stderr.decode("utf-8", errors="ignore") or "Shapefile export failed."
            }, status=500)

    if export_selection:
        return _build_kml_zip_response(export_rows, slum, selected_filters, include_csv=include_csv)

    return _build_kml_response(export_rows, slum, selected_filters)

@login_required
def can_refresh_section(request):
    result = {
        "can_refresh": request.user.has_perm("component.can_refresh_section")
    }
    return JsonResponse(result)
