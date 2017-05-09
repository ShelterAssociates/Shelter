from django.shortcuts import render
from sponsor.models import *
from master.models import *	
from django.views.decorators.csrf import csrf_exempt
import simplejson as json


def sponsors(request):
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
			print j.slum.name
			print j.slum.electoral_ward.administrative_ward.city
			print j.slum.electoral_ward.administrative_ward.city.id
			cref=CityReference.objects.get(id=j.slum.electoral_ward.administrative_ward.city.name_id)
			print cref.city_name
			slumdict.update({'slumname':j.slum.name,
							 'slum_id':j.slum.id,'count':len(j.household_code) ,
							 'cityname' : str(cref.city_name)
							 ,'city_id' : j.slum.electoral_ward.administrative_ward.city.id})
			print slumdict
			slumnameArray.append(slumdict)
		data.update({'sponsor_project_name':i,'slumnames':slumnameArray})
		dataarray.append(data)
	print ("dataarray",":", dataarray) 	    
	jsondata ={}
	jsondata= { 'dataarray'  : dataarray}
	return render(request, 'sponsors.html', {'jsondata':jsondata})