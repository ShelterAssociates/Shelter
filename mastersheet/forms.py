from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from master.models import *
from django.contrib import admin
from django.db.models.fields.related import ManyToOneRel




class find_slum(forms.Form):
    def __init__(self, *args, **kwargs):
        super(find_slum,self).__init__( *args, **kwargs)
        self.fields['slumname'] = forms.ModelChoiceField(queryset=Slum.objects.all(), widget=ForeignKeyRawIdWidget(rel=ManyToOneRel(Slum._meta.get_field('id'),Slum, 'id' ), admin_site=admin.site))
        self.fields['slumname'].widget.attrs.update({'class':'customized-form'})
        self.fields['slumname'].label = "Select slum"

    class Meta:
        raw_id_fields = ('slumname',)
        model = 'Slum'

class file_form(forms.Form):
    file = forms.FileField(help_text="Files with xls and xlsx are accepted")