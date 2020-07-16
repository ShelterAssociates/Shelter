from django.shortcuts import render
from django.http import HttpResponse
from sponsor.models import *
from master.models import *
from django.views.decorators.csrf import csrf_exempt
import json
from component.cipher import *
import zipfile
import shutil
import os


def sponsors(request):
    sp = []#Sponsor.objects.filter(user=request.user)
    sponsor_projectArray = []#SponsorProjectDetails.objects.filter(sponsor=request.user).values_list('sponsor_project__name',flat=True)
    sponsor_projectArray = sorted(set(sponsor_projectArray))
    dataarray = []
    cipher = AESCipher()
    slumnameArray = []
    for i in sponsor_projectArray:
        data = {}
        Spd = SponsorProjectDetails.objects.filter(sponsor_project__name=i, sponsor__user=request.user)
        for j in Spd:
            slumdict = {}
            project_type_index = j.sponsor_project.project_type
            TYPE_CHOICESdict = dict(TYPE_CHOICES)
            cref = CityReference.objects.get(id=j.slum.electoral_ward.administrative_ward.city.name_id)
            slumdict.update({'slumname': j.slum.name,
                             'slum_id': j.slum.id, 'count': len(j.household_code),
                             'cityname': str(cref.city_name),
                             'city_id': j.slum.electoral_ward.administrative_ward.city.id,
                             'city_id_encrypted': "city::" + str(cipher.encrypt(
                                 str(j.slum.electoral_ward.administrative_ward.city.id))),
                             'project_type': TYPE_CHOICESdict[project_type_index],
                             'project_name': j.sponsor_project
                             })
            slumnameArray.append(slumdict)
        data.update({'sponsor_project_name': i, 'slumnames': slumnameArray})
        dataarray.append(data)
    jsondata = {}
    jsondata = {'dataarray': dataarray}

    sponsor_loggedin = SponsorProject.objects.filter(sponsor__user=request.user).order_by("start_date")
    #print sponsor_loggedin
    sponsor_project_details_subfields = SponsorProjectDetailsSubFields.objects.filter(sponsor_project_details__sponsor__user=request.user)
    slums_under_sponsor = SponsorProjectDetails.objects.filter(sponsor__user=request.user)
    # print slums_under_sponsor

    projects_under_sponsor_array = []

    slums_under_sponsor_array = []
    # print slums_under_sponsor
    for i in slums_under_sponsor:
        # print "i.quarter:" + i.quarter + i.slum.name
        slums_under_sponsor_dict = {}
        slums_under_sponsor_dict.update({
            'name': i.slum.name,
            'households': i.household_code,
            'project_of_slum': i.sponsor_project,
            'no_of_households': len(i.household_code),
            'slum_id': i.slum.id,
            'cityname': str(i.slum.electoral_ward.administrative_ward.city.name.city_name),
            'city_id': i.slum.electoral_ward.administrative_ward.city.id,
            'city_id_encrypted': "city::" + str(cipher.encrypt(
                str(i.slum.electoral_ward.administrative_ward.city.id))),
            'subfields':i.sponsorprojectdetailssubfields_set.all()
        })
        slums_under_sponsor_array.append(slums_under_sponsor_dict)
    slums_under_sponsor_array = sorted(slums_under_sponsor_array, key=lambda k: k['cityname'])
    # print slums_under_sponsor_array
    for l in sponsor_loggedin:
        no_of_households = 0
        no_of_households_q1 = 0
        no_of_households_q2 = 0
        no_of_households_q3 = 0
        no_of_households_q4 = 0
        tempArray = []
        for m in slums_under_sponsor_array:
            # print m['name'], m['project_of_slum'],l.name
            if str(l.name) == str(m["project_of_slum"]):
                #print "In here..!!!"
                no_of_households = no_of_households + m['no_of_households']
            # print m['quarter']
                '''if m['quarter'] == '1':
                    no_of_households_q1 += m['no_of_households']
                if m['quarter'] == '2':
                    no_of_households_q2 += m['no_of_households']
                if m['quarter'] == '3':
                    no_of_households_q3 += m['no_of_households']
                if m['quarter'] == '4':
                    no_of_households_q4 += m['no_of_households']'''
                tempArray.append(m)
        # print tempArray
        temp = ProjectImages.objects.filter(sponsor_project__name = l.name)
        docs = ProjectDocuments.objects.filter(sponsor_project__name = l.name)
        #print "temp :" + str(temp)
        #l.temp_set.all()
        #print "temp:" + str(temp)
        projects_under_sponsor_dict = {}
        projects_under_sponsor_dict.update({
            'project_Name': l.name,
            'project_Type': l.project_type,
            'start_year': l.start_date,
            'end_year': l.end_date,
            'status': l.status,
            'q1_households': no_of_households_q1,
            'q2_households': no_of_households_q2,
            'q3_households': no_of_households_q3,
            'q4_households': no_of_households_q4,
            'images': temp,
            'documents': l.projectdocuments_set.all(),
            'slums_in_project': tempArray,
            'households_in_project': no_of_households
        })
        projects_under_sponsor_array.append(projects_under_sponsor_dict)

    for k in projects_under_sponsor_array:
        print ("number of households in " + str(k['project_Name']) + ":" + str(k['households_in_project']))
    # print projects_under_sponsor_array

    return render(request, 'sponsors.html', {'cities': slumnameArray, 'projects': projects_under_sponsor_array})


def create_zip(request, slumname):
    cipher = AESCipher()
    user_id = request.user.id
    logged_sponsor = Sponsor.objects.get(user__id=user_id)
    SlumObj = Slum.objects.get(name=slumname)

    sponsored_slums = SponsorProjectDetails.objects.filter(slum=SlumObj).filter(sponsor=logged_sponsor)

    rp_slum_code = str(SlumObj.shelter_slum_code)
    folder_name = '/home/shelter/Documents/Project/Shelter/media/' + str(request.user)
    if os.path.isfile('/home/shelter/Documents/Project/Shelter/media/'+str(request.user)+'.zip'):

        zip_file = open(folder_name + '.zip', 'r')
        response = HttpResponse(zip_file, content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename="%s"' % str(request.user)
        return response
    else:

        os.mkdir(folder_name)
        i = 0
        for household_code in sponsored_slums[0].household_code:
            key = cipher.encrypt(str(rp_slum_code) + '|' + str(household_code) + '|' + str(request.user.id))
            com = "sh /opt/BIRT/ReportEngine/genReport.sh -f PDF -o " + folder_name + "/household_code_" + str(
                household_code) + ".pdf -p key=" + key + " /srv/Shelter/reports/FFReport.rptdesign"
            print(com)
            os.system(com)
            i = i + 1
            print("os.system(com) executed. File no." + str(i) + " created")

        shutil.make_archive(folder_name, 'zip', folder_name)

        zip_file = open(folder_name + '.zip', 'r')
        response = HttpResponse(zip_file, content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename="%s"' % str(request.user)

        delete_command = "rm -rf " + folder_name
        os.system(delete_command)
        return response
