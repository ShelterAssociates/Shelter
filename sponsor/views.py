from django.shortcuts import render
from django.http import HttpResponse
from sponsor.models import *
from master.models import *
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required

import json
from component.cipher import *
import zipfile
import shutil
import os

@login_required(login_url='/accounts/login/')
def sponsors(request):

	cipher = AESCipher()

	# -----------------------------
	# Sponsor projects (ordered)
	# -----------------------------
	sponsor_loggedin = SponsorProject.objects.filter(
		sponsor__user=request.user
	).order_by("-start_date")

	# -----------------------------
	# Slums under sponsor
	# -----------------------------
	slums_under_sponsor = SponsorProjectDetails.objects.filter(
		sponsor__user=request.user
	)

	slums_under_sponsor_array = []

	for i in slums_under_sponsor:
		slums_under_sponsor_dict = {
			'name': i.slum.name,
			'households': i.household_code,
			'project_of_slum': i.sponsor_project,
			'no_of_households': len(i.household_code),
			'slum_id': i.slum.id,
			'cityname': str(i.slum.electoral_ward.administrative_ward.city.name.city_name),
			'city_id': i.slum.electoral_ward.administrative_ward.city.id,
			'city_id_encrypted': "city::" + str(
				cipher.encrypt(str(i.slum.electoral_ward.administrative_ward.city.id))
			),
			'subfields': i.sponsorprojectdetailssubfields_set.all()
		}
		slums_under_sponsor_array.append(slums_under_sponsor_dict)

	slums_under_sponsor_array = sorted(
		slums_under_sponsor_array,
		key=lambda k: k['cityname']
	)

	# -----------------------------
	# Build projects data
	# -----------------------------
	projects_under_sponsor_array = []

	for l in sponsor_loggedin:

		no_of_households = 0
		no_of_households_q1 = 0
		no_of_households_q2 = 0
		no_of_households_q3 = 0
		no_of_households_q4 = 0

		tempArray = []

		for m in slums_under_sponsor_array:
			if str(l.name) == str(m['project_of_slum']):
				no_of_households += m['no_of_households']
				tempArray.append(m)

		# -----------------------------
		# VALIDATE IMAGES (KEY FIX)
		# -----------------------------
		all_images = ProjectImages.objects.filter(
			sponsor_project__name=l.name
		)

		valid_images = []
		for img in all_images:
			if img.image and default_storage.exists(img.image.name):
				valid_images.append(img)

		# -----------------------------
		# Documents
		# -----------------------------
		docs = ProjectDocuments.objects.filter(
			sponsor_project__name=l.name
		)

		projects_under_sponsor_dict = {
			'project_Name': l.name,
			'project_Type': l.project_type,
			'start_year': l.start_date,
			'end_year': l.end_date,
			'status': l.status,
			'q1_households': no_of_households_q1,
			'q2_households': no_of_households_q2,
			'q3_households': no_of_households_q3,
			'q4_households': no_of_households_q4,
			'images': valid_images,           # ✅ only existing images
			'documents': docs,
			'slums_in_project': tempArray,
			'households_in_project': no_of_households
		}

		projects_under_sponsor_array.append(projects_under_sponsor_dict)

	# -----------------------------
	# Render
	# -----------------------------
	return render(
		request,
		'sponsors.html',
		{
			'projects': projects_under_sponsor_array
		}
	)
@login_required(login_url='/accounts/login/')
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
