#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Forms Page for master app"""

import urllib2
import json

from django import forms
from django.conf import settings

from master.models import Survey, City  ,Rapid_Slum_Appraisal
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.forms import widgets
from django.core.exceptions import ValidationError


SURVEY_LIST = []


class SurveyCreateForm(forms.ModelForm):
    """Create a new survey"""

    kobotool_survey_id = forms.ChoiceField(widget=forms.Select(),
                                           required=True)
    kobotool_survey_url = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        """Initialization"""
        try:
            self.survey = kwargs.pop('survey')
        except KeyError:
            print 'No survey Id'
        super(SurveyCreateForm, self).__init__(*args, **kwargs)
        self.list_i = []
        self.list_i = get_kobo_id_list()
        self.fields['kobotool_survey_id'].choices = self.list_i
        self.fields['kobotool_survey_id'].initial = [0]
        self.fields['kobotool_survey_url'].required = False

        # self.fields['kobotoolSurvey_url'].widget.attrs['readonly'] = True

    class Meta:
        """Metadata for class SurveyCreateForm"""
        model = Survey
        fields = [
            'name',
            'description',
            'city',
            'survey_type',
            'analysis_threshold',
            'kobotool_survey_id',
            ]

    def save(self, *args, **kwargs):
        """Method to create a new Mapping Survey Form"""
        instance = super(SurveyCreateForm, self).save(commit=False)
        try:
            instance.id = self.survey
        except IOError:
            print 'Error for Survey_id'

        kobourl = ''
        data = self.cleaned_data

        for survey_value in SURVEY_LIST:
            if survey_value[0] == data['kobotool_survey_id']:
                kobourl = survey_value[1]

        instance.kobotool_survey_url = kobourl
        instance.save()
        return instance


def get_kobo_id_list():

    # url="http://kc.shelter-associates.org/api/v1/forms?format=json"
    """Method which fetches the KoboCat ID's and URL's from the Kobo Toolbox API"""

    url = settings.KOBOCAT_FORM_URL
    req = urllib2.Request(url)
    req.add_header('Authorization', settings.KOBOCAT_TOKEN)
    resp = urllib2.urlopen(req)
    content = resp.read()
    data = json.loads(content)

    temp_arr = []
    temp_arr.append(('', '-----------'))
    for value in data:
        SURVEY_LIST.append((value['id_string'], value['url']))
        temp_arr.append((value['id_string'], value['id_string']))

    return temp_arr


class LocationWidget(widgets.TextInput):
    """Map Widget"""
    template_name = 'draw.html'
    def render(self, name, value, attrs=None):
        context = {'POLYGON':value}
        return mark_safe(render_to_string(self.template_name, context))


class CityFrom(forms.ModelForm):
    """City Form"""
    shape = forms.CharField(widget=LocationWidget())
    class Meta:
        model = City
        fields = ('name', 'shape', 'state_code', 'district_code', 'city_code')
        exclude = ('created_by', 'created_on')



class Rapid_Slum_AppraisalForm(forms.ModelForm):
    general_info_left_image = forms.ImageField()
    toilet_info_left_image = forms.ImageField()
    waste_management_info_left_image = forms.ImageField()
    water_info_left_image = forms.ImageField()
    roads_and_access_info_left_image = forms.ImageField()
    drainage_info_left_image = forms.ImageField() 
    gutter_info_left_image = forms.ImageField()

    class Meta:
        model = Rapid_Slum_Appraisal
        fields = '__all__'
 
"""
    def clean_general_info_left_image(self):
        image = self.cleaned_data.get('general_info_left_image')
        print image
        if image:
            if image._size > 3*1024*1024:
                raise ValidationError("Image file too large ( > 3mb )")
            return image
        else:
            raise ValidationError("Couldn't read uploaded image")    
    
    def clean_toilet_info_left_image(self):
        image = self.cleaned_data.get('toilet_info_left_image')
        if image:
            if image._size > 3*1024*1024:
                raise ValidationError("Image file too large ( > 3mb )")
            return image
        else:
            raise ValidationError("Couldn't read uploaded image")    

    def clean_waste_management_info_left_image(self):
        image = self.cleaned_data.get('waste_management_info_left_image')
        if image:
            if image._size > 3*1024*1024:
                raise ValidationError("Image file too large ( > 3mb )")
            return image
        else:
            raise ValidationError("Couldn't read uploaded image")    

    def clean_water_info_left_image(self):
        image = self.cleaned_data.get('water_info_left_image')
        if image:
            if image._size > 3*1024*1024:
                raise ValidationError("Image file too large ( > 3mb )")
            return image
        else:
            raise ValidationError("Couldn't read uploaded image")    

    def clean_roads_and_access_info_left_image(self):
        image = self.cleaned_data.get('roads_and_access_info_left_image')
        if image:
            if image._size > 3*1024*1024:
                raise ValidationError("Image file too large ( > 3mb )")
            return image
        else:
            raise ValidationError("Couldn't read uploaded image")    

    def clean_drainage_info_left_image(self):
        image = self.cleaned_data.get('drainage_info_left_image')
        if image:
            if image._size > 3*1024*1024:
                raise ValidationError("Image file too large ( > 3mb )")
            return image
        else:
            raise ValidationError("Couldn't read uploaded image")    

    def clean_gutter_information_left_image(self):
        image = self.cleaned_data.get('gutter_information_left_image')
        if image:
            if image._size > 3*1024*1024:
                raise ValidationError("Image file too large ( > 3mb )")
            return image
        else:
            raise ValidationError("Couldn't read uploaded image")    
"""

