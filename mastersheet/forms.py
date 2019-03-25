from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget, AdminTimeWidget
from master.models import *
from django.contrib import admin
from django.db.models.fields.related import ManyToOneRel
from mastersheet.models import *
from django.forms import extras

class BaseForm(forms.Form):
    '''
        Base form class
    '''
    def clean_slum(self):
        """
        Check permissions of city level access
        :return: 
        """
        if 'instance' in self and 'slum' in self.instance:
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
class account_find_slum(forms.Form):
    def __init__(self, *args, **kwargs):
        super(account_find_slum,self).__init__( *args, **kwargs)
        self.fields['account_slumname'] = forms.ModelChoiceField(queryset=Slum.objects.all(), widget=ForeignKeyRawIdWidget(rel=ManyToOneRel(Slum._meta.get_field('id'),Slum, 'id' ), admin_site=admin.site))
        self.fields['account_cityname'] = forms.ModelChoiceField(queryset = City.objects.all())
        self.fields['account_slumname'].widget.attrs.update({'class':'customized-form'})
        self.fields['account_slumname'].widget.attrs.update({'name':'account_slumname', 'id':'id_account_slumname'})
        self.fields['account_slumname'].label = "Select slum"
        self.fields['account_cityname'].widget.attrs.update({'class':'customized-form'})
        self.fields['account_cityname'].widget.attrs.update({'name':'account_cityname', 'id':'account_cityname'})
        self.fields['account_cityname'].label = "Select city"
        self.fields['account_start_date'] = forms.DateField(widget=AdminTimeWidget())
        self.fields['account_start_date'].label = "From"
        self.fields['account_start_date'].widget.attrs.update({'name':'account_start_date', 'class':'datepicker', 'style':'width:80px;'})
        self.fields['account_end_date'] = forms.DateField(widget=AdminTimeWidget())#extras.SelectDateWidget()) 
        self.fields['account_end_date'].label = "To"
        self.fields['account_end_date'].widget.attrs.update({'name':'account_end_date', 'class':'datepicker', 'style':'width:80px;'})
        


    class Meta:
        raw_id_fields = ('account_slumname',)
        model = 'Slum'

class file_form(forms.Form):
    file = forms.FileField(help_text="Files with xls and xlsx are accepted")
