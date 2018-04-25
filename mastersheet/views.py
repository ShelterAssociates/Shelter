from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
from mastersheet.forms import find_slum, file_form
from mastersheet.models import *
from itertools import chain
from master.models import *
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import pandas
import urllib2
from django.conf import settings
import collections
from django.http import JsonResponse
from mastersheet.daily_reporting_sync import ToiletConstructionSync, CommunityMobilizaitonSync
from collections import defaultdict

#The views in this file correspond to the mastersheet functionality of shelter app.


# 'masterSheet()' is the principal view.
# It collects the data from newest version of RHS form and family factsheets
# Also, it retrieves the data of accounts and SBM. This view bundles them in a single object
# to be displayed to the front end.
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser, login_url='/admin/')
def masterSheet(request, slum_code = 0 ):
    if "slumname" in str(request.GET.get('form')):

        delimiter = 'slumname='
        slum_code = Slum.objects.filter(pk = int(request.GET.get('form').partition(delimiter)[2]) ).values_list("shelter_slum_code", flat = True)[0]



    formdict = []
    if slum_code is not 0:
        urlv = str(settings.KOBOCAT_FORM_URL)+str('data/130?query={"slum_name":"') + str(slum_code) + '"}'  # '+str(slum_code)+'
        #urlv = str(settings.KOBOCAT_FORM_URL)+str('data/98?query={"slum_name":"') + str(slum_code) + '"}'  # '+str(slum_code)+'

        url_family_factsheet = str(settings.KOBOCAT_FORM_URL)+str('data/68?format=json&query={"group_vq77l17/slum_name":"')+ str(slum_code) + str('"}&fields=["OnfieldFactsheet","group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet","group_ne3ao98/Cost_of_upgradation_in_Rs","group_ne3ao98/Where_the_individual_ilet_is_connected_to","group_ne3ao98/Use_of_toilet","group_vq77l17/Household_number"]')
        #url_family_factsheet = str(settings.KOBOCAT_FORM_URL)+str('data/97?format=json&query={"group_vq77l17/slum_name":"')+ str(slum_code) + str('"}&fields=["OnfieldFactsheet","group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet","group_ne3ao98/Cost_of_upgradation_in_Rs","group_ne3ao98/Where_the_individual_ilet_is_connected_to","group_ne3ao98/Use_of_toilet","group_vq77l17/Household_number"]')

        url_RHS_form = str(settings.KOBOCAT_FORM_URL)+str('forms/130/form.json')
        #url_RHS_form = str(settings.KOBOCAT_FORM_URL) + str('forms/98/form.json"')

        url_FF_form = str(settings.KOBOCAT_FORM_URL)+str('forms/142/form.json')

        kobotoolbox_request = urllib2.Request(urlv)
        kobotoolbox_request_family_factsheet = urllib2.Request(url_family_factsheet)
        kobotoolbox_request_RHS_form = urllib2.Request(url_RHS_form)

        kobotoolbox_request.add_header('Authorization', settings.KOBOCAT_TOKEN)
        kobotoolbox_request_family_factsheet.add_header('Authorization',
                                                        settings.KOBOCAT_TOKEN)
        kobotoolbox_request_RHS_form.add_header('Authorization', settings.KOBOCAT_TOKEN)

        res = urllib2.urlopen(kobotoolbox_request)
        res_family_factsheet = urllib2.urlopen(kobotoolbox_request_family_factsheet)
        res_RHS_form = urllib2.urlopen(kobotoolbox_request_RHS_form)

        html = res.read()
        html_family_factsheet = res_family_factsheet.read()
        html_RHS_form = res_RHS_form.read()

        formdict = json.loads(html)
        formdict_family_factsheet = json.loads(html_family_factsheet)
        formdict_RHS_form = json.loads(html_RHS_form)
        name_label_data = []

        try:
            for i in formdict_RHS_form['children']:
                temp_data = trav(i)  # trav() function traverses the dictionary to find last hanging child
                name_label_data.extend(temp_data)
        except Exception as e:
            print e
        # arranging data with respect to household numbers
        temp_FF = {obj_FF['group_vq77l17/Household_number']: obj_FF for obj_FF in formdict_family_factsheet}

        temp_FF_keys = temp_FF.keys()
        for x in formdict:
            if x['Household_number'] in temp_FF_keys:
                x.update(temp_FF[x['Household_number']])
                x['OnfieldFactsheet'] = 'Yes'

        toilet_reconstruction_fields = ['slum', 'household_number', 'agreement_date_str', 'agreement_cancelled',
                                        'septic_tank_date_str', 'phase_one_material_date_str',
                                        'phase_two_material_date_str', 'phase_three_material_date_str',
                                        'completion_date_str', 'status', 'comment', 'material_shifted_to','id']
        daily_reporting_data = ToiletConstruction.objects.extra(
            select={'phase_one_material_date_str': "to_char(phase_one_material_date, 'YYYY-MM-DD ')",
                    'phase_two_material_date_str': "to_char(phase_two_material_date, 'YYYY-MM-DD ')",
                    'phase_three_material_date_str': "to_char(phase_three_material_date, 'YYYY-MM-DD ')",
                    'septic_tank_date_str': "to_char(septic_tank_date, 'YYYY-MM-DD ')",
                    'agreement_date_str': "to_char(agreement_date, 'YYYY-MM-DD ')",
                    'completion_date_str': "to_char(completion_date, 'YYYY-MM-DD ')"}).filter(
            slum__shelter_slum_code=slum_code)

        daily_reporting_data = daily_reporting_data.values(*toilet_reconstruction_fields)

        for i in daily_reporting_data:
            i['status'] = ToiletConstruction.get_status_display(i['status'])




        temp_daily_reporting = {obj_DR['household_number']: obj_DR for obj_DR in daily_reporting_data}
        temp_DR_keys = temp_daily_reporting.keys()

        try:
            for x in formdict:
                if x['Household_number'] in temp_DR_keys:
                    x.update(temp_daily_reporting[x['Household_number']])
                    x.update({'tc_id_'+str(x['Household_number']): temp_daily_reporting[x['Household_number']]['id']})

        except Exception as err:
            print err

        sbm_fields = ['slum', 'household_number', 'name', 'application_id', 'photo_uploaded', 'created_date_str', 'id']
        sbm_data = SBMUpload.objects.extra(
            select={'created_date_str': "to_char(created_date, 'YYYY-MM-DD ')"}).filter(
            slum__shelter_slum_code=slum_code)
        sbm_data = sbm_data.values(*sbm_fields)

        temp_sbm = {obj_DR['household_number']: obj_DR for obj_DR in sbm_data}
        temp_sbm_keys = temp_sbm.keys()
        try:
            for x in formdict:
                if x['Household_number'] in temp_sbm_keys:
                    x.update(temp_sbm[x['Household_number']])
        except Exception as err:
            print err

        community_mobilization_fields = ['slum', 'household_number', 'activity_type', 'activity_date_str','id']
        community_mobilization_data = CommunityMobilization.objects.extra(
            select={'activity_date_str': "to_char(activity_date, 'YYYY-MM-DD ')"}).filter(
            slum__shelter_slum_code=slum_code)
        community_mobilization_data1 = community_mobilization_data.values(*community_mobilization_fields)
        community_mobilization_data_list = list(community_mobilization_data1)

        # The json field of 'household_numbers' will have a list of household numbers.
        # We need to sort the data with respect to each household number in order to
        # append it in formdict.

        for x in community_mobilization_data_list:
            HH_list_flat = []
            HH_list_flat.append(json.loads(x['household_number']))
            x['household_number'] = HH_list_flat[0]

        try:
            for i in range(len(community_mobilization_data)):
                y = community_mobilization_data[i]
                for z in y.household_number:
                    for x in formdict:
                        if int(x['Household_number']) == int(z):
                            new_activity_type = community_mobilization_data[i].activity_type.name
                            x.update({new_activity_type: y.activity_date_str})
                            x.update({str(new_activity_type) + "_id" : y.id})
        except Exception as e:
            print e

        vendor = VendorHouseholdInvoiceDetail.objects.filter(slum__shelter_slum_code=slum_code)
        # Arranging name_label_data with respect to label and corresponding codes('names' is the key used for them in the json) and labels
        name_label_data_dict = {
        obj_name_label_data['name']: {child['name']: child['label'] for child in obj_name_label_data['children']} for
        obj_name_label_data in name_label_data}

        for y in vendor:
            for z in y.household_number:
                for x in formdict:
                    if int(x['Household_number']) == int(z):
                        vendor_name = "vendor_type" + y.vendor.vendor_type.name
                        invoice_number = "invoice_number" + y.vendor.vendor_type.name
                        x.update({
                            vendor_name: y.vendor.name,
                            invoice_number: y.invoice_number
                        })
                        x.update({str(y.vendor.vendor_type.name) + " Invoice Number"+"_id" : y.id})
                        x.update({"Name of "+str(y.vendor.vendor_type.name)+" vendor""_id" : y.id})

                    # Changing the codes to actual labels
                    try:
                        for key_f in x:
                            for key_nl in name_label_data_dict.keys():
                                if str(key_nl) in str(key_f):
                                    string = x[key_f].split(" ")
                                    for num in string:
                                        string[string.index(num)] = name_label_data_dict[key_nl][num]
                                    x[key_f] = ", ".join(string)
                        # Handling current place of defecation column
                        for keys in x:
                            if 'group_oi8ts04/C1' in keys:
                                x.update({'current place of defecation': x['group_oi8ts04/C1']})
                            elif 'group_oi8ts04/C2' in keys:
                                x.update({'current place of defecation': x['group_oi8ts04/C2']})
                            elif 'group_oi8ts04/C3' in keys:
                                x.update({'current place of defecation': x['group_oi8ts04/C3']})
                            elif 'group_oi8ts04/C4' in keys:
                                x.update({'current place of defecation': x['group_oi8ts04/C4']})
                            elif 'group_oi8ts04/C5' in keys:
                                x.update({'current place of defecation': x['group_oi8ts04/C5']})
                    except:
                        pass




    return HttpResponse(json.dumps(formdict),  content_type = "application/json")



