from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget, ManyToManyRawIdWidget
from master.models import *
from django.contrib import admin
from django.db.models.fields.related import ManyToOneRel
from django.contrib.admin.widgets import FilteredSelectMultiple, RelatedFieldWidgetWrapper




class find_slum(forms.Form):
    def __init__(self, *args, **kwargs):
        super(find_slum,self).__init__( *args, **kwargs)
        self.fields['slumname'] = forms.ModelChoiceField(queryset=Slum.objects.all(), widget=ForeignKeyRawIdWidget(rel=ManyToOneRel(Slum._meta.get_field('id'),Slum, 'id' ), admin_site=admin.site))
        self.fields['slumname'].widget.attrs.update({'class':'customized-form'})

        #slum_name = forms.ModelChoiceField(label='Search Slum', queryset=Slum.objects.all())

    class Meta:
        raw_id_fields = ('slumname',)
        model = 'Slum'