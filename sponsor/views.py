from django.shortcuts import render

# Create your views here.

@csrf_exempt
def sponsors(request):
	return render(request, 'sponsors.html', {'form': form})
