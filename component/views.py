from django.shortcuts import render
#from pykml import parser
from .forms import KMLUpload

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
