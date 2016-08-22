# -*- coding: utf-8 -*-

from pymongo import MongoClient
import psycopg2
import re
from __builtin__ import str
import json
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
jsonid_arr=[]

xform_id_old="132"
xform_id="7"
xform_survey_id="14"
xform_id_string="ajH7Pcg2vjtmKmpY8JfW4D"
formhub_uid="0cdb11367db646b2bec0f92117c5061a"
formhub_old_uid="1c0b0cef39054d85bdf2b17bb17e4043"
version_id="47"
xml_form_string='<uploaded_form_usq3zf id="Sanjay_Gandhi_Nagar_RHS_Navi_M">'
xml_form_id='uploaded_form_usq3zf'
xform_name='Sanjay_Gandhi_Nagar_RHS_Navi_M'


def postgresmigration():
	
	conn1 = psycopg2.connect(database='dockerlive1',
                            user='postgres',
                            password='',
                            host='172.17.0.4',
			    port='5432')
	
	conn = psycopg2.connect(database='kobotoolbox',
                            user='kobo',
                            password='',
                            host='172.17.0.4',
                            port='5432')

		
	#/******************** Code For Postgres******************************************/
	jsonid_arr=[]
	jsonid=""
	xmldata=""
	jsondata={}
		
	try:
	    cursor = conn1.cursor()	
	    query="select  id,json,xml from logger_instance_copy where xform_id="+xform_id_old+";"	
	    cursor.execute(query)
	except  e:
	    print e
	jsonCursor = cursor.fetchall()
	for json1 in  jsonCursor:
	    for json2 in json1: 			
	       
		if type(json2)==int:				
		    jsonid=json2
		   
		elif type(json2)==dict :
	       	    jsondata={}							
		    for key,data in json2.items():
		        if key =="_xform_id_string":
			    data=xform_id_string 	  					
			if key == "formhub/uuid" :
			    data=formhub_uid 	  				
			if data:			   
			    data=str(data).replace("\u20b9","")
			    data=data.replace("'","")
			
			jsondata[key]=data
		    		
		elif type(json2)==str :
		   
		    val='<'+xform_id_string+'  id="'+xform_id_string+'" version="'+version_id+'"><__version__>'+version_id+'</__version__>'	
		    xmldata=json2.replace('<?xml version=\'1.0\' ?>', '<?xml version="1.0" ?>')\
                                     .replace(str(xml_form_string),str(val) )\
				     .replace(formhub_old_uid,formhub_uid)\
				     .replace('/'+xml_form_id,'/'+xform_id_string+'')\
				     .replace("'","")
	   
	    updatequery="Update logger_instance_copy set json='"+json.dumps(jsondata)+"', xml='"+xmldata+"',xform_id='"+xform_id+"',survey_type_id='"+xform_survey_id+"'  where id="+str(jsonid)+";"		
		
	   
	    try:
	        cursor.execute(updatequery)
		conn1.commit()
		print "Success"
	    except Exception as inste:
		print ("Query Error ", inste)

 
def mongodbmigration():	
	try:    
	    client = MongoClient('mongodb://172.17.0.5:27017/')
	    livemydb = client['formhub']
	except Exception as e:
	    print ("live 123",e)
		
	mogocursor=dict()
	
	try:
            client = MongoClient('mongodb://172.17.0.5:27017/')
            mydb = client['dockerlive']
	    mogocursor=mydb.mycollection.find({"_xform_id_string" : str(xform_name) }).sort("_id",1);
        except Exception as ex:
            print ("docker 123",ex)	

	count=0
	for json1 in  mogocursor:		
            json1['_xform_id_string']=xform_id_string
	    json1['formhub/uuid']=formhub_uid
	    json1['_userform_id']='shelter_'+xform_id_string
	   
	    count = count + 1
	    
	    try:
		livemydb.instances.insert(json1)
	
	    except Exception as ex:
		print ex


if __name__ == "__main__":
    postgresmigration()
    #mongodbmigration()
	
	