def trav(node):
    #Traverse up till the child node and add to list
    if 'type' in node and node['type'] == "group":
        return list(chain.from_iterable([trav(child) for child in node['children']]))
    elif (node['type'] == "select one" or node['type'] == "select all that apply") and 'children' in node.keys():
        return [node]
    return []

@user_passes_test(lambda u: u.is_superuser, login_url='/admin/')
def define_columns(request):
    """
    Method to send datatable columns.
    :param request: 
    :return: 
    """
    formdict_new = [
        {"data": "Household_number", "title": "Household Number" ,"className": "add_hyperlink"},#1
        {"data": "Date_of_survey", "title": "Date of Survey"},
        {"data": "Name_s_of_the_surveyor_s", "title": "Name of the Surveyor"},
        {"data": "Type_of_structure_occupancy", "title": "Type of structure occupancy"},
        {"data": "Type_of_unoccupied_house", "title": "Type of unoccupied house"},#5
        {"data": "Parent_household_number", "title": "Parent household number"},
        {"data": "group_og5bx85/Full_name_of_the_head_of_the_household",
         "title": "Full name of the head of the household"},
        {"data": "group_og5bx85/Type_of_survey", "title": "Type of the survey"},
        {"data": "group_el9cl08/Enter_the_10_digit_mobile_number", "title": "Mobile number"},
        {"data": "group_el9cl08/Aadhar_number", "title": "Aadhar card number"},#10
        {"data": "group_el9cl08/Number_of_household_members", "title": "Number of household members"},
        {"data": "group_el9cl08/Do_you_have_any_girl_child_chi",
         "title": "Do you have any girl child/children under the age of 18?"},
        {"data": "group_el9cl08/How_many", "title": "How many?"},
        {"data": "group_el9cl08/Type_of_structure_of_the_house", "title": "Type of structure of the house"},
        {"data": "group_el9cl08/Ownership_status_of_the_house", "title": "Ownership status of the house"},#15
        {"data": "group_el9cl08/House_area_in_sq_ft", "title": "House area in sq. ft."},
        {"data": "group_el9cl08/Type_of_water_connection", "title": "Type of water connection"},
        {"data": "group_el9cl08/Facility_of_solid_waste_collection", "title": "Facility of solid waste management"},
        {"data": "group_el9cl08/Does_any_household_m_n_skills_given_below",
         "title": "Does any household member have any of the construction skills give below?"},

        {"data": "group_oi8ts04/Have_you_applied_for_individua",
         "title": "Have you applied for an individual toilet under SBM?"},#20
        {"data": "group_oi8ts04/How_many_installments_have_you", "title": "How many installments have you received?"},
        {"data": "group_oi8ts04/When_did_you_receive_ur_first_installment",
         "title": "When did you receive your first installment?"},
        {"data": "group_oi8ts04/When_did_you_receive_r_second_installment",
         "title": "When did you receive your second installment?"},
        {"data": "group_oi8ts04/When_did_you_receive_ur_third_installment",
         "title": "When did you receive your third installment?"},
        {"data": "group_oi8ts04/If_built_by_contract_ow_satisfied_are_you",
         "title": "If built by a contractor, how satisfied are you?"},#25
        {"data": "group_oi8ts04/Status_of_toilet_under_SBM", "title": "Status of toilet under SBM?"},
        {"data": "group_oi8ts04/What_was_the_cost_in_to_build_the_toilet",
         "title": "What was the cost incurred to build the toilet?"},
        {"data": "current place of defecation", "title": "Current place of defecation"},

        {"data": "group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets",
         "title": "Is there availability of drainage to connect to the toilet?"},
        {"data": "group_oi8ts04/Are_you_interested_in_an_indiv",
         "title": "Are you interested in an individual toilet?"},#30
        {"data": "group_oi8ts04/What_kind_of_toilet_would_you_likes", "title": "What kind of toilet would you like?"},
        {"data": "group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built",
         "title": "Under what scheme would you like your toilet to be built?"},
        {"data": "group_oi8ts04/If_yes_why", "title": "If yes, why?"},
        {"data": "group_oi8ts04/If_no_why", "title": "If no, why?"},
        {"data": "group_oi8ts04/What_is_the_toilet_connected_to", "title": "What is the toilet connected to?"},#35
        {"data": "group_oi8ts04/Who_all_use_toilets_in_the_hou", "title": "Who all use toilets in the household?"},
        {"data": "group_oi8ts04/Reason_for_not_using_toilet", "title": "Reason for not using toilet"},

        {"data": "OnfieldFactsheet", "title": "Factsheet onfield"},
        {"data": "group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet",
         "title": "Have you upgraded your toilet/bathroom/house while constructing individual toilet?"},
        {"data": "group_ne3ao98/Cost_of_upgradation_in_Rs", "title": "House renovation cost"},#40
        {"data": "group_ne3ao98/Where_the_individual_ilet_is_connected_to",
         "title": "Where the individual toilet is connected to?"},
        {"data": "group_ne3ao98/Use_of_toilet", "title": "Use of toilet"},

        {"data": "name", "title": "SBM Applicant Name"},
        {"data": "application_id", "title": "Application ID"},
        {"data": "photo_uploaded", "title": "Is toilet photo uploaded on site?"},#45
        {"data": "photo_verified", "title": "Photo Verified"},
        {"data": "photo_approved", "title": "Photo Approved"},
        {"data": "application_verified", "title": "Application Verified"},
        {"data": "application_approved", "title": "Application Approved"},

        {"data": "agreement_date_str", "title": "Date of Agreement"},#50
        {"data": "agreement_cancelled", "title": "Agreement Cancelled?"},
        {"data": "septic_tank_date_str", "title": "Date of septic tank supplied"},
        {"data": "phase_one_material_date_str", "title": "Date of first phase material"},
        {"data": "phase_two_material_date_str", "title": "Date of second phase material"},
        {"data": "phase_three_material_date_str", "title": "Date of third phase material"},#55
        {"data": "completion_date_str", "title": "Construction Completion Date"},
        {"data": "material_shifted_to", "title": "Material sifted to"},
        {"data": "status", "title": "Final Status"}#58

        # Append community mobilization here #

        # Append vendor type here #
    ]
    final_data = {}
    final_data['buttons'] = collections.OrderedDict()
    final_data['buttons']['RHS'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    final_data['buttons']['Follow-up'] = [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
    final_data['buttons']['Family factsheet'] = [37, 38, 39, 40, 41]
    final_data['buttons']['SBM'] = [42, 43, 44, 45, 46, 47, 48]
    final_data['buttons']['Construction status'] = [49, 50, 51, 52, 53, 54, 55, 56, 57]

    # We define the columns for community mobilization and vendor details in a dynamic way. The
    # reason being these columns are prone to updates and additions.
    activity_pre_len = len(formdict_new)
    activity_type_model = ActivityType.objects.filter(display_flag=True).order_by('display_order')

    try:
        for i in range(len(activity_type_model)):
            formdict_new.append({"data":activity_type_model[i].name, "title":activity_type_model[i].name})
    except Exception as e:
        print e
    final_data['buttons']['Community Mobilization'] = range(activity_pre_len, len(formdict_new))

    vendor_type_model = VendorType.objects.filter(display_flag=True).order_by('display_order')
    vendor_pre_len = len(formdict_new)
    try:
        for i in vendor_type_model:
            formdict_new.append({"data":"vendor_type"+str(i.name), "title":"Name of "+str(i.name)+" vendor"})
            formdict_new.append({"data":"invoice_number"+str(i.name), "title":str(i.name) + " Invoice Number"})
    except Exception as e:
        print e
    final_data['buttons']['Accounts'] = range(vendor_pre_len, len(formdict_new))
    final_data['data'] = formdict_new
    return HttpResponse(json.dumps(final_data),  content_type = "application/json")

@user_passes_test(lambda u: u.is_superuser, login_url='/admin/')
def renderMastersheet(request):
    slum_search_field = find_slum()
    file_form1 = file_form()
    return render(request, 'masterSheet.html', {'form': slum_search_field, 'file_form':file_form1})

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser, login_url='/admin/')
def file_ops(request):
    slum_search_field = find_slum()
    file_form1 = file_form()
    response = []
    resp = {}
    if request.method == "POST":
        try:
            resp = handle_uploaded_file(request.FILES.get('file'),response)
            response = resp
        except Exception as e: 
            response.append(('msg', str(e)))
    
    
    return HttpResponse(json.dumps(response), content_type="application/json")

# Pandas libraries help us in handling DataFrames with convenience
# In the sheet that is being uploaded, the 'Agreement Cancelled' field should be blank if the agreement
# is not cancelled. If it has any entry, the agreement_cancelled field in the database will be set to
#  True
def handle_uploaded_file(f,response):

    df = pandas.read_excel(f)
    df1=df.set_index("House Number")
    # We divide the dataframe into subframes for vendors, their invoices and community mobilization

    flag_accounts = 0
    flag_SBM = 0
    flag_ComMob = 0
    flag_TC = 0

    try:
        df_vendors = df1.filter(like='Vendor Name')
        df_invoice = df1.filter(like = 'Invoice')
    except:
        flag_accounts = 1


    try:
        df_ComMob = df1.loc[:,'FGD with women':'Community Mobilization Ends']
    except:
        flag_ComMob = 1

    try:
        df_sbm = df1.loc[:,'SBM Name':'Toilet photo uploaded on SBM site']
    except:
        flag_SBM = 1
        print "error with sbm"

    try:
        df_TC = df1.loc[:,'Date of Agreement':'Final Status']
    except:
        flag_TC = 1



    # *******************************IMPORTANT!!!!*************************************
    # In the excel sheet that has been uploaded, it is imperative to have a column with
    # a header 'Community Mobilization Ends' right after the last mobilization activity's
    # column.This column will be blank. It will be used to slice a sub frame which will have
    # all the community mobilization activities.
    response.append(("total_records",len(df1.index.values)))
    for i in df1.index.values:
        this_slum = Slum.objects.get(name=df1.loc[int(i), 'Select Slum'])

        if flag_SBM != 1:
            try:
                
                SBM_instance = SBMUpload.objects.get(slum = this_slum, household_number = int(i))
                if check_null(SBM_instance.application_id) is False:
                    SBM_instance.update(
                        name=df_sbm.loc[int(i), 'SBM Name'],
                        application_id=df_sbm.loc[int(i), 'Application ID'],
                        photo_uploaded=check_bool(df_sbm.loc[int(i), 'Toilet photo uploaded on SBM site'])
                    )
                    SBM_instance.save()
                    response.append(("updated sbm", i))
            except Exception as e:
                if check_null(df1.loc[int(i), 'Application ID']) is not None:
                    SBM_instance_1 = SBMUpload(
                     slum = this_slum,
                     household_number = int(i),
                     name = df1.loc[int(i), 'SBM Name'],
                     application_id = df_sbm.loc[int(i),'Application ID'],
                     photo_uploaded = check_bool(df_sbm.loc[int(i),'Toilet photo uploaded on SBM site'])
                    )
                    SBM_instance_1.save()
                    response.append(("newly created sbm", i))

        if flag_ComMob != 1:

            for p,q in df_ComMob.loc[int(i)].items():

                if check_null(q) is not None:
                    household_nums = []
                    try:
                        activityType_instance = ActivityType.objects.get(name = p)
                        if activityType_instance:
                            try:

                                ### IMPORTANT!!!!! Date should also be considered!!! INCOMPLETE!!!!!
                                ComMob_instance = CommunityMobilization.objects.get(slum = this_slum,activity_type=activityType_instance)

                                temp = ComMob_instance.household_number
                                if int(i) not in temp:
                                    temp.append(int(i))
                                    response.append(("updated ComMob", i))
                                ComMob_instance.household_number = temp
                                ComMob_instance.save()
                                

                            except Exception as e:
                                household_nums.append(int(i))
                                CM_instance = CommunityMobilization(
                                    slum = this_slum,
                                    household_number = household_nums,
                                    activity_type = activityType_instance,
                                    activity_date = df_ComMob.loc[int(i), p]
                                )
                                CM_instance.save()
                                response.append(("newly created ComMob",i))
                    except Exception as e:
                        response.append(("The error says: " +str(e)+ ". This error is with Comminity Mobilization columns for following household numbers", i))

        if flag_accounts != 1:

            for j,m in df_vendors.loc[int(i)].items():
                if check_null(m) is not None:
                    household_nums = []
                    k = df_vendors.columns.get_loc(j)
                    string = unicode(df_invoice.loc[int(i)][k])

                    try:
                        Vendor_instance = Vendor.objects.get(name=str(m))
                        if Vendor_instance:
                            try:
                                VHID_instance_1 = VendorHouseholdInvoiceDetail.objects.get(vendor=Vendor_instance,
                                                                                       invoice_number=string.split('/')[0],
                                                                                       slum=this_slum)
                                temp = VHID_instance_1.household_number
                                if int(i) not in temp:
                                    temp.append(int(i))
                                    response.append(("updated VHID",i))
                                VHID_instance_1.household_number = temp
                                VHID_instance_1.save()
                                

                            except Exception as e:
                                print e
                                print "VHID is not found"
                                household_nums.append(int(i))
                                VHID_instance = VendorHouseholdInvoiceDetail(
                                    vendor = Vendor.objects.get(name=str(m)),
                                    slum = this_slum,
                                    invoice_number = string.split('/')[0],
                                    invoice_date     =datetime.datetime.strptime(string.split('/')[1], '%d.%m.%Y') ,
                                    household_number = household_nums
                                )
                                VHID_instance.save()
                                response.append(("newly created VHID",i))

                    except Exception as e:
                        response.append(("The error says: " +str(e)+ ". This error is with Vendor Invoice Details Columns for following household numbers", i))
                        
        if flag_TC != 1:
            try:
                TC_instance = ToiletConstruction.objects.select_related().filter(household_number = int(i), slum__name = this_slum)
                print TC_instance
                if TC_instance:
                    TC_instance[0].update_model( df_TC.loc[int(i), : ])
                    response.append(("updated TC",i))

                else:
                    this_status = " "
                    stat = df_TC.loc[int(i), 'Final Status']
                    for j in range(len(STATUS_CHOICES)):
                        if str(STATUS_CHOICES[j][1]).lower() == str(stat).lower():  # STATUS_CHOICE is imported from mastersheet/models.py
                            this_status=STATUS_CHOICES[j][0]
                   
                    TC_instance = ToiletConstruction(
                                                        slum = this_slum,
                                                        agreement_cancelled = check_bool(df_TC.loc[int(i), 'Agreement Cancelled']),
                                                        household_number = int(i),
                                                        septic_tank_date = check_null(df_TC.loc[int(i), 'Date of Septic Tank supplied']),
                                                        phase_one_material_date = check_null(df_TC.loc[int(i), 'Material Supply Date 1st']),
                                                        phase_two_material_date = check_null(df_TC.loc[int(i), 'Material Supply Date-2nd']),
                                                        phase_three_material_date = check_null(df_TC.loc[int(i), 'Material Supply Date-3rd']),
                                                        completion_date = check_null(df_TC.loc[int(i), 'Construction Completion Date']),
                                                        comment = check_null(df_TC.loc[int(i), 'Comment']),
                                                        status = this_status
                                                    )

                    TC_instance.save()
                    response.append(("newly created TC",i))
            except Exception as e:
                response.append(("The error says: " +str(e)+ ". This error is with Toilet Construction Columns for following household numbers", i))
                
   

    d = defaultdict(list)
    for k,v in response:
        d[k].append(v)
    return d
 

def check_null(s):
    if pandas.isnull(s):
        return None
    else:
        return s
def check_bool(s):
    if str(s).lower() == 'yes':
        return True
    else:
        return False

@csrf_exempt
@user_passes_test(lambda u: u.is_superuser, login_url='/admin/')
def delete_selected(request):
    """
     Method to delete selected records.
    :param request: 
    :return: 
    """
    slum_search_field = find_slum()
    file_form1 = file_form()
    response = {}
    response['response'] = "Records deleted successfully"

    records = json.loads(request.body)
    delete_selected_records(records)

    return HttpResponse(json.dumps(response), content_type="application/json")

def delete_selected_records(records):
    """
    Method to delete selected records. CALLED from delete_selected
    :param records: 
    :return: 
    """
    kobo_form = 130  # *****IMPORTANT***** This form number (98) is for local setting. Do change it to 130 before going live.
    headers = {}
    headers["Authorization"] = settings.KOBOCAT_TOKEN
    for r in records['records']:
        try:
            if r:
                deleteURL = '/'.join([settings.KOBOCAT_FORM_URL[:-1], 'data', str(kobo_form), str(r)])
                objresponseDeleted = requests.delete(deleteURL, headers=headers)
                print(' deleted for ' + str(r) + ' with response ' + str(objresponseDeleted))
        except Exception as e:
            print "No record selected to delete."

@user_passes_test(lambda u: u.is_superuser, login_url='/admin/')
def sync_kobo_data(request,slum_id):
    """
    Method to sync data from kobotoolbox for community mobilization and toilet construction status(Daily reporting)
    :param request: 
    :param slum_id: 
    :return: success/error msg
    """
    data={}
    try:
        slum = Slum.objects.get(id=slum_id)
        user = request.user
        toilet_const = ToiletConstructionSync(slum, user)
        t_data = toilet_const.fetch_data()
        com_mobilization = CommunityMobilizaitonSync(slum, user)
        c_data = com_mobilization.fetch_data()

        if any(t_data) and any(c_data):
            if t_data[2] > c_data[2]:
                toilet_const.update_sync_info(t_data[2])
            else:
                com_mobilization.update_sync_info(c_data[2])
        elif any(t_data) and not any(c_data):
            toilet_const.update_sync_info(t_data[2])
        elif not any(t_data) and any(c_data):
            com_mobilization.update_sync_info(c_data[2])
        data['flag'] = True
        if not any(t_data) and not any(c_data):
            data['msg'] = "Nothing to sync for slum - " + slum.name
        else:
            data['msg'] = "Data successfully synced for slum - "+slum.name
            data['msg'] += "\nTotal records updated : " + str(t_data[0]+c_data[0])
    except Exception as e:
        data['flag']=False
        data['msg'] = "Error occurred while sync from kobo. Please contact administrator." +str(e)
    return HttpResponse(json.dumps(data), content_type="application/json")










