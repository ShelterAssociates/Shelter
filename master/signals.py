#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Signals Page for masters app"""

import json
import psycopg2

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from master.models import Survey, Slum, Rapid_Slum_Appraisal
from bs4 import BeautifulSoup as Soup


@receiver(post_save, sender=Slum)
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



@receiver(post_save,sender=Rapid_Slum_Appraisal)
def Rapid_Slum_Appraisa_created_trigger(sender,instance, **kwargs):
    print "I am in Rapid_Slum_Appraisal"
    this = Rapid_Slum_Appraisal.objects.get(id=instance.id)
    try:
        if this.gutter_info_left_image.name != instance.gutter_info_left_image.name:
            print "I am in try"
            this.gutter_info_left_image.delete(save=False)                
    except:
        print "I am in except"
        pass # when new photo then we do nothing, normal case          
 





"""
    try:
        if this.water_info_left_image.name != instance.water_info_left_image.name:
            print "I am in try"
            this.water_info_left_image.delete(save=False)                
    except:
        print "I am in except"
        pass # when new photo then we do nothing, normal case          
    try:
        if this.waste_management_info_left_image.name != instance.waste_management_info_left_image.name:
            print "I am in try"
            this.waste_management_info_left_image.delete(save=False)                
    except:
        print "I am in except"
        pass # when new photo then we do nothing, normal case          
    try:
        if this.toilet_info_left_image.name != instance.toilet_info_left_image.name:
            print "I am in try"
            this.toilet_info_left_image.delete(save=False)                
    except:
        print "I am in except"
        pass # when new photo then we do nothing, normal case          
    try:
        if this.general_info_left_image.name != instance.general_info_left_image.name:
            print "I am in try"
            this.general_info_left_image.delete(save=False)                
    except:
        print "I am in except"
        pass # when new photo then we do nothing, normal case          
    try:
        if this.roads_and_access_info_left_image.name != instance.roads_and_access_info_left_image.name:
            print "I am in try"
            this.roads_and_access_info_left_image.delete(save=False)                
    except:
        print "I am in except"
        pass # when new photo then we do nothing, normal case          
    try:
        if this.drainage_info_left_image.name != instance.drainage_info_left_image.name:
            print "I am in try"
            this.drainage_info_left_image.delete(save=False)               
    except:
        print "I am in except"
        pass # when new photo then we do nothing, normal case          
            
 """ 