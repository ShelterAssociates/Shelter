from django.shortcuts import render
from django.template import RequestContext,loader
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_memeber_required

# Create your views here.

@staff_memeber_required
def index(request):
	template = get_template('index.html')
	context = RequestContext(request, {})
	return HttpResponse(template.render(context))
   #return render(request,"admin/index.html",{})
   #return render(request,"/home/softcorner/Django_Project/lib/python2.7/site-packages/django/contrib/admin/templates/admin/index.html",{})
 

