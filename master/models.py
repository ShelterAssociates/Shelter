#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Models Page for master app"""

import datetime

from django.contrib.gis.db import models
from django.contrib.auth.models import User

class CityReference(models.Model):
    """Worldwide City Database"""
    city_name = models.CharField(max_length=20)
    city_code = models.CharField(max_length=20)
    district_name = models.CharField(max_length=20)
    district_code = models.CharField(max_length=20)
    state_name = models.CharField(max_length=20)
    state_code = models.CharField(max_length=20)

    def __unicode__(self):
        """Returns string representation of object"""
        return str(self.city_name)

class City(models.Model):
    """Shelter City Database"""
    name = models.ForeignKey(CityReference)
    city_code = models.CharField(max_length=48)
    state_name = models.CharField(max_length=48)
    state_code = models.CharField(max_length=48)
    district_name = models.CharField(max_length=48)
    district_code = models.CharField(max_length=48)
    shape = models.PolygonField(srid=4326)
    created_by = models.ForeignKey(User)
    created_on = models.DateTimeField(default=datetime.datetime.now())

    def __unicode__(self):
        """Returns string representation of object"""
        return str(self.name)

    class Meta:
        """Metadata for class City"""
        verbose_name = 'City'
        verbose_name_plural = 'Cities'

SURVEYTYPE_CHOICES = (('Slum Level', 'Slum Level'), ('Household Level',
                                                     'Household Level'), ('Household Member Level',
                                                                          'Household Member Level'))

class Survey(models.Model):
    """Shelter Survey Database"""
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    city = models.ForeignKey(City)
    survey_type = models.CharField(max_length=50,
                                   choices=SURVEYTYPE_CHOICES)
    analysis_threshold = models.IntegerField()
    kobotool_survey_id = models.CharField(max_length=50)
    kobotool_survey_url = models.CharField(max_length=512)

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Metadata for class Survey"""
        verbose_name = 'Survey'
        verbose_name_plural = 'Surveys'


class AdministrativeWard(models.Model):
    """Administrative Ward Database"""
    city = models.ForeignKey(City)
    name = models.CharField(max_length=512)
    shape = models.CharField(max_length=2048)
    ward_no = models.CharField(max_length=10)
    description = models.CharField(max_length=2048)
    office_address = models.CharField(max_length=2048)

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Metadata for class Administrative Ward"""
        verbose_name = 'Administrative Ward'
        verbose_name_plural = 'Administrative Wards'


class ElectoralWard(models.Model):
    """Electoral Ward Database"""
    administrative_ward = models.ForeignKey(AdministrativeWard)
    name = models.CharField(max_length=512)
    shape = models.CharField(max_length=2048)
    ward_no = models.CharField(max_length=10)
    ward_code = models.CharField(max_length=10)
    extra_info = models.CharField(max_length=4096)

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Metadata for class ElectoralWard"""
        verbose_name = 'Electoral Ward'
        verbose_name_plural = 'Electoral Wards'


class Slum(models.Model):
    """Slum Database"""
    electoral_ward = models.ForeignKey(ElectoralWard)
    name = models.CharField(max_length=100)
    shape = models.CharField(max_length=2048)
    description = models.CharField(max_length=100)
    shelter_slum_code = models.CharField(max_length=512)

    def __unicode__(self):
        """Returns string representation of object"""
        return str(self.name)

    class Meta:
        """Metadata for class Slum"""
        verbose_name = 'Slum'
        verbose_name_plural = 'Slums'


class WardOfficeContact(models.Model):
    """Ward Office Contact Database"""
    administrative_ward = models.ForeignKey(AdministrativeWard)
    title = models.CharField(max_length=25)
    name = models.CharField(max_length=200)
    telephone = models.CharField(max_length=50)

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Metadata for WardOfficeContact"""
        verbose_name = 'Ward Officer Contact'
        verbose_name_plural = 'Ward Officer Contacts'


class ElectedRepresentative(models.Model):
    """Elected Reresentative Database"""
    electoral_ward = models.ForeignKey(ElectoralWard)
    name = models.CharField(max_length=200)
    tel_nos = models.CharField(max_length=50)
    address = models.CharField(max_length=512)
    post_code = models.CharField(max_length=20)
    additional_info = models.CharField(max_length=2048)
    elected_rep_Party = models.CharField(max_length=50)

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Metadata for class ElectedRepresentative"""
        verbose_name = 'Elected Representative'
        verbose_name_plural = 'Elected Representatives'


class ShapeCode(models.Model):
    """Shape Code Database"""
    code = models.CharField(max_length=25)
    description = models.CharField(max_length=100)

    class Meta:
        """Metadata for class ShapeCode"""
        verbose_name = 'Shape Code'
        verbose_name_plural = 'Shape Codes'


class DrawableComponent(models.Model):
    """Drawable Component Database"""
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=100)
    extra = models.CharField(max_length=4096)
    maker_icon = models.CharField(max_length=500)
    shape_code = models.ForeignKey(ShapeCode)

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Metadata for class Drawable Component"""
        verbose_name = 'Drawable Component'
        verbose_name_plural = 'Drawable Components'


