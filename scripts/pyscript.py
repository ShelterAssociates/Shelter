# -*- coding: utf-8 -*-
#1. created logger_instance_copy table in old kobotoolbox database.
#2. Enter one dummy entry for each form and deploy it,then it will create survey_type and version.
#3. Check the ids of old kobotoolbox database and new Docker database it should not be same.
#4. Make change in "postgresmigration()" function of pyscript.py according to old kobotoolbox database and new Docker database. Run the script
#5. Data of old database logger_instance_copy are change according to new database format.
#6. Go to postgres container then switch to postgres paste the query with changes i.e commented in pyscript.py
#7. Now old postgres data is transfer to new database.
#8. Run the script pyscript.py with "mongodbmigration()" function.
#9. After completing the script check last id of postgres database and reset database schema id with next id.


from pymongo import MongoClient
import psycopg2
import re
from __builtin__ import str
import json
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
jsonid_arr=[]

#------------------------
#old kobotoolbox form id
xform_id_old="172"
# docker form id
xform_id="5"
# docker survey id
xform_survey_id="8"
# docker id_string
xform_id_string="aSJM5YWy8LXcmHYL3ZMGgY"
# docker uuid 
formhub_uid="752bb4d151fd4c96ad1b12bfb5f82569"
# old kobotoolbox uuid
formhub_old_uid="20c45355d2084791a50ffe5ac17cd1c3"
# docker form version in kobocat
version_id="43"
# old kobotoolbox xml 
xml_form_string='<uploaded_form_rkdb4w id="Impact_Assessment_V2">' 
# docker xml id
xml_form_id='uploaded_form_rkdb4w'
# docker form title
xform_name='Impact_Assessment_V2'



def postgresmigration():
	
	conn1 = psycopg2.connect(database='dockerlive1',
                            user='postgres',
                            password='softcorner',
                            host='172.17.0.2',
			    port='5432')
			
	#/******************** Code For Postgres ******************************************/
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
	for jsontupal in  jsonCursor:
	    for json2 in jsontupal:
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
		
	    except Exception as inste:
		print ("Query Error ", inste)

 
#***********************************************************************
'''
Go to postgres 

postgres@postgres:/$ 

psql dockerlive1 -c "\copy (SELECT id, json, xml, date_created, date_modified, deleted_at, status, uuid, geom, survey_type_id, user_id, xform_id FROM logger_instance_copy where xform_id= 5) TO STDOUT" | psql kobotoolbox -c "\copy logger_instance (id, json, xml, date_created, date_modified, deleted_at, status, uuid, geom, survey_type_id, user_id, xform_id) FROM STDIN"

'''
#********************************************************************


def mongodbmigration():	
	try:
	    client = MongoClient('mongodb://172.17.0.4:27017/')
	    dockermongodb = client['formhub']
	except Exception as e:
	    print ("Docker Mongo Database Connection error ",e)
		
	mogocursor=dict()
	
	try:
            client = MongoClient('mongodb://172.17.0.4:27017/')
            oldkobomongodb = client['dockerlive1']
	    mogocursor=oldkobomongodb.instances.find({"_xform_id_string" : str(xform_name) }).sort("_id",1);
        except Exception as ex:
            print ("Old Kobotoolbox Mongo Database Connection error",ex)	


	for mongodata in  mogocursor:		
            mongodata['_xform_id_string']=xform_id_string
	    mongodata['formhub/uuid']=formhub_uid
	    mongodata['_userform_id']='shelter_'+xform_id_string	   
	  
	    try:
		dockermongodb.instances.insert(mongodata)		
	    except Exception as ex:
		print ("Docker mongo Query Error ", ex)


if __name__ == "__main__":
    postgresmigration()
    #mongodbmigration()
	
	


