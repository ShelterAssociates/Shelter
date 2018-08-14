from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from master.models import *
from django.contrib import admin
from django.db.models.fields.related import ManyToOneRel
from mastersheet.models import *

class BaseForm(forms.Form):
    '''
        Base form class
    '''
    def clean_slum(self):
        """
        Check permissions of city level access
        :return: 
        """
        original_slum = self.instance.slum
        if not original_slum.has_permission(self.request.user):
            raise ValidationError("You do not have access to change this slum")
        slum = self.cleaned_data['slum']
        if not slum.has_permission(self.request.user):
            raise ValidationError("You do not have access to this slum")
        return slum

class VendorHouseholdInvoiceDetailForm(BaseForm, forms.ModelForm):

    class Meta:
        model = VendorHouseholdInvoiceDetail
        fields = '__all__'

class SBMUploadForm(BaseForm, forms.ModelForm):

    class Meta:
        model = SBMUpload
        fields = '__all__'

class ToiletConstructionForm(BaseForm, forms.ModelForm):

    class Meta:
        model = ToiletConstruction
        fields = '__all__'

class CommunityMobilizationForm(BaseForm, forms.ModelForm):

    class Meta:
        model = CommunityMobilization
        fields = '__all__'

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