class PlottedShape(models.Model):
    """Plotted Shape Database"""
    slum = models.CharField(max_length=100)
    name = models.CharField(max_length=512)
    lat_long = models.CharField(max_length=2000)
    drawable_component = models.ForeignKey(DrawableComponent)
    created_by = models.ForeignKey(User)
    created_on = models.DateTimeField(default=datetime.datetime.now())

    def __unicode__(self):
        """Returns string representation of object"""
        return self.name

    class Meta:
        """Metadata for class PlottedShape"""
        verbose_name = 'Plotted Shape'
        verbose_name_plural = 'Plotted Shapes'

CHOICES_ALL = (('0', 'None'), ('1', 'All'), ('2', 'Allow Selection'))

class RoleMaster(models.Model):
    """Role Master Database"""
    name = models.CharField(max_length=100)
    city = models.IntegerField(choices=CHOICES_ALL)
    slum = models.IntegerField(choices=CHOICES_ALL)
    kml = models.BooleanField(blank=False)
    dynamic_query = models.BooleanField(blank=False)
    predefined_query = models.BooleanField(blank=False)
    can_request = models.BooleanField(blank=False)
    users = models.BooleanField(blank=False)
    create_save_query = models.BooleanField(blank=False)
    deploy_survey = models.BooleanField(blank=False)
    upload_images = models.BooleanField(blank=False)
    prepare_reports = models.BooleanField(blank=False)

    class Meta:
        """Metadata for class RoleMaster"""
        verbose_name = 'Role Master'
        verbose_name_plural = 'Role Masters'

class UserRoleMaster(models.Model):
    """User Role Master Database"""
    user = models.ForeignKey(User)
    role_master = models.ForeignKey(RoleMaster)
    city = models.ForeignKey(City)
    slum = models.ForeignKey(Slum)

    class Meta:
        """Metadata for class UserRoleMaster"""
        verbose_name = 'User Role Master'
        verbose_name_plural = 'User Role Masters'


class ProjectMaster(models.Model):
    """Project Master Database"""
    created_user = models.CharField(max_length=100)
    created_date = models.DateTimeField(default=datetime.datetime.now())

    class Meta:
        """Metadata for class ProjectMaster"""
        verbose_name = 'Project Master'
        verbose_name_plural = 'Project Masters'


class Rapid_Slum_Appraisal(models.Model):
    slum_name = models.ForeignKey(Slum)
    approximate_population=models.IntegerField()
    toilet_cost=models.IntegerField()
    toilet_seat_to_persons_ratio = models.IntegerField()
    percentage_with_an_individual_water_connection = models.IntegerField()
    frequency_of_clearance_of_waste_containers=models.IntegerField()
    general_info_left_image = models.ImageField()
    toilet_info_left_image = models.ImageField()
    waste_management_info_left_image = models.ImageField()
    water_info_left_image = models.ImageField()
    roads_and_access_info_left_image = models.ImageField()
    drainage_info_left_image = models.ImageField() 
    gutter_info_left_image = models.ImageField(blank=True, null=True)     

class Individual_Fatsheet(models.Model):
    Name_of_the_family_head =  models.CharField(max_length=2048)
    Name_of_Native_village_district_and_state =  models.CharField(max_length=2048)
    Duration_of_stay_in_the_city  =  models.CharField(max_length=2048)
    Duration_of_stay_in_this_current_settlement  =  models.CharField(max_length=2048)
    Type_of_house  =  models.CharField(max_length=2048)
    Owner_or_tenant  =  models.CharField(max_length=2048)
    Total_family_members = models.IntegerField()
    Number_of_male_members  = models.IntegerField()
    Number_of_female_members  = models.IntegerField()
    Number_of_children_under_five_years_of_age = models.IntegerField()
    Number_of_members_over_60_years_of_age = models.IntegerField()
    Number_of_disabled_members = models.IntegerField()
    If_yes_specify_type_of_disability = models.CharField(max_length=50)
    Number_of_earning_members = models.IntegerField()
    Occupations_of_earning_members = models.CharField(max_length=2048)
    Approximate_monthly_family_income =  models.CharField(max_length=2048)
    img = models.ImageField()

 
            