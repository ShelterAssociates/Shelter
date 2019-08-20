#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Views Page for master app"""

import json
import psycopg2
from django.core.urlresolvers import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import ListView
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import FormView
from django.views.generic.base import View
from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis import geos
from django.views.decorators.clickjacking import xframe_options_exempt

from master.models import Survey, CityReference, Rapid_Slum_Appraisal, \
						  Slum, AdministrativeWard, ElectoralWard, City, \
						  WardOfficeContact, ElectedRepresentative, drainage
from master.forms import SurveyCreateForm, ReportForm, Rapid_Slum_AppraisalForm, DrainageForm, LoginForm
from sponsor.models import SponsorProjectDetails
from django.contrib.auth import authenticate, login
from django.contrib.auth import *
from django.contrib.auth.models import User, Group
from component.cipher import *
from utils.utils_permission import access_right
import urllib
from django.http import Http404
from django.core.exceptions import PermissionDenied
from graphs.models import *

@staff_member_required
def index(request):
	"""Renders the index template in browser"""
	template = loader.get_template('index.html')
	context = RequestContext(request, {'site_url':'/'})
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
	success_url = '/admin/surveymapping/'

	def dispatch(self, request, *args, **kwargs):
		"""Signal Dispatcher"""
		try:
			self.survey = 0
			if kwargs['survey']:
				self.survey = kwargs['survey']
		except KeyError:
			print 'Error'
		return super(SurveyCreateView, self).dispatch(request, *args,
													  **kwargs)

	def get_form(self, form_class):
		"""
		Check if the user already saved contact details. If so, then show
		the form populated with those details, to let user change them.
		"""
		try:
		    survey = Survey.objects.get(id=self.survey)
		    return form_class(instance=survey, **self.get_form_kwargs())
		except Survey.DoesNotExist:
		    return form_class(**self.get_form_kwargs())

	def form_valid(self, form):
		"""Actions to perform if form is valid"""
		form.save()
		return super(SurveyCreateView, self).form_valid(form)

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
def rimdisplay(request):
	"""Display Rapid Slum Appraisal Records"""
	if request.method=='POST':
		deleteList=[]
		deleteList=request.POST.getlist('selectcheckbox')
		if deleteList :
			for i in deleteList:
				R = Rapid_Slum_Appraisal.objects.get(pk=i)
				R.delete()

	query = request.GET.get("q")
	R = ""
	RA = ""
	if(query):
		R = Rapid_Slum_Appraisal.objects.filter(slum_name__name__contains=query)
	else:
		R = Rapid_Slum_Appraisal.objects.all()
	paginator = Paginator(R, 10)
	page = request.GET.get('page')
	try:
		RA = paginator.page(page)
	except PageNotAnInteger:
		RA = paginator.page(1)
	except EmptyPage:
		RA = paginator.page(paginator.num_pages)
	return render(request, 'rimdisplay.html',{'R':R,'RA':RA})

@csrf_exempt
def rimedit(request,Rapid_Slum_Appraisal_id):
	"""Update Rapid Slum Appraisal Record"""
	if request.method == 'POST':
		R = Rapid_Slum_Appraisal.objects.get(pk=Rapid_Slum_Appraisal_id)
		form = Rapid_Slum_AppraisalForm(request.POST or None,request.FILES,instance=R)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect('/admin/sluminformation/rim/display')
	elif request.method=="GET":
		R = Rapid_Slum_Appraisal.objects.get(pk=Rapid_Slum_Appraisal_id)
		form = Rapid_Slum_AppraisalForm(instance=R)
	return render(request, 'riminsert.html', {'form': form})

@csrf_exempt
def riminsert(request):
	"""Insert Rapid Slum Appraisal Record"""
	if request.method == 'POST':
		form = Rapid_Slum_AppraisalForm(request.POST,request.FILES)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect('/admin/sluminformation/rim/display')
	else:
		form = Rapid_Slum_AppraisalForm()
	return render(request, 'riminsert.html', {'form': form})

