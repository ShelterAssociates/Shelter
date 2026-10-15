#!/usr/bin/python
# -*- coding: utf-8 -*-
"""The Django Forms Page for master app"""

from django import forms

from master.models import (
    Survey,
    City,
    Rapid_Slum_Appraisal,
    AdministrativeWard,
    ElectoralWard,
    Slum,
    drainage,
)
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.forms import widgets
from django.core.exceptions import ValidationError

from django.contrib.auth.forms import AuthenticationForm


class LocationWidget(widgets.TextInput):
    """Map Widget"""

    template_name = "draw.html"

    def render(self, name, value, attrs=None, renderer=None):
        context = {"POLYGON": value}
        return mark_safe(render_to_string(self.template_name, context))


class CityFrom(forms.ModelForm):
    """City Form"""

    shape = forms.CharField(widget=LocationWidget())

    class Meta:
        model = City
        fields = (
            "name",
            "shape",
            "state_code",
            "district_code",
            "city_code",
            "border_color",
            "background_color",
        )
        exclude = ("created_by", "created_on")

    def clean_shape(self):
        shape = self.cleaned_data.get("shape")
        if shape == "None":
            raise forms.ValidationError("Please draw Polygon")
        return shape


class AdministrativeWardFrom(forms.ModelForm):
    """AdministrativeWard Form"""

    shape = forms.CharField(widget=LocationWidget())

    class Meta:
        model = AdministrativeWard
        fields = "__all__"

    def clean_shape(self):
        shape = self.cleaned_data.get("shape")
        if shape == "None":
            raise forms.ValidationError("Please draw Polygon")
        return shape


class ElectoralWardForm(forms.ModelForm):
    """Electoral Ward Form"""

    shape = forms.CharField(widget=LocationWidget())

    class Meta:
        model = ElectoralWard
        fields = "__all__"

    def clean_shape(self):
        shape = self.cleaned_data.get("shape")
        if shape == "None":
            raise forms.ValidationError("Please draw Polygon")
        return shape


class SlumForm(forms.ModelForm):
    """Slum Form"""

    shape = forms.CharField(widget=LocationWidget())

    class Meta:
        model = Slum
        fields = "__all__"

    def clean_shape(self):
        shape = self.cleaned_data.get("shape")
        if shape == "None":
            raise forms.ValidationError("Please draw Polygon")
        return shape


class Rapid_Slum_AppraisalForm(forms.ModelForm):
    """Rapid Slum AppraisalForm"""

    class Meta:
        model = Rapid_Slum_Appraisal
        fields = "__all__"


class ReportForm(forms.Form):
    City = forms.ChoiceField()
    AdministrativeWard_Name_List = []
    Default = ("0", "---select---")
    AdministrativeWard_Name_List.append(Default)
    AdministrativeWard = forms.ChoiceField(choices=AdministrativeWard_Name_List)
    ElectoralWard_Name_List = []
    Default = ("0", "---select---")
    ElectoralWard_Name_List.append(Default)
    ElectoralWard = forms.ChoiceField(choices=ElectoralWard_Name_List)
    Slum_Name_List = []
    Default = ("0", "---select---")
    Slum_Name_List.append(Default)
    Slum = forms.ChoiceField(choices=Slum_Name_List)
    form = forms.ChoiceField()


class DrainageForm(forms.ModelForm):
    """Drainage sForm"""

    class Meta:
        model = drainage
        fields = "__all__"


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
