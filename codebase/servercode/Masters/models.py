from django.db import models
import datetime
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.forms import ModelForm
from django.db.models.signals import pre_save, pre_delete, post_save, post_delete
from django.dispatch import receiver
import django.contrib.gis.db.backends.postgis 
import psycopg2
import json
from bs4 import BeautifulSoup as Soup
from django.conf import settings

class City(models.Model):
	Name = models.CharField(max_length=20)
	Shape = models.CharField(max_length=2000)
	State_code = models.CharField(max_length=5)
	District_Code = models.CharField(max_length=5)
	City_code = models.CharField(max_length=5)
	createdBy =  models.ForeignKey(User)
	createdOn = models.DateTimeField( default= datetime.datetime.now())
	def __unicode__(self):
		return self.Name 



SURVEYTYPE_CHOICES = (('Slum Level', 'Slum Level'),
					  ('Household Level', 'Household Level'),
					  ('Household Member Level', 'Household Member Level'))


class Survey(models.Model):
	Name = models.CharField(max_length=50)
	Description = models.CharField(max_length=200)
	City_id = models.ForeignKey(City)
	Survey_type = models.CharField(max_length=50, choices=SURVEYTYPE_CHOICES)
	AnalysisThreshold = models.IntegerField()
	kobotoolSurvey_id = models.CharField(max_length=50)
	kobotoolSurvey_url = models.CharField(max_length=512)
	
	def __unicode__(self):
		return self.Name
	


class Administrative_Ward(models.Model):
	Name = models.CharField(max_length=512)
	Shape = models.CharField(max_length=2048)
	Ward_no =models.CharField(max_length=10)
	Description = models.CharField(max_length=2048)
	OfficeAddress = models.CharField(max_length=2048)
	City_id	= models.ForeignKey(City)
	def __unicode__(self):
		return self.Name    

class Electrol_Ward(models.Model):
	Name = models.CharField(max_length=512)
	Shape = models.CharField(max_length=2048)
	WardNo = models.CharField(max_length=10)
	Electrolward_code = models.CharField(max_length=10)
	Electoralward_Desc = models.CharField(max_length=4096)
	AdministrativeWard_id = models.ForeignKey(Administrative_Ward)
	def __unicode__(self):
		return self.Name


class Slum(models.Model):
     Name = models.CharField(max_length=100)
     Shape = models.CharField(max_length=2048)
     Description = models.CharField(max_length=100)
     ElectrolWard_id = models.ForeignKey(Electrol_Ward)
     Shelter_slum_code = models.CharField(max_length=512)
     def __unicode__(self):
		return str(self.Name)   

class WardOffice_Contacts(models.Model):
	Name  = models.CharField(max_length=200)
	Title = models.CharField(max_length=25)
	Telephone = models.CharField(max_length=50)
	Administrativeward_id = models.ForeignKey(Administrative_Ward)
	def __unicode__(self):
		return self.Name  

class Elected_Representative(models.Model):
	Name = models.CharField(max_length=200) 
	Telnos = models.CharField(max_length=50)
	Address = models.CharField(max_length=512)
	Postcode = models.CharField(max_length=20)
	AdditionalInfo = models.CharField(max_length=2048)
	ElectedRep_Party = models.CharField(max_length=50)
	Eletrolward_id = models.ForeignKey(Electrol_Ward)
	def __unicode__(self):
		return self.Name

class ShaperCode(models.Model):
	Code = models.CharField(max_length=25)
	Description = models.CharField(max_length=100)

class Drawable_Component(models.Model):
	Name  = models.CharField(max_length=100)
	Color = models.CharField(max_length=100)
	Extra = models.CharField(max_length=4096)
	Maker_icon = models.CharField(max_length=500)
	Shapecode_id = models.ForeignKey(ShaperCode)
	def __unicode__(self):
		return self.Name


class PlottedShape(models.Model):
	Slum = models.CharField(max_length=100)
	Name = models.CharField(max_length=512)
	Lat_long = models.CharField(max_length=2000)
	Drawable_Component_id = models.ForeignKey(Drawable_Component)
	createdBy =  models.ForeignKey(User)
	createdOn= models.DateTimeField(default= datetime.datetime.now())
	def __unicode__(self):
		return self.Name

class Sponser(models.Model):
	organization = models.CharField(max_length=200)
	address = models.CharField(max_length=2048)
	Phonenumber = models.CharField(max_length=50)
	description = models.CharField(max_length=2048)
	image = models.CharField(max_length=2048)


CHOICES_ALL = (('0', '0'),
					  ('1', '1'),
					  ('2', '2'))

class Filter_Master(models.Model):
	Name = models.CharField(max_length=512)
	IsDeployed = models.CharField(max_length=1)
	VisibleTo = models.IntegerField(choices=CHOICES_ALL)
	createdBy = models.ForeignKey(User)
	createdOn= models.DateTimeField(default= datetime.datetime.now())


