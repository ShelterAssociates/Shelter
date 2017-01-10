from django.shortcuts import render
from django.contrib import messages
from .forms import KMLUpload
from .kmlparser import KMLParser

def kml_upload(request):
    if request.method == 'POST':
        form = KMLUpload(request.POST or None,request.FILES)
        if form.is_valid():
            docFile = request.FILES['kml_file'].read()
            print form.cleaned_data
            objKML = KMLParser(docFile, form.cleaned_data['slum_name'])
            messages.success(request,'Form submission successful')
    else:
        form = KMLUpload()
    return render(request, 'kml_upload.html', {'form': form})
