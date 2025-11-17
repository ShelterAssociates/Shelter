from django.shortcuts import render

# Create your views here.


def digipin_generate(request):
	return render(request, "helpers/digipin_generate.html")