@csrf_exempt
def report(request):
	""" RIM Report Form"""
	form = ReportForm()
	return render(request,'report.html', {'form':form})

@csrf_exempt
def administrativewardList(request):
	"""Administrativeward List Display"""
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
def electoralWardList(request):
	"""Electoral Ward List"""
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
def slumList(request):
	"""Slum Ward List"""
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
def rimreportgenerate(request):
	"""Generate RIM Report"""
	sid = request.POST['Sid']
	SlumObj = Slum.objects.get(id=sid)
	rp_slum_code = str(SlumObj.shelter_slum_code)
	string = settings.BIRT_REPORT_URL + "Birt/frameset?__format=pdf&__report=RIMReport.rptdesign&slum=" + str(rp_slum_code)
	data = {'string': string}
	return HttpResponse(json.dumps(data),content_type='application/json')

@csrf_exempt
def drainagereportgenerate(request):
	"""Generate RIM Report"""
	sid = request.POST['Sid']
	Fid = request.POST['Fid']
	SlumObj = Slum.objects.get(id=sid)
	rp_slum_code = str(SlumObj.shelter_slum_code)
	rp_xform_title = Fid
	string = settings.BIRT_REPORT_URL + "Birt/frameset?__format=pdf&__report=DrainageReport.rptdesign&slum=" + str(rp_slum_code)
	data ={}
	data = {'string': string}
	return HttpResponse(json.dumps(data),content_type='application/json')


@csrf_exempt
def vulnerabilityreport(request):
	"""Generate Vulnerability Report """
	string = settings.BIRT_REPORT_URL + "Birt/frameset?__format=pdf&__report=Vulnerability_Report.rptdesign"
	return HttpResponseRedirect(string)

# @xframe_options_exempt
def slummap(request):
	template = loader.get_template('slummapdisplay.html')
	context = RequestContext(request, {})
	return HttpResponse(template.render(context))

@csrf_exempt
@access_right
def citymapdisplay(request):
	city_dict={}
	city_main={}
	cipher = AESCipher()

	for c in City.objects.all():
		city_dict={}
		city_dict["name"]= c.name.city_name
		city_dict["id"]= "city::"+cipher.encrypt(str(c.id))
		city_dict["lat"]= str(c.shape)
		city_dict["bgColor"]= c.background_color
		city_dict["borderColor"]= c.border_color
		city_dict["content"]={}
		city_main.update({str(c.name.city_name) : city_dict })

	return HttpResponse(json.dumps(city_main),content_type='application/json')

