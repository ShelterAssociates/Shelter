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
from BeautifulSoup import BeautifulStoneSoup as Soup

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

class Survey(models.Model):
	Name = models.CharField(max_length=50)
	Description = models.CharField(max_length=200)
	City_id = models.ForeignKey(City)
	Survey_type = models.CharField(max_length=50)
	AnalysisThreshold = models.IntegerField()
	kobotoolSurvey_id = models.CharField(max_length=50)
	kobotoolSurvey_url = models.CharField(max_length=50)
	def __unicode__(self):
		return self.Name


class Administrative_Ward(models.Model):
	Name = models.CharField(max_length=50)
	Shape = models.CharField(max_length=2048)
	Ward_no =models.CharField(max_length=10)
	Description = models.CharField(max_length=512)
	OfficeAddress = models.CharField(max_length=512)
	City_id	= models.ForeignKey(City)
	def __unicode__(self):
		return self.Name    

class Electrol_Ward(models.Model):
	Name = models.CharField(max_length=50)
	Shape = models.CharField(max_length=2048)
	WardNo = models.CharField(max_length=200)
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
	Name  = models.CharField(max_length=50)
	Title = models.CharField(max_length=10)
	Telephone = models.CharField(max_length=20)
	Administrativeward_id = models.ForeignKey(Administrative_Ward)
	def __unicode__(self):
		return self.Name  

class Elected_Representative(models.Model):
	Name = models.CharField(max_length=50) 
	Telnos = models.CharField(max_length=20)
	Address = models.CharField(max_length=100)
	Postcode = models.CharField(max_length=20)
	AdditionalInfo = models.CharField(max_length=200)
	ElectedRep_Party = models.CharField(max_length=50)
	Eletrolward_id = models.ForeignKey(Electrol_Ward)
	def __unicode__(self):
		return self.Name

class ShaperCode(models.Model):
	Code = models.CharField(max_length=100)
	Description = models.CharField(max_length=100)

class Drawable_Component(models.Model):
	Name  = models.CharField(max_length=100)
	Color = models.CharField(max_length=100)
	Extra = models.CharField(max_length=100)
	Maker_icon = models.CharField(max_length=100)
	Shapecode_id = models.ForeignKey(ShaperCode)
	def __unicode__(self):
		return self.Name


class PlottedShape(models.Model):
	Slum = models.CharField(max_length=100)
	Name = models.CharField(max_length=100)
	Lat_long = models.CharField(max_length=2000)
	Drawable_Component_id = models.ForeignKey(Drawable_Component)
	creaatedBy =  models.ForeignKey(User)
	createdOn= models.DateTimeField(default= datetime.datetime.now())
	def __unicode__(self):
		return self.Name

class Sponser(models.Model):
	organization = models.CharField(max_length=100)
	address = models.CharField(max_length=50)
	Phonenumber = models.CharField(max_length=20)
	description = models.CharField(max_length=256)
	image = models.CharField(max_length=2048)


class Filter_Master(models.Model):
	name = models.CharField(max_length=30)
	IsDeployed = models.CharField(max_length=1)
	VisibleTo = models.IntegerField()
	createdBy = models.ForeignKey(User)
	createdOn= models.DateTimeField(default= datetime.datetime.now())
	

class RoleMaster(models.Model):
	RoleName = models.CharField(max_length=100)
	City = models.IntegerField()
	Slum = models.IntegerField()
	KML = models.CharField(max_length=1)
	DynamicQuery = models.CharField(max_length=1)
	PredefinedQuery = models.CharField(max_length=1)
	CanRequest = models.CharField(max_length=1)
	Users = models.CharField(max_length=1)
	CreateSaveQuery = models.CharField(max_length=1)
	DeploySurvey = models.CharField(max_length=1)
	UploadImages = models.CharField(max_length=1)
	PrepareReports = models.CharField(max_length=1)
	
 

class Sponsor_Project(models.Model):
	Name = models.CharField(max_length=50)
	Type = models.CharField(max_length=30)
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
    conn = psycopg2.connect(database='onadata', user='postgres', password='softcorner', host='localhost', port='5432')#, sslmode='require')
    print instance
    print instance.Name
    print instance.ElectrolWard_id.AdministrativeWard_id.City_id
    objSurveys=Survey.objects.filter(City_id=instance.ElectrolWard_id.AdministrativeWard_id.City_id)
    
    for objSurvey in objSurveys:
        arrlist = objSurvey.kobotoolSurvey_url.split('/')
	id = arrlist[len(arrlist)-1].split('?')[0]
        cursor = conn.cursor()
        cursor.execute('select json from logger_xform where id='+id)
        a = cursor.fetchall()
        k = None
        for v in a[0]: 
            k=json.loads(v)
        k["children"][0]["children"].append({'name':instance.Name,'label':instance.Name})   
        aa = json.dumps(k)
        cursor = conn.cursor()
        cursor.execute('select xml from logger_xform where id='+id)
        b = cursor.fetchall()
        x = []
        for v in b[0]:
            print type(v) 
            x=v
        soup = Soup(x)
        soup.select1.append(Soup('<item>\n<label>'+instance.Name+'</label>\n<value>'+instance.Name+'</value>\n</item>\n'))
    
        xx= unicode(soup)
        cursor.execute('BEGIN')
        cursor.execute('update logger_xform set json=%s, xml=%s where id='+id,[(aa,),(xx,)])
        cursor.execute('COMMIT')



