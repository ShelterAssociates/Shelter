from django.shortcuts import render
#from pykml import parser
from .forms import KMLUpload
from .models import  Component
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect
import json

def kml_upload(request):
	if request.method == 'POST':
		form = KMLUpload(request.POST or None,request.FILES)
		if form.is_valid():
			docFile = request.FILES['kmlfile'].read()
			root = parser.fromstring(docFile)
			data ={}
			for number in range((root.Document.Folder.Placemark.__len__()-1)):
				description=str(root.Document.Folder.Placemark[number].description)
				coordinates=str(root.Document.Folder.Placemark[number].MultiGeometry.Polygon.outerBoundaryIs.LinearRing.coordinates)
				data = {
					'description' : description ,
					'coordinates' : coordinates ,
				}
		return HttpResponse(json.dumps(data),content_type='application/json')
	else:
		form = KMLUpload()
	return render(request, 'kml_upload.html', {'form': form})



@csrf_exempt
def fetchcomponentdata(request,slumid):
	compo_dict={}
	compo_main={}

	for c in Component.objects.all():
		compo_dict={}
		compo_dict["name"]= c.name.compo_name
		compo_dict["id"]= c.id
		compo_dict["lat"]= str(c.shape)
		compo_dict["bgColor"]= c.background_color
		compo_dict["borderColor"]= c.border_color
		compo_dict["content"]={}
		compo_main.update({str(c.name.compo_name) : compo_dict })


	return HttpResponse(json.dumps(compo_main),content_type='application/json')