@csrf_exempt
@access_right
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
	score_dict ={}

	admin_main={}
	for a in AdministrativeWard.objects.filter(city__id=id):
		admin_dict={}
		admin_dict["name"]=a.name
		admin_dict["id"]=a.id
		admin_dict["lat"]= json.loads(a.shape.json)
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

		adminwd_score = QolScoreData.objects.filter(slum__electoral_ward__administrative_ward__name = a.name)
		"""Quality of living scores setion and admin ward wise"""
		if adminwd_score:
			scores = []
			section_scores = {}
			slum_general = adminwd_score.values_list('general', flat=True)
			slum_gutter = adminwd_score.values_list('gutter', flat=True)
			slums_drainage = adminwd_score.values_list('drainage', flat=True)
			slum_waste = adminwd_score.values_list('waste', flat=True)
			slum_water = adminwd_score.values_list('water', flat=True)
			slum_toilet = adminwd_score.values_list('toilet', flat=True)
			slum_str_n_occup = adminwd_score.values_list('str_n_occup', flat=True)
			slum_road = adminwd_score.values_list('road', flat=True)
			slum_total_all_sections = adminwd_score.values_list('total_score', flat=True)
			section_scores = {'total_score': sum(slum_total_all_sections) / len(slum_total_all_sections),
							  'toilet': sum(slum_toilet)/len(slum_toilet),
							  'general': sum(slum_general) / len(slum_general),
							  'str_n_occup': sum(slum_str_n_occup) / len(slum_str_n_occup),
							  'road': sum(slum_road) / len(slum_road),
							  'water': sum(slum_water) / len(slum_water),
							  'waste': sum(slum_waste) / len(slum_waste),
							  'drainage': sum(slums_drainage) / len(slums_drainage),
							  'gutter': sum(slum_gutter) / len(slum_gutter)}
			scores.append(section_scores)
			admin_dict['ele_scores'] = section_scores

	for e in ElectoralWard.objects.filter(administrative_ward__city__id=id):
		elctrol_dict={}
		elctrol_dict["name"]=e.name
		elctrol_dict["id"]=e.id
		elctrol_dict["lat"]=json.loads(e.shape.json)
		elctrol_dict["info"]=e.extra_info
		elctrol_dict["bgColor"]=e.background_color
		elctrol_dict["borderColor"]=e.border_color

		electrolwd=ElectedRepresentative.objects.filter(electoral_ward = e.id)
		if electrolwd :
			elctrol_dict["wardOfficerName"]=electrolwd[0].name
			elctrol_dict["wardOfficeAddress"]= electrolwd[0].address +" "+electrolwd[0].post_code
			elctrol_dict["wardOfficeTel"] = electrolwd[0].tel_nos

		electrolwd_scores = QolScoreData.objects.filter(slum__electoral_ward__name = e.name)
		"""Quality of living scores setion and ward wise"""
		if electrolwd_scores:
			scores=[]
			section_scores = {}
			slum_general = electrolwd_scores.values_list('general', flat=True)
			slum_gutter = electrolwd_scores.values_list('gutter', flat=True)
			slums_drainage = electrolwd_scores.values_list('drainage', flat=True)
			slum_waste = electrolwd_scores.values_list('waste', flat=True)
			slum_water = electrolwd_scores.values_list('water', flat=True)
			slum_toilet = electrolwd_scores.values_list('toilet', flat=True)
			slum_str_n_occup = electrolwd_scores.values_list('str_n_occup', flat=True)
			slum_road = electrolwd_scores.values_list('road', flat=True)
			slum_total_all_sections = electrolwd_scores.values_list('total_score',flat=True)
			section_scores ={'total_score': sum(slum_total_all_sections)/len(slum_total_all_sections),
							 'toilet': sum(slum_toilet)/len(slum_toilet),
							 'general':sum(slum_general)/len(slum_general),
							 'str_n_occup':sum(slum_str_n_occup)/len(slum_str_n_occup),
							 'road': sum(slum_road)/len(slum_road),
							 'water': sum(slum_water)/len(slum_water),
							 'waste':sum(slum_waste)/len(slum_waste),
							 'drainage': sum(slums_drainage)/len(slums_drainage),
							 'gutter': sum(slum_gutter)/len(slum_gutter)}
			scores.append(section_scores)
			elctrol_dict['ele_scores']= section_scores
		elctrol_dict["content"]={}
		city_main["content"][str(e.administrative_ward.name)]["content"].update({e.name : elctrol_dict })

	for s in Slum.objects.filter(electoral_ward__administrative_ward__city__id=id, status=True):
		slum_dict={}
		slum_dict["name"]=s.name
		slum_dict["id"]=s.id
		slum_dict["lat"]=json.loads(s.shape.json)
		slum_dict["info"]=s.description
		slum_dict["factsheet"]=s.factsheet.url if s.factsheet else ''
		slum_dict["photo"]=s.photo.url if s.photo else ''
		slum_dict["associated"] = s.associated_with_SA
		city_main["content"]\
		[str(s.electoral_ward.administrative_ward.name)]["content"]\
		[str(s.electoral_ward.name)]["content"].update({s.name : slum_dict })

	for i in QolScoreData.objects.filter(slum__electoral_ward__administrative_ward__city__id=id):
		"""Quality of living scores setion and slum wise"""
		score_dict = {}
		score_dict['total_score'] = i.total_score
		score_dict['road'] = i.road
		score_dict['water'] = i.water
		score_dict['waste'] = i.waste
		score_dict['drainage'] = i.drainage
		score_dict['gutter'] = i.gutter
		score_dict['general'] = i.general
		score_dict['str_n_occup'] = i.str_n_occup
		score_dict['toilet'] = i.toilet
		city_main["content"] \
			[str(i.slum.electoral_ward.administrative_ward.name)]["content"] \
			[str(i.slum.electoral_ward.name)]['content'] \
			[str(i.slum.name)].update({'scores': score_dict})

	return HttpResponse(json.dumps(city_dict),content_type='application/json')

