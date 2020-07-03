#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Signals Page for masters app"""

import json
import psycopg2

from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver
from django.conf import settings

from master.models import Survey, Slum, Rapid_Slum_Appraisal
from bs4 import BeautifulSoup as Soup


#@receiver(post_save, sender=Slum)
def slum_created_trigger(sender, instance, **kwargs):
    """Triggers the below code when a slum is created"""
    conn = psycopg2.connect(database=settings.KOBOCAT_DATABASES['DBNAME'],
                            user=settings.KOBOCAT_DATABASES['USER'],
                            password=settings.KOBOCAT_DATABASES['PASSWORD'],
                            host=settings.KOBOCAT_DATABASES['HOST'],
                            port=settings.KOBOCAT_DATABASES['PORT'])

    obj_surveys = \
        Survey.objects.filter(city=instance.electoral_ward.administrative_ward.city)
    for obj_survey in obj_surveys:
        arrlist = obj_survey.kobotool_survey_url.split('/')
        koboform_id = arrlist[len(arrlist) - 1].split('?')[0]
        cursor = conn.cursor()
        cursor.execute('select json from logger_xform where id='
                       + koboform_id)
        json_cursor = cursor.fetchall()
        kobo_json = None

        for json_value in json_cursor[0]:
            kobo_json = json.loads(json_value)
            kobo_json['children'][0]['children'
                                    ].append({'name': instance.name,
                                              'label': instance.name})
            koboform_json = json.dumps(kobo_json)

        cursor = conn.cursor()
        cursor.execute('select xml from logger_xform where id='
                       + koboform_id)
        xml_cursor = cursor.fetchall()
        kobo_xml = []
        for xml_value in xml_cursor[0]:
            kobo_xml = xml_value
        soup = Soup(kobo_xml, 'html.parser')
        soup.select1.append(Soup('<item>\n<label>' + instance.name
                                 + '</label>\n<value>' + instance.name
                                 + '''</value>
</item>
''', 'html.parser'))
        koboform_xml = unicode(soup)

        # koboformXml= unicode(soup.prettify())

        cursor.execute('BEGIN')
        cursor.execute('update logger_xform set json=%s, xml=%s where id='
                       + koboform_id, [(koboform_json, ), (koboform_xml,
                                                          )])
        cursor.execute('COMMIT')



@receiver(pre_save,sender=Rapid_Slum_Appraisal)
def Rapid_Slum_Appraisal_created_trigger(sender,instance, **kwargs):
    """Triggers the below code when image is updated"""
    try:
        this = Rapid_Slum_Appraisal.objects.get(id=instance.id)
        #print "Hi"
        try:
            if this.gutter_info_left_image.name != instance.gutter_info_left_image.name:
                this.gutter_info_left_image.delete(save=False)                
        except:
            pass 
        try:
            if this.water_info_left_image.name != instance.water_info_left_image.name:
                this.water_info_left_image.delete(save=False)                
        except:
            pass           
        try:
            if this.waste_management_info_left_image.name != instance.waste_management_info_left_image.name:
                this.waste_management_info_left_image.delete(save=False)                
        except:
            pass          
        try:
            if this.toilet_info_left_image.name != instance.toilet_info_left_image.name:
                this.toilet_info_left_image.delete(save=False)                
        except:
            pass 
        try:
            if this.general_info_left_image.name != instance.general_info_left_image.name:
                this.general_info_left_image.delete(save=False)                
        except:
            pass        
        try:
            if this.roads_and_access_info_left_image.name != instance.roads_and_access_info_left_image.name:
                this.roads_and_access_info_left_image.delete(save=False)                
        except:
            pass          
        try:
            if this.drainage_info_left_image.name != instance.drainage_info_left_image.name:
                this.drainage_info_left_image.delete(save=False)               
        except:
            pass
        try:
            if this.general_image_bottomdown1.name != instance.general_image_bottomdown1.name:
                this.general_image_bottomdown1.delete(save=False)               
        except:
            pass
        try:
            if this.general_image_bottomdown2.name != instance.general_image_bottomdown2.name:
                this.general_image_bottomdown2.delete(save=False)               
        except:
            pass
        try:
            if this.toilet_image_bottomdown1.name != instance.toilet_image_bottomdown1.name:
                this.toilet_image_bottomdown1.delete(save=False)               
        except:
            pass
        try:
            if this.toilet_image_bottomdown2.name != instance.toilet_image_bottomdown2.name:
                this.toilet_image_bottomdown2.delete(save=False)               
        except:
            pass
        try:
            if this.waste_management_image_bottomdown1.name != instance.waste_management_image_bottomdown1.name:
                this.waste_management_image_bottomdown1.delete(save=False)               
        except:
            pass
        try:
            if this.waste_management_image_bottomdown2.name != instance.waste_management_image_bottomdown2.name:
                this.waste_management_image_bottomdown2.delete(save=False)               
        except:
            pass
        try:
            if this.water_image_bottomdown1.name != instance.water_image_bottomdown1.name:
                this.water_image_bottomdown1.delete(save=False)               
        except:
            pass
        try:
            if this.water_image_bottomdown2.name != instance.water_image_bottomdown2.name:
                this.water_image_bottomdown2.delete(save=False)               
        except:
            pass
        try:
            if this.roads_image_bottomdown1.name != instance.roads_image_bottomdown1.name:
                this.roads_image_bottomdown1.delete(save=False)               
        except:
            pass
        try:
            if this.roads_image_bottomdown2.name != instance.roads_image_bottomdown2.name:
                this.roads_image_bottomdown2.delete(save=False)               
        except:
            pass
        try:
            if this.drainage_image_bottomdown1.name != instance.drainage_image_bottomdown1.name:
                this.drainage_image_bottomdown1.delete(save=False)               
        except:
            pass
        try:
            if this.drainage_image_bottomdown2.name != instance.drainage_image_bottomdown2.name:
                this.drainage_image_bottomdown2.delete(save=False)               
        except:
            pass
        try:
            if this.gutter_image_bottomdown1.name != instance.gutter_image_bottomdown1.name:
                this.gutter_image_bottomdown1.delete(save=False)               
        except:
            pass
        try:
            if this.gutter_image_bottomdown2.name != instance.gutter_image_bottomdown2.name:
                this.gutter_image_bottomdown2.delete(save=False)               
        except:
            pass                                                                  
    except:
        pass           
 
@receiver(pre_delete,sender=Rapid_Slum_Appraisal)
def Rapid_Slum_Appraisa_delete_trigger(sender,instance, **kwargs):
    this = Rapid_Slum_Appraisal.objects.get(id=instance.id)
    this.general_image_bottomdown1.delete()
    this.general_image_bottomdown2.delete()
    this.toilet_image_bottomdown1.delete()
    this.toilet_image_bottomdown2.delete()
    this.waste_management_image_bottomdown1.delete()
    this.waste_management_image_bottomdown2.delete()
    this.water_image_bottomdown1.delete()
    this.water_image_bottomdown2.delete()
    this.roads_image_bottomdown1.delete()
    this.road_image_bottomdown2.delete()
    this.drainage_image_bottomdown1.delete()
    this.drainage_image_bottomdown2.delete()
    this.gutter_image_bottomdown1.delete()
    this.gutter_image_bottomdown2.delete()
    this.drainage_info_left_image.delete()               
    this.roads_and_access_info_left_image.delete()
    this.general_info_left_image.delete()
    this.toilet_info_left_image.delete()
    this.waste_management_info_left_image.delete()
    this.water_info_left_image.delete() 
    this.gutter_info_left_image.delete()
    
