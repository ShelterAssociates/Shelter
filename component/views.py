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
from django.db.models.functions import TruncMonth
from mastersheet.models import ToiletConstruction

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
    print("Current status:", slum.current_status)
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
    
        print("Sponsor IDs:", sponsors)
    
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
    print(metadata)
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
            # print("Processing Filter:", metad.name, "with code:", metad.code)
            # print("Field Details:", field)
            
            if city_name != 'Kolhapur' and field[0] == 'If individual water connection, type of water meter?':
                pass
            else:
                if field[0] in rhs_analysis:
                    options = []
                    options = [rhs_analysis[field[0]][option] for option in field[1].split('|,|') if option in rhs_analysis[field[0]]]
                    component['child'] = list(set(sum(options,[])))
        # # Sponsor : Depending on superuser or sponsor render the data accordingly
        elif metad.type == 'S' and (metad.authenticate == False or not request.user.is_anonymous):
            # print("Fetching Sponsor Data for Component:", metad.name) 
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
        print(object_id , comp_name)
        if not object_id or not comp_name:
            return JsonResponse({"success": False, "message": "Missing object_id or comp_name"}, status=400)

        # Try to delete the component
        try:
            comp = Component.objects.filter(object_id=object_id, metadata__name=comp_name)
            print("Component to be deleted:", comp)
            comp.delete()
            return JsonResponse({"success": True, "message": f'Component "{comp_name}" deleted successfully'})
        except Component.DoesNotExist:
            return JsonResponse({"success": False, "message": "Component not found"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    else:
        return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)

# ================== New API for Sponsor Toilet Household Month End Dates ==================
def get_household_month_end_dates(request):
    slum_id = request.GET.get('slum_id')

    if not slum_id:
        return JsonResponse({"error": "slum_id is required"}, status=400)

    toilet_filter = {
        'completion_date__isnull': False,
        'slum_id': slum_id
    }

    # ----------------------------------------------------------------
    # CASE 1: Superuser / staff → same logic as get_component
    #         only toilets whose household_number exists in
    #         SponsorProjectDetails.household_code for that slum
    # ----------------------------------------------------------------
    if request.user.is_superuser or request.user.is_staff:

        # Fetch all household codes linked to this slum via SponsorProjectDetails
        # (mirrors get_component sponsor logic)
        sponsor_households_qs = SponsorProjectDetails.objects.filter(
            slum_id=slum_id
        ).values_list("household_code", flat=True)

        all_house_codes = []
        for codes in sponsor_households_qs:
            if codes:
                try:
                    if isinstance(codes, list):
                        all_house_codes.extend(codes)
                    else:
                        all_house_codes.extend(json.loads(codes))
                except Exception:
                    pass

        # Deduplicate — same as get_component uses set()
        all_house_codes = list(set(str(c) for c in all_house_codes))

        if not all_house_codes:
            return JsonResponse({"error": "No sponsor-linked households found for this slum"}, status=404)

        toilet_filter['household_number__in'] = all_house_codes
        toilets = ToiletConstruction.objects.filter(**toilet_filter)
        return build_response(toilets, scope='all', slum_id=slum_id)

    # ----------------------------------------------------------------
    # CASE 2: Sponsor user → only their sponsor project household codes
    #         for that slum (same as get_component sponsor check)
    # ----------------------------------------------------------------
    elif request.user.groups.filter(name='sponsor').exists():
        sponsor_name = request.GET.get('sponsor_name')

        # Get sponsor IDs linked to this user
        sponsor_qs = request.user.sponsor_set.all()
        if sponsor_name:
            sponsor_qs = sponsor_qs.filter(organization_name=sponsor_name)

        sponsor_ids = sponsor_qs.values_list('id', flat=True)

        if not sponsor_ids:
            return JsonResponse({"error": "No sponsor linked to this user"}, status=403)

        # Get sponsor project IDs for this user — mirrors get_component logic
        sponsor_project_ids = SponsorProject.objects.filter(
            sponsor_id__in=sponsor_ids
        ).values_list("id", flat=True)

        # Fetch household codes only for sponsor's projects in this slum
        sponsor_households_qs = SponsorProjectDetails.objects.filter(
            sponsor_project_id__in=sponsor_project_ids,
            slum_id=slum_id
        ).values_list("household_code", flat=True)

        all_house_codes = []
        for codes in sponsor_households_qs:
            if codes:
                try:
                    if isinstance(codes, list):
                        all_house_codes.extend(codes)
                    else:
                        all_house_codes.extend(json.loads(codes))
                except Exception:
                    pass

        all_house_codes = list(set(str(c) for c in all_house_codes))

        if not all_house_codes:
            return JsonResponse({"error": "No households found for this sponsor in the given slum"}, status=404)

        toilet_filter['household_number__in'] = all_house_codes
        toilets = ToiletConstruction.objects.filter(**toilet_filter)
        return build_response(toilets, scope='sponsor', slum_id=slum_id, user=request.user)

    # ----------------------------------------------------------------
    # CASE 3: No valid role
    # ----------------------------------------------------------------
    else:
        return JsonResponse({"error": "You do not have permission to access this data"}, status=403)


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

@login_required
def can_refresh_section(request):
    result = {
        "can_refresh": request.user.has_perm("component.can_refresh_section")
    }
    return JsonResponse(result)