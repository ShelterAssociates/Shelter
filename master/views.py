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

from master.models import Survey, CityReference, Rapid_Slum_Appraisal, Slum, AdministrativeWard 
from master.models import ElectoralWard, Slum
from master.forms import SurveyCreateForm, Rapid_Slum_AppraisalForm, ReportForm

from django.views.generic.base import View
from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings

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

@csrf_exempt
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

@csrf_exempt
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

@csrf_exempt
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



#This is to for dynamic report generation

@csrf_exempt
def report(request):#
    form = ReportForm()
    return render(request,'report.html', {'form':form})


@csrf_exempt
def AdministrativewardList(request):
    cid = request.POST['id']
    Aobj = AdministrativeWard.objects.filter(city=cid)
    idArray = []
    nameArray = []
    for i in Aobj:
        nameArray.append(str(i.name))
        idArray.append(i.id)
    data ={}
    data = { 'idArray'  : idArray,
             'nameArray': nameArray
            }       
    return HttpResponse(json.dumps(data),content_type='application/json')


@csrf_exempt
def ElectoralWardList(request):
    Aid = request.POST['id']
    Eobj = ElectoralWard.objects.filter(administrative_ward=Aid)
    idArray = []
    nameArray = []
    for i in Eobj:
        nameArray.append(str(i.name))
        idArray.append(i.id)
    data ={}
    data = { 'idArray'  : idArray,'nameArray': nameArray }
    return HttpResponse(json.dumps(data),content_type='application/json')

@csrf_exempt
def SlumList(request):
    Eid = request.POST['id']
    Sobj = Slum.objects.filter(electoral_ward=Eid)
    idArray = []
    nameArray = []
    for i in Sobj:
        nameArray.append(str(i.name))
        idArray.append(i.id)
    data ={}
    data = { 'idArray' :idArray,'nameArray':nameArray}
    return HttpResponse(json.dumps(data),content_type='application/json')

@csrf_exempt
def ReportGenerate(request):
    sid = request.POST['Sid']
    Fid = request.POST['Fid']
    SlumObj = Slum.objects.get(id=sid)
    rp_slum_code = str(SlumObj.shelter_slum_code)
    rp_xform_title = Fid
    string = settings.BIRT_REPORT_URL + "Birt/frameset?__report=FactSheet.rptdesign&rp_xform_title=" + rp_xform_title + "&rp_slum_code=" + str(rp_slum_code)
    data ={}
    data = {'string': string}
    return HttpResponse(json.dumps(data),content_type='application/json')


