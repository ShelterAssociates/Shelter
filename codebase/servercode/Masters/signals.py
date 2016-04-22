from Masters.models import *
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




@receiver(post_save,sender=Slum)
def Slum_Created_Trigger(sender,instance,**kwargs):
	print "Hello"
	conn = psycopg2.connect(database=settings.KOBOCAT_DATABASES['DBNAME'], 
							user=settings.KOBOCAT_DATABASES['USER'], 
							password=settings.KOBOCAT_DATABASES['PASSWORD'], 
							host=settings.KOBOCAT_DATABASES['HOST'], 
							port=settings.KOBOCAT_DATABASES['PORT'] )
	
	objSurveys=Survey.objects.filter(City_id=instance.ElectoralWard_id.AdministrativeWard_id.City_id)
	print "Query"
	for objSurvey in objSurveys:
		arrlist = objSurvey.kobotoolSurvey_url.split('/')
		koboformId = arrlist[len(arrlist)-1].split('?')[0]
		cursor = conn.cursor()
		cursor.execute('select json from logger_xform where id='+koboformId)
		jsonCursor = cursor.fetchall()
		koboJson = None
		for jsonValue in jsonCursor[0]: 
			koboJson=json.loads(jsonValue)
			koboJson["children"][0]["children"].append({'name':instance.Name,'label':instance.Name})   
			koboformJson = json.dumps(koboJson)

		cursor = conn.cursor()
		cursor.execute('select xml from logger_xform where id='+koboformId)
		xmlCursor = cursor.fetchall()
		koboXml = []
		for xmlValue in xmlCursor[0]:           
			koboXml=xmlValue
		soup = Soup(koboXml,"html.parser")    
		soup.select1.append(Soup('<item>\n<label>'+instance.Name+'</label>\n<value>'+instance.Name+'</value>\n</item>\n','html.parser'))
		koboformXml= unicode(soup)
		#koboformXml= unicode(soup.prettify())
		cursor.execute('BEGIN')
		cursor.execute('update logger_xform set json=%s, xml=%s where id='+koboformId,[(koboformJson,),(koboformXml,)])
		cursor.execute('COMMIT')
		print "Done"


        

