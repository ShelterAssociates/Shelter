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
			if kwargs['Survey_id'] :
				self.id=kwargs['Survey_id']
		except :
			print "Error"		
		return super(SurveyCreateView, self).dispatch(request, *args, **kwargs)
	

	def get_context_data(self, **kwargs):
	 	context_data = super(SurveyCreateView, self).get_context_data(**kwargs)
	 	try:
	 		if self.id:	 	
	 			self.surveydata=Survey.objects.get(id=self.id)
	 			context_data['form']=self.form_class(initial={'Name':self.surveydata.Name, 'Description':self.surveydata.Description,
                             'City_id':self.surveydata.City_id,'Survey_type':self.surveydata.Survey_type,
                             'AnalysisThreshold':self.surveydata.AnalysisThreshold,
                             'kobotoolSurvey_id':self.surveydata.kobotoolSurvey_id,
                             'Survey_id':self.surveydata.id})
	 	except:
	 		print "get_context_data Error"
	 	return context_data
       
	
	def get_form_kwargs(self):
		kwargs = super( SurveyCreateView, self).get_form_kwargs()
		try:
			kwargs['Survey_id']=self.id
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
