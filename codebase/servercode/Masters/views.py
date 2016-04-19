from django.shortcuts import render
from django.template import RequestContext,loader
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django import template
from django.template.loader import get_template
from django.shortcuts import render,render_to_response,get_object_or_404
from .models import City,Survey
from .forms import SurveyCreateForm
from .models import Survey
from django.views.generic import ListView
from django.views.generic.edit import FormView,CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
import json


@staff_member_required
def index(request):
	template = get_template('index.html')
	context = RequestContext(request, {})
	return HttpResponse(template.render(context))


class SurveyListView(ListView):
	template_name = 'SurveyListView.html'
	model = Survey


class SurveyCreateView(FormView):
	template_name = 'SurveyCreate_form.html'
	form_class=SurveyCreateForm
	success_url='SurveyCreate/'
	print "survey Creation "
	
	def form_valid(self, form):
		print "hello"
		print form['Survey_type'].value()
		
		#dd.Survey_type=form['Survey_type'].value()
		#email = form.Survey_type_choices_display()
		form.save()
		
		return super(SurveyCreateView, self).form_valid(form)
	
	def form_invalid(self, form):
		print "456"
		#return HttpResponseRedirect(self.get_success_url())		
		return super(SurveyCreateView, self).form_invalid(form)
	
	def get_success_url(self):			
		return reverse('SurveyCreate')   

def SurveyDeleteView(request):
	id = request.GET.get('id', None)
	if id:
		obj = Survey.objects.get(id=id)
		if obj:
			obj.delete()
		message = 'Success'
	else:
		message = 'Failure'
	data = {}
	data['message']= message
	context = RequestContext(request)
	return render_to_response('SurveyListView.html',data, context)
