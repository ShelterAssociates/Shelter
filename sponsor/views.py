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
	for i in Spd:
	    print i.sponsor_project.name
	    print i.slum.name	
	    print i.slum.id
	    sponsor_projectArray.append(i.sponsor_project.name)
	    slumnameArray.append(i.slum.name)
	data ={}
	data = { 'sponsor_projectArray'  : sponsor_projectArray,
			 'slumnameArray': slumnameArray
		   }    
	return render(request, 'sponsors.html', {'data':data})