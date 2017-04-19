from django.shortcuts import render
from sponsor.models import *	
from django.views.decorators.csrf import csrf_exempt

# Create your views here.


def sponsors(request):
	data=request.user
	Sp = Sponsor.objects.filter(user=data)
	k = 0
	for i in Sp:
		k = i.id
		print i.id
		print i.user
	print "k=" + str(k)	
	sponsor_projectArray = []
	slumnameArray = []	
	Spd=SponsorProjectDetails.objects.filter(sponsor=k)
	for i in Spd:#print i.sponsor_project.name#print i.slum.nam#print i.slum.id
	    sponsor_projectArray.append(i.sponsor_project.name)
	dataarray =[]    
	for i in sponsor_projectArray:
		data = {}
		Spd = SponsorProjectDetails.objects.filter(sponsor_project__name=i)
		for j in Spd:
			slumdict={}
			print j.slum.name
			print j.slum.id
			print len(j.household_code)
			slumdict.update({'slumname':j.slum.name,'id':j.slum.id,'count':len(j.household_code)})
			slumnameArray.append(slumdict)
		data.update({'sponsor_project_name':i,'slumnames':slumnameArray})
		dataarray.append(data)
	print dataarray	    
	jsondata ={}
	jsondata= { 'dataarray'  : dataarray}
			
	return render(request, 'sponsors.html', {'jsondata':jsondata})

#Spd=SponsorProjectDetails.objects.filter(sponsor_project__name='ambedkar slum collection')
#[{'slumnames': [{'count': '2', 'name': 'ambedkarnagar', 'id': '12'}, {'count': '3', 'name': 'mahatama gandhi', 'id': '10'}], 'name': 'alphalevel'}...{}]

