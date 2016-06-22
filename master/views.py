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

from master.models import Survey, CityReference, Person ,RAPID_SLUM_APPRAISAL
from master.forms import SurveyCreateForm

from django.views.generic.base import View
from wkhtmltopdf.views import PDFTemplateResponse

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


class mypdfview(View):#url="http://kc.shelter-associates.org/api/v1/data/161?format=json" #url= "http://45.56.104.240:8001/api/v1/data/161?format=json"
    url= "http://45.56.104.240:8001/api/v1/data/161?format=json"
    req = urllib2.Request(url)
    req.add_header('Authorization', 'OAuth2 a0028f740988d80cbe670f24a9456d655b8dd419')
    resp = urllib2.urlopen(req)
    content = resp.read()
    data = json.loads(content)
    p=data[0]
    result=p['_attachments']
    print type(result)
    slumname ="PuneSlum"
    datadict = {slumname :"PuneSlum"}
    SurveyNumber = 1
    img ="http://45.56.104.240:8001/media/"+result[0]['filename']
    template='report.html'
    print datadict[slumname]
    context= {'img':img,'data':data,'datadict':datadict}
    print img
    def get(self, request):
        response = PDFTemplateResponse(request=request,
                                        template=self.template,
                                        filename="hello.pdf",
                                        context= self.context,
                                       show_content_in_browser=False,
                                       cmd_options={'margin-top': 50,},
                                       )
        return response

"""
def report(request):
    t = loader.get_template('index.html')
    c = Context({'message': 'Hello world!'})
    return HttpResponse(t.render(c))
    
"""
def report(request):
    return HttpResponse("Hello world!")
"""
def insert(request):
    # If this is a post request we insert the person
    if request.method == 'POST':
        p = Person(
            name=request.POST['name'],
            phone=request.POST['phone'],
            age=request.POST['age']
        )
        p.save()

    t = loader.get_template('insert.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c))
"""
def delete(request, person_id):
    p = Person.objects.get(pk=person_id)
    p.delete()
    return HttpResponseRedirect('/')
    
"""
def edit(request, person_id):
    p = Person.objects.get(pk=person_id)
    if request.method == 'POST':
        p.name = request.POST['name']
        p.phone = request.POST['phone']
        p.age = request.POST['age']
        p.save()
    t = loader.get_template('insert.html')
    c = RequestContext(request, {
        'person': p
    })
    return HttpResponse(t.render(c))
"""
"""
def display(request):
    P = Person.objects.all()
    t = loader.get_template('display1.html')
    Hello ="hello"
    c = RequestContext(request, {'P':P})
    return HttpResponse(t.render(c))
"""

def display(request):
    R = RAPID_SLUM_APPRAISAL.objects.all()
    t = loader.get_template('display4.html')
    c = RequestContext(request, {'R':R})
    return HttpResponse(t.render(c))



def insert(request):
    print request
    if request.method == 'POST':
        print "Hello"
        R = RAPID_SLUM_APPRAISAL(
            Approximate_Population= request.POST['Approximate_Population'],
            Toilet_Cost=request.POST['Toilet_Cost'],            
            Toilet_seat_to_persons_ratio=request.POST['Toilet_seat_to_persons_ratio'],
            Percentage_with_an_Individual_Water_Connection=request.POST['Percentage_with_an_Individual_Water_Connection'],
            Frequency_of_clearance_of_waste_containers=request.POST['Frequency_of_clearance_of_waste_containers'],
            image1=request.POST['Image1'],
            image2=request.POST['Image2'],
            image3=request.POST['Image3'],
            image4=request.POST['Image4']            
        )
        R.save()
    t = loader.get_template('insert.html')
    c = RequestContext(request)
    return HttpResponseRedirect(t.render(c))


def edit(request,RAPID_SLUM_APPRAISAL_id):
    R = RAPID_SLUM_APPRAISAL.objects.get(pk=RAPID_SLUM_APPRAISAL_id)
    if request.method == 'POST':
        Approximate_Population= request.POST['Approximate_Population']
        Toilet_Cost=request.POST['Toilet_Cost']           
        Toilet_seat_to_persons_ratio=request.POST['Toilet_seat_to_persons_ratio']
        Percentage_with_an_Individual_Water_Connection=request.POST['Percentage_with_an_Individual_Water_Connection']
        Frequency_of_clearance_of_waste_containers=request.POST['Frequency_of_clearance_of_waste_containers']
        image1=request.POST['Image1']
        image2=request.POST['Image2']
        image3=request.POST['Image3']
        image4=request.POST['Image4']            
        R.save()
    t = loader.get_template('insert.html')
    c = RequestContext(request, {
        'RAPID_SLUM_APPRAISAL': R
    })
    return HttpResponseRedirect(t.render(c))