@csrf_exempt
def modelmapdisplay(request):
	""" ftech reference polygon """
	shape = "";
	background_color="";
	modelList=['city','administrativeward','electoralward']
	mid = request.POST['id']
	model=request.POST['model']
	try:
		if model in modelList:
			contenttypeobj=ContentType.objects.get(app_label="master",model=model)
			modelobj=contenttypeobj.get_all_objects_for_this_type(id=mid)
			modelval=modelobj.values()
			shape=str(modelval[0]['shape'])
			background_color=str(modelval[0]['background_color'])
	except:
		shape =""
		background_color=""
	data ={}
	data = {'shape': shape,'background_color':background_color}
	return HttpResponse(json.dumps(data),content_type='application/json')

def drainageinsert(request):
	""" RIM Report Form"""
	if request.method == 'POST':
		form = DrainageForm(request.POST,request.FILES)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect('/admin/sluminformation/drainage/display/')
	else:
		form = DrainageForm()
	return render(request,'drainageinsert.html', {'form':form})

def drainagedisplay(request):
	""" drainage display List Form"""
	if request.method=='POST':
		deleteList=[]
		deleteList=request.POST.getlist('delete')
		for i in deleteList:
			R = drainage.objects.get(pk=i)
			R.delete()
	query = request.GET.get("q")
	R=""
	RA =""
	if(query):
		R = drainage.objects.filter(slum_name__name__contains=query)
	else:
		R = drainage.objects.all()
	paginator = Paginator(R, 10)
	page = request.GET.get('page')
	try:
		RA = paginator.page(page)
	except PageNotAnInteger:
		RA = paginator.page(1)
	except EmptyPage:
		RA = paginator.page(paginator.num_pages)
	return render(request, 'drainagedisplay.html',{'R':R,'RA':RA})

def drainageedit(request,drainage_id):
	if request.method == 'POST':
		d = drainage.objects.get(pk=drainage_id)
		form = DrainageForm(request.POST or None,request.FILES,instance=d)
		if form.is_valid():
			form.save()
			return HttpResponseRedirect('/admin/sluminformation/drainage/display/')
	elif request.method=="GET":
		d = drainage.objects.get(pk=drainage_id)
		form = DrainageForm(instance=d)
	return render(request, 'drainageinsert.html', {'form': form})


def sluminformation(request):
	return render(request,'sluminformation.html')


@csrf_exempt
def cityList(request):
	"""city List Display"""
	Cobj = City.objects.all()
	idArray = []
	nameArray = []
	for i in Cobj:
		nameArray.append(str(i.name))
		idArray.append(i.id)
	data ={}
	data = { 'idArray'  : idArray,
			 'nameArray': nameArray
			}
	return HttpResponse(json.dumps(data),content_type='application/json')

