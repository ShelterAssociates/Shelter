from django.shortcuts import render
from django.template import RequestContext,loader
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import requires_csrf_token

# Create your views here.
@staff_member_required
def index(request):
	template = loader.get_template('index.html')
	context = RequestContext(request, {})
	return HttpResponse(template.render(context))


