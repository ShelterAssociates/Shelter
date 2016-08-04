#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Views Page for master app"""
import json
import urllib2

from django.core.urlresolvers import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import FormView

from master.models import Survey, CityReference, Rapid_Slum_Appraisal, Slum
from master.forms import SurveyCreateForm, Rapid_Slum_AppraisalForm

from django.views.generic.base import View
from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

@staff_member_required
def index(request):
    """Renders the index template in browser"""
    template = loader.get_template('index.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))


class SurveyListView(ListView):
    """Renders the Survey View template in browser"""
    template_name = 'SurveyListView.html'
    model = Survey

    def get_queryset(self):
        try:
            filter_input = self.kwargs['name']
        except KeyError:
            filter_input = ''
        if filter_input != '':
            object_list = self.model.objects.filter(name__icontains=filter_input)
        else:
            object_list = self.model.objects.all()
        return object_list


class SurveyCreateView(FormView):
    """Fetches and renders the Add New Survey Mapping template in browser"""
    template_name = 'SurveyCreate_form.html'
    form_class = SurveyCreateForm
    success_url = 'SurveyCreate/'

    def dispatch(self, request, *args, **kwargs):
        """Signal Dispatcher"""
        try:
            if kwargs['survey']:
                self.id = kwargs['survey']
        except KeyError:
            print 'Error'
        return super(SurveyCreateView, self).dispatch(request, *args,
                                                      **kwargs)

    def get_context_data(self, **kwargs):
        """Returns a dictionary(json data format)"""
        context_data = super(SurveyCreateView,
                             self).get_context_data(**kwargs)
        try:
            if self.id:
                self.surveydata = Survey.objects.get(id=self.id)
                context_data['form'] = self.form_class(initial={
                    'name': self.surveydata.name,
                    'description': self.surveydata.description,
                    'city': self.surveydata.city,
                    'survey_type': self.surveydata.survey_type,
                    'analysis_threshold': self.surveydata.analysis_threshold,
                    'kobotool_survey_id': self.surveydata.kobotool_survey_id,
                    'survey': self.surveydata.id,
                    })
        except RuntimeError:
            print 'get_context_data Error'
        return context_data

    def get_form_kwargs(self):
        """'Get' request for form data"""
        kwargs = super(SurveyCreateView, self).get_form_kwargs()
        try:
            kwargs['survey'] = self.id
        except AttributeError:
            print 'get_form_kwargs Error'
        return kwargs

    def form_valid(self, form):
        """Actions to perform if form is valid"""
        form.save()
        return super(SurveyCreateView, self).form_valid(form)

    def form_invalid(self, form):
        """Actions to perform if form is invalid"""
        return super(SurveyCreateView, self).form_invalid(form)

    def get_success_url(self):
        """If form is valid -> redirect to"""
        return reverse('SurveyCreate')


def survey_delete_view(survey):
    """Delete Survey Object"""
    obj = Survey.objects.get(id=survey)
    if obj:
        obj.delete()
        message = 'Success'
    else:
        message = 'Failure'
    data = {}
    data['message'] = message
    return HttpResponseRedirect('/admin/surveymapping/')

@csrf_exempt
def search(request):
    """Autofill add city form fields based on City ID"""
    sid = request.POST['id']
    cityref = CityReference.objects.get(id=sid)
    data_dict = {
        'city_code': str(cityref.city_code),
        'district_name': str(cityref.district_name),
        'district_code': str(cityref.district_code),
        'state_name': str(cityref.state_name),
        'state_code': str(cityref.state_code),
        }
    return HttpResponse(json.dumps(data_dict),
                        content_type='application/json')

def display(request):
    """Display Rapid Slum Appraisal Records"""
    if request.method=='POST':
        deleteList=[]
        deleteList=request.POST.getlist('delete')
        for i in deleteList:
            R = Rapid_Slum_Appraisal.objects.get(pk=i)
            R.delete()                 
    R = Rapid_Slum_Appraisal.objects.all()
    paginator = Paginator(R, 1) 
    page = request.GET.get('page')
    try:
        RA = paginator.page(page)
    except PageNotAnInteger:
        RA = paginator.page(1)
    except EmptyPage:
        RA = paginator.page(paginator.num_pages)        
    return render(request, 'display.html',{'R':R,'RA':RA})

def edit(request,Rapid_Slum_Appraisal_id):
    """Update Rapid Slum Appraisal Record"""
    if request.method == 'POST':
        R = Rapid_Slum_Appraisal.objects.get(pk=Rapid_Slum_Appraisal_id)
        form = Rapid_Slum_AppraisalForm(request.POST or None,request.FILES,instance=R)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/admin/factsheet/')
    elif request.method=="GET":
        R = Rapid_Slum_Appraisal.objects.get(pk=Rapid_Slum_Appraisal_id)
        form = Rapid_Slum_AppraisalForm(instance= R)
    return render(request, 'edit.html', {'form': form})

def insert(request):
    """Insert Rapid Slum Appraisal Record"""
    if request.method == 'POST':
        form = Rapid_Slum_AppraisalForm(request.POST,request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/admin/factsheet/')
    else:
        form = Rapid_Slum_AppraisalForm()  
    return render(request, 'insert.html', {'form': form})




from django.template.loader import get_template
from django.template import Context
from django.http import Http404,HttpResponse
from django.shortcuts import render
from py4j.java_gateway import JavaGateway

def generate_birt(request):
    if'q'in request.GET:
        gateway =JavaGateway()
        stack = gateway.entry_point.getStack(request.GET['q'])
        reportHTML = stack.getReport()
        return render(request,'birt_parameters.html',{'report_html': reportHTML})
    else:
        error ='You entered an empty request!'
        return render(request,'birt_parameters.html',{'report_html':'You entered an empty request'})
"""
def birt_report(request):
    http://127.0.0.1:54678/viewer/frameset?__report=%2Fhome%2Fsoftcorner%2FBIRT%2FBIRTDemo%2Fdemo.rptdesign&__format=html&__svg=true&__locale=en_IN&__timezone=IST&__masterpage=true&__rtl=false&__cubememsize=10&__resourceFolder=%2Fhome%2Fsoftcorner%2FBIRT%2FBIRTDemo&-197343101
"""

"""

def birt_report(request, report_id, report_url=None, template='report_parameters.html'):
    if request.method == 'POST':
        form = ReportParametersForm(request.POST)
        if form.is_valid():
            report_params = form.save()
            form_id = report_params.id
            url = "http://<hostname>/Birt/frameset?__report=" + report_url + ".rptdesign"
            url += "&param_id=" + str(form_id)
            r = requests.get(url)
            return HttpResponse(content=str(r.content),status=200,content_type='text/html; charset=utf-8')
        else:
            form = ReportParametersForm()
            return render(request,template,{
                'form': form,
                'report_url': report_url,
                'report_id': report_id,
            })

"""


def birt_report(request):
    if 'lastName' in request.GET:
        message = "http://127.0.0.1:8080/Birt/frameset?__report=test.rptdesign&__format=html&sample="
        html = "<html><head><body><iframe height=300 width=600 src=" + message + "></iframe></body></html>"
        return HttpResponse(html)
    else:
        message = 'You submitted an empty form.'
        return HttpResponse(message)