@csrf_exempt
def formList(request):
	""" Form List"""
	old = psycopg2.connect(database='kobotoolbox',user='kobo',password='kobo',host='172.17.0.7',port='5432')
	cursor_old = old.cursor()
	cursor_old.execute("select id, title from logger_xform;")
	fetch_data = cursor_old.fetchall()
	idArray = []
	nameArray = []
	for i in fetch_data:
		nameArray.append(str(i[1]))
		idArray.append(i[0])
	data ={}
	data = { 'idArray'  : idArray,
			 'nameArray': nameArray
		   }
	return HttpResponse(json.dumps(data),content_type='application/json')


@csrf_exempt
def modelList(request):
	"""city adminstravive electrol ward dropdown list"""
	sid = request.POST['id']
	SlumObj = Slum.objects.get(id=sid)
	sname=SlumObj.name
	eid=SlumObj.electoral_ward.id
	ename=str(SlumObj.electoral_ward.name)
	aid=SlumObj.electoral_ward.administrative_ward.id
	aname=str(SlumObj.electoral_ward.administrative_ward.name)
	cid=SlumObj.electoral_ward.administrative_ward.city.id
	cref=CityReference.objects.get(id=SlumObj.electoral_ward.administrative_ward.city.name_id)
	cname=cref.city_name
	data ={}
	data = {
			'sid'  : sid,
			'sname': sname,
			'eid'  : eid,
			'ename': ename,
			'aid' : aid,
			'aname': aname,
			'cid'  : cid,
			'cname': cname
		   }
	return HttpResponse(json.dumps(data),content_type='application/json')

@csrf_exempt
@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('master.can_generate_reports') or u.groups.filter(name='sponsor').exists())
def familyrportgenerate(request):
	"""Generate RIM Report"""
	sid = request.POST['Sid']
	#Fid = request.POST['Fid']
	houseno = request.POST['HouseNo']
	SlumObj = Slum.objects.get(id=sid)
	rp_slum_code = str(SlumObj.shelter_slum_code)

	project_details = False
	if not request.user.is_superuser and not request.user.has_perm('master.can_generate_reports'):
		project_details = SponsorProjectDetails.objects.filter(slum=SlumObj, sponsor__user=request.user, household_code__contains=int(houseno)).exists()
	else:
		project_details = True
	#rp_xform_title = Fid
	data ={}
	if project_details:
		cipher = AESCipher()
		key = cipher.encrypt(str(rp_slum_code) + '|' + str(houseno) + '|' +  str(request.user.id))
		string = settings.BIRT_REPORT_URL + "Birt/frameset?__format=pdf&__report=FFReport.rptdesign&key=" + urllib.quote_plus(key)
		data = {'string': string}
	else:
		data = {'error':'Not authorized'}
	return HttpResponse(json.dumps(data),content_type='application/json')

def city_wise_map(request, key, slumname = None):
	cipher = AESCipher()
	city = cipher.decrypt(key.split('::')[1])
 	city = City.objects.get(pk=int(city))
	template = loader.get_template('city_wise_map.html')
        data={}
	if slumname :
		data['slum_name' ] = slumname
	if city:
		data['city_id'] = city.id
		data['city_name'] = city.name.city_name
	else:
		data['error'] = "URL incorrect"
	context = RequestContext(request, data)
	return HttpResponse(template.render(context))

def login_success(request):
	return_to = ""
	if 'next' in request.GET:
		return_to =  request.GET['next']
	if (request.user.groups.filter(name__in=['sponsor']).exists()):
		return HttpResponseRedirect('/sponsor/')
	else:
		if (request.user.groups.filter(name__in=['ulb']).exists()):
			return HttpResponseRedirect('/city::B5+A2nt050dP4nC55nmuYx9/MPi6RFp2cgBUKxRkedE=')

	if return_to:
		return HttpResponseRedirect(return_to.strip().replace(" ", "+"))
	else:
		return HttpResponseRedirect('/admin/')

def user_login(request):
	"""
	This is temp function used to navigate all the users using old URL.
	:param request: 
	:return: 
	"""
	return HttpResponseRedirect('/accounts/login/')



