#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Views Page for master app"""

import json
import psycopg2


from django.core.urlresolvers import reverse
from django.contrib.admin.views.decorators import staff_member_required 
from django.contrib.auth.decorators import login_required
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import FormView

from master.models import Survey, CityReference, Rapid_Slum_Appraisal, \
                          Slum, AdministrativeWard, ElectoralWard, City, \
                          WardOfficeContact, ElectedRepresentative
from master.forms import SurveyCreateForm, ReportForm, Rapid_Slum_AppraisalForm

from django.views.generic.base import View
from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings
from django.contrib.auth.decorators import login_required

from django.contrib.gis import geos

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
    query = request.GET.get("q") 
    if(query):
        R = Rapid_Slum_Appraisal.objects.filter(slum_name__name__contains=query)
        paginator = Paginator(R, 6) 
        page = request.GET.get('page')
        try:
            RA = paginator.page(page)
        except PageNotAnInteger:
            RA = paginator.page(1)
        except EmptyPage:
            RA = paginator.page(paginator.num_pages)      
        return render(request, 'display.html',{'R':R,'RA':RA})
    else:    
        R = Rapid_Slum_Appraisal.objects.all()
        paginator = Paginator(R, 6) 
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


@csrf_exempt
def report(request):
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
    print json.dumps(data)    
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
    string = settings.BIRT_REPORT_URL + "Birt/frameset?__format=pdf&__report=FactSheet.rptdesign&rp_xform_title=" + rp_xform_title + "&rp_slum_code=" + str(rp_slum_code)
    data ={}
    data = {'string': string}
    return HttpResponse(json.dumps(data),content_type='application/json')

@csrf_exempt
def VulnerabilityReport(request):
    string = settings.BIRT_REPORT_URL + "Birt/frameset?__format=pdf&__report=Vulnerability_Report.rptdesign"
    return HttpResponseRedirect(string)    


@csrf_exempt
def jsondata(request):
    old = psycopg2.connect(database='onadata1',user='postgres',password='softcorner',host='127.0.0.1',port='5432')
    cursor_old = old.cursor()
    cursor_old.execute("select json from logger_instance where xform_id=106 and id=9;")
    fetch_data = cursor_old.fetchone()
    data = fetch_data
    return HttpResponse(json.dumps(data),content_type='application/json')

def slummap(request):
    template = loader.get_template('slummapdisplay.html')
    context = RequestContext(request, {})
    return HttpResponse(template.render(context))

@csrf_exempt
def citymapdisplay(request):
    city_dict={}
    city_main={}
    
    for c in City.objects.all():
        city_dict={}
        city_dict["name"]= c.name.city_name
        city_dict["id"]= c.id
        city_dict["lat"]= str(c.shape)
        city_dict["bgColor"]= c.background_color
        city_dict["borderColor"]= c.border_color
        city_dict["content"]={}
        city_main.update({str(c.name.city_name) : city_dict })
        
    
    return HttpResponse(json.dumps(city_main),content_type='application/json')   

@csrf_exempt
def slummapdisplay(request,id):
    slum_list=[]
    city_dict={}
    city_main={"content" : {}}
    admin_dict={}
    admin_main={}
    elctrol_dict=dict()
    elctrol_main=dict()
    slum_dict=dict()
    slum_main=dict()
    main_list=[]
    
    
         
    admin_main={}
    for a in AdministrativeWard.objects.filter(city__id=id):
        admin_dict={}
        admin_dict["name"]=a.name
        admin_dict["id"]=a.id
        admin_dict["lat"]= str(a.shape)
        admin_dict["info"]=a.description
        admin_dict["bgColor"]=a.background_color
        admin_dict["borderColor"]=a.border_color
        
        adminwd=WardOfficeContact.objects.filter(administrative_ward = a.id)
        if adminwd :
            admin_dict["wardOfficerName"]=adminwd[0].name
            admin_dict["wardOfficeAddress"]= adminwd[0].address_info 
            admin_dict["wardOfficeTel"] = adminwd[0].telephone
        admin_dict["content"]={}
        city_main["content"].update({a.name:admin_dict})
    
        
        
    for e in ElectoralWard.objects.filter(administrative_ward__city__id=id):
        elctrol_dict={}
        elctrol_dict["name"]=e.name
        elctrol_dict["id"]=e.id
        elctrol_dict["lat"]=str(e.shape)
        elctrol_dict["info"]=e.extra_info
        elctrol_dict["bgColor"]=e.background_color
        elctrol_dict["borderColor"]=e.border_color
        
        electrolwd=ElectedRepresentative.objects.filter(electoral_ward = e.id)
        if electrolwd :
            elctrol_dict["wardOfficerName"]=electrolwd[0].name
            elctrol_dict["wardOfficeAddress"]= electrolwd[0].address +" "+electrolwd[0].post_code
            elctrol_dict["wardOfficeTel"] = electrolwd[0].tel_nos
        
        elctrol_dict["content"]={}
                   
        city_main["content"][str(e.administrative_ward.name)]["content"].update({e.name : elctrol_dict })                
             
    for s in Slum.objects.filter(electoral_ward__administrative_ward__city__id=id):
        slum_dict={}
        slum_dict["name"]=s.name
        slum_dict["id"]=s.id
        slum_dict["lat"]=str(s.shape)
        slum_dict["info"]=s.description
        slum_dict["factsheet"]=s.factsheet.url if s.factsheet else ''
        slum_dict["photo"]=s.photo.url if s.photo else ''
        
        city_main["content"]\
        [str(s.electoral_ward.administrative_ward.name)]["content"]\
        [str(s.electoral_ward.name)]["content"].update({s.name : slum_dict })                
    return HttpResponse(json.dumps(city_main),content_type='application/json')
    

@csrf_exempt
def Acitymapdisplay(request):
    Shape="";
    cid = request.POST['id']
    print cid
    Aobj = AdministrativeWard.objects.filter(city=cid)
    for i in Aobj:
        Shape=str(i.shape)
    return HttpResponse(json.dumps(Shape),content_type='application/json')

