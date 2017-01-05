from django.shortcuts import render
#from pykml import parser

"""
#url(r'^sluminformation/kmlinsert/$', kmlinsert, name='kmlinsert'),

@csrf_exempt
def kmlinsert(request):
	if request.method == 'POST':
		form = KMLForm(request.POST or None,request.FILES)
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
		form = KMLForm()
	return render(request, 'kmlinsert.html', {'form': form})
    """