CHOICE = (('0', '0'),
					  ('1', '1'))
	

CHOICES_ALL = (('0', '0'),
					  ('1', '1'),
					  ('2', '2'))


class RoleMaster(models.Model):
	RoleName = models.CharField(max_length=100)
	City = models.IntegerField(choices=CHOICES_ALL)
	Slum = models.IntegerField(choices=CHOICES_ALL)
	KML =  models.BooleanField(choices=CHOICE,blank=False)
	DynamicQuery = models.BooleanField(choices=CHOICE,blank=False)
	PredefinedQuery = models.BooleanField(choices=CHOICE,blank=False)
	CanRequest = models.BooleanField(choices=CHOICE,blank=False)
	Users = models.BooleanField(choices=CHOICE,blank=False)
	CreateSaveQuery = models.BooleanField(choices=CHOICE,blank=False)
	DeploySurvey = models.BooleanField(choices=CHOICE,blank=False)
	UploadImages = models.BooleanField(choices=CHOICE,blank=False)
	PrepareReports = models.BooleanField(choices=CHOICE,blank=False)
	


Type_CHOICES = (('0', '0'),
					  ('1', '1'))

class Sponsor_Project(models.Model):
	Name = models.CharField(max_length=512)
	Type =  models.IntegerField(choices=Type_CHOICES)
	Sponsor_id = models.ForeignKey(Sponser)
	createdBy = models.ForeignKey(User)
	createdOn= models.DateTimeField(default= datetime.datetime.now())
	def __unicode__(self):
		return self.Name

class Sponsor_ProjectMetadata(models.Model):
	household_code = models.IntegerField()
	slum_id = models.ForeignKey(Slum)
	Sponsor_Project_id = models.ForeignKey(Sponsor_Project)


class Filter(models.Model):
	query = models.CharField(max_length=4096)
	Filter_Master_id = models.ForeignKey(Filter_Master)


class Sponsor_user(models.Model):
	Sponsor_id = models.ForeignKey(Sponser)
	auth_user_id = models.ForeignKey(User)

class FilterMasterMetadata(models.Model):
	user_id = models.ForeignKey(User)
	user_type = models.ForeignKey(Group)
	filter_id = models.ForeignKey(Filter_Master)


class ProjectMaster(models.Model):
	created_user = models.CharField(max_length=100) 
	created_date = models.DateTimeField(default= datetime.datetime.now())


class UserRoleMaster(models.Model):
	user_id = models.ForeignKey(User)
	role_id = models.ForeignKey(RoleMaster)
	City_id = models.ForeignKey(City)
	slum_id = models.ForeignKey(Slum)

@receiver(post_save,sender=Slum)
def Slum_Created_Trigger(sender,instance,**kwargs):
	#Database connection with Kobocat Postgres
    conn = psycopg2.connect(database=settings.KOBOCAT_DATABASES['DBNAME'], 
							user=settings.KOBOCAT_DATABASES['USER'], 
							password=settings.KOBOCAT_DATABASES['PASSWORD'], 
							host=settings.KOBOCAT_DATABASES['HOST'], 
							port=settings.KOBOCAT_DATABASES['PORT'] )
   

    objSurveys=Survey.objects.filter(City_id=instance.ElectrolWard_id.AdministrativeWard_id.City_id)
    for objSurvey in objSurveys:
    	#Split Kobocat URL to get Form_ID
    	arrlist = objSurvey.kobotoolSurvey_url.split('/')
    	koboformId = arrlist[len(arrlist)-1].split('?')[0]
    	
    	#Get JSON data from Kobocat
    	cursor = conn.cursor()
        cursor.execute('select json from logger_xform where id='+koboformId)
        jsonCursor = cursor.fetchall()
        koboJson = None
        for jsonValue in jsonCursor[0]: 
            koboJson=json.loads(jsonValue)
        koboJson["children"][0]["children"].append({'name':instance.Name,'label':instance.Name})   
        koboformJson = json.dumps(koboJson)
        
        #Get XML data from Kobocat
        cursor = conn.cursor()
        cursor.execute('select xml from logger_xform where id='+koboformId)
        xmlCursor = cursor.fetchall()
        koboXml = []
        for xmlValue in xmlCursor[0]:           
            koboXml=xmlValue
            
        soup = Soup(koboXml,"html.parser")    
        
        #Append New City In XML
        soup.select1.append(Soup('<item>\n<label>'+instance.Name+'</label>\n<value>'+instance.Name+'</value>\n</item>\n','html.parser'))
        koboformXml= unicode(soup.prettify())
        
        #Update Kobocat database JSON and XML fields 
        cursor.execute('BEGIN')
        cursor.execute('update logger_xform set json=%s, xml=%s where id='+koboformId,[(koboformJson,),(koboformXml,)])
        cursor.execute('COMMIT')


