from django import template
from django.core.urlresolvers import reverse,reverse_lazy
from django.contrib.admin.views.decorators import staff_member_required
from django.template import RequestContext,loader
from django.template.loader import get_template
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render,render_to_response,get_object_or_404
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import FormView,CreateView, UpdateView, DeleteView
from models import City,Survey,CityReference
from forms import SurveyCreateForm
import json


@staff_member_required
def index(request):
	template = loader.get_template('index.html')
	context = RequestContext(request, {})
	return HttpResponse(template.render(context))


class SurveyListView(ListView):
	template_name = 'SurveyListView.html'
	model = Survey


class SurveyCreateView(FormView):
	template_name = 'SurveyCreate_form.html'
	form_class=SurveyCreateForm
	success_url='SurveyCreate/'
	
	def dispatch(self, request, *args, **kwargs):		
		try:
			if kwargs['survey'] :
				self.id=kwargs['survey']
		except :
			print "Error"		
		return super(SurveyCreateView, self).dispatch(request, *args, **kwargs)
	

	def get_context_data(self, **kwargs):
	 	context_data = super(SurveyCreateView, self).get_context_data(**kwargs)
	 	try:
	 		if self.id:	 	
	 			self.surveydata=Survey.objects.get(id=self.id)
	 			context_data['form']=self.form_class(initial={'name':self.surveydata.name, 'description':self.surveydata.description,
                             'city':self.surveydata.city,'survey_type':self.surveydata.survey_type,
                             'analysis_threshold':self.surveydata.analysis_threshold,
                             'kobotool_survey_id':self.surveydata.kobotool_survey_id,
                             'survey':self.surveydata.id})
	 	except:
	 		print "get_context_data Error"
	 	return context_data
       
	
	def get_form_kwargs(self):
		kwargs = super( SurveyCreateView, self).get_form_kwargs()
		try:
			kwargs['survey']=self.id
 		except:
 		 	print "get_form_kwargs Error"
		return kwargs

		
	def form_valid(self, form):
		form.save()
		return super(SurveyCreateView, self).form_valid(form)
	
	def form_invalid(self, form):		
		return super(SurveyCreateView, self).form_invalid(form)
	
	def get_success_url(self):			
		return reverse('SurveyCreate')   	
  

def SurveyDeleteView(request,survey):
	obj = Survey.objects.get(id=survey)
	if obj:
		obj.delete()
		message = 'Success'
	else:
		message = 'Failure'
	data = {}
	data['message']= message
	return HttpResponseRedirect('/admin/surveymapping/')


@csrf_exempt
def search(request):
	id = request.POST['id']
	c = CityReference.objects.get(id=id)
	data_dict = {'city_code': str(c.city_code),'district_name':str(c.district_name),'district_code':str(c.district_code),'state_name':str(c.state_name),'state_code':str(c.state_code)}
	return HttpResponse(json.dumps(data_dict), content_type = "application/json")
