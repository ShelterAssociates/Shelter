from django.shortcuts import render
from sponsor.models import *
from master.models import *	
from django.views.decorators.csrf import csrf_exempt
import json
from component.cipher import *
import commands
import zipfile
import os

"""
def sponsors(request):
	print "user: " + str(request.user)
	data=request.user
	Sp = Sponsor.objects.filter(user=data)
	k = 0
	for i in Sp:
		k = i.id
	print "k=" + str(k)	
	sponsor_projectArray = []
	Spd=SponsorProjectDetails.objects.filter(sponsor=k)
	for i in Spd:##print i.sponsor_project.name#print i.slum.nam#print i.slum.id
	    sponsor_projectArray.append(str(i.sponsor_project.name))
	sponsor_projectArray = sorted(set(sponsor_projectArray))
	print sponsor_projectArray
	dataarray =[]    	
	for i in sponsor_projectArray:
		slumnameArray = []	
		data = {}
		Spd = SponsorProjectDetails.objects.filter(sponsor_project__name=i,sponsor__user=request.user)
		for j in Spd:
			slumdict={}
			project_type_index=j.sponsor_project.project_type
			TYPE_CHOICESdict=dict(TYPE_CHOICES)
			print TYPE_CHOICESdict[project_type_index]
			print j.slum.name
			print j.slum.electoral_ward.administrative_ward.city
			print j.slum.electoral_ward.administrative_ward.city.id
			cref=CityReference.objects.get(id=j.slum.electoral_ward.administrative_ward.city.name_id)
			print cref.city_name
			slumdict.update({'slumname':j.slum.name,
							 'slum_id':j.slum.id,'count':len(j.household_code) ,
							 'cityname' : str(cref.city_name)
							 ,'city_id' : j.slum.electoral_ward.administrative_ward.city.id,	
							 'project_type': TYPE_CHOICESdict[project_type_index]
							 })
			print slumdict
			slumnameArray.append(slumdict)
		data.update({'sponsor_project_name':i,'slumnames':slumnameArray})
		dataarray.append(data)
	print ("dataarray",":", dataarray) 	    
	jsondata ={}
	jsondata= { 'dataarray'  : dataarray}
	return render(request, 'sponsors.html', {'jsondata':jsondata})

"""

"""	

def sponsors(request):
	cities = [
    {'name': 'Mumbai', 'population': '19,000,000', 'country': 'India'},
    {'name': 'Calcutta', 'population': '15,000,000', 'country': 'India'},
    {'name': 'New York', 'population': '20,000,000', 'country': 'USA'},
    {'name': 'Chicago', 'population': '7,000,000', 'country': 'USA'},
    {'name': 'Tokyo', 'population': '33,000,000', 'country': 'Japan'},
	]
	jsondata ={}
	jsondata = { 'cities' : cities }
	return render(request, 'sponsors.html', {'cities':cities})
"""


def sponsors(request):
	#print "user: " + str(request.user)
	print "Sponsors madhe aala"
	data=request.user
	Sp = Sponsor.objects.filter(user=data)
	k = 0
	#print "Sp = " + str(Sp)
	for i in Sp:
		k = i.id
	#print "k=" + str(k)	
	sponsor_projectArray = []
	Spd=SponsorProjectDetails.objects.filter(sponsor=k)
	for i in Spd:##print i.sponsor_project.name#print i.slum.nam#print i.slum.id
	    sponsor_projectArray.append(str(i.sponsor_project.name))
	sponsor_projectArray = sorted(set(sponsor_projectArray))
	#print sponsor_projectArray
	dataarray =[]
	cipher = AESCipher()
	slumnameArray = []    	
	for i in sponsor_projectArray:
		data = {}
		Spd = SponsorProjectDetails.objects.filter(sponsor_project__name=i,sponsor__user=request.user)
		for j in Spd:
			slumdict={}
			project_type_index=j.sponsor_project.project_type
			TYPE_CHOICESdict=dict(TYPE_CHOICES)
			cref=CityReference.objects.get(id=j.slum.electoral_ward.administrative_ward.city.name_id)
			slumdict.update({'slumname':j.slum.name,
							 'slum_id':j.slum.id,'count':len(j.household_code),
							 'cityname' : str(cref.city_name),
							 'city_id' : j.slum.electoral_ward.administrative_ward.city.id,	
							 'city_id_encrypted' : "city::" + cipher.encrypt(str(j.slum.electoral_ward.administrative_ward.city.id)),
							 'project_type': TYPE_CHOICESdict[project_type_index]
							 })
			#print slumdict
			slumnameArray.append(slumdict)
		data.update({'sponsor_project_name':i,'slumnames':slumnameArray})
		dataarray.append(data)
	#print ("dataarray",":", dataarray)
	#print ("slumnameArray:",":",slumnameArray)  	    
	jsondata ={}
	jsondata= { 'dataarray'  : dataarray}
	return render(request, 'sponsors.html', {'cities':slumnameArray})

def create_zip(request, slumname):

	print "We are in create_zzip"

	cipher = AESCipher()
	user_id = request.user.id
	logged_sponsor = Sponsor.objects.get(user__id = user_id)
	SlumObj = Slum.objects.get(name = slumname)
	sponsored_slums = SponsorProjectDetails.objects.filter(slum = SlumObj).filter(sponsor = logged_sponsor)
	
	rp_slum_code = str(SlumObj.shelter_slum_code)


	folder_name = '/home/shelter/Documents/Project/Shelter/media/'+ str(request.user)
	os.mkdir(folder_name)
	print sponsored_slums[0].household_code
	for household_code in sponsored_slums[0].household_code:

		key = cipher.encrypt(str(rp_slum_code) + '|' + str(household_code) + '|' +  str(request.user.id))
		com = "sh /home/shelter/BIRT_NEW/ReportEngine/genReport.sh -f PDF -o "+folder_name+"/household_code_"+str(household_code)+".pdf -p key=" + key + " /home/shelter/Documents/Project/Shelter/reports/FFReport.rptdesign"
		os.system(com)
		print "os.system(com) execute zalay"
	zf = zipfile.ZipFile("myzipfile111.zip", "w")	
	for dirName, subdirList, fileList in os.walk(request.user):
		print "dirName= " + dirName 
		zf.write(dirName)
		for fname in fileList:
			zf.write(os.path.join(dirName, fname))
			print "Zip is being written"
        #print fname


	os.rmdir(folder_name)
	return render(request, 'sponsors.html')
