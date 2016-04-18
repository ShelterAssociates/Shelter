from django.shortcuts import render
from django.template import RequestContext,loader
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required

from django import template
from django.template.loader import get_template
from django.shortcuts import render,render_to_response,get_object_or_404
import urllib2,urllib
import json
import simplejson 
from .models import City,Survey
from .forms import SurveyCreateForm
from .models import Survey
from django.views.generic import ListView
from django.views.generic.edit import FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
# Create your views here.

@staff_member_required
def index(request):
	template = get_template('index.html')
	context = RequestContext(request, {})
	return HttpResponse(template.render(context))


class SurveyListView(ListView):
	template_name = 'SurveyListView.html'
	model = City


class SurveyCreateView(FormView):
	template_name = 'SurveyCreate_form.html'
	form_class=SurveyCreateForm
	#success_url='surveymapping/'
	
	def form_valid(self, form):
		return super(SurveyCreateView, self).form_valid(form)
       	