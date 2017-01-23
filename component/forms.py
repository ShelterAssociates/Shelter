from django import forms
from master.models import City, AdministrativeWard, ElectoralWard, Slum

class KMLUpload(forms.Form):
    AdministrativeWard = forms.ModelChoiceField(queryset=AdministrativeWard.objects.all(), required=True, error_messages={'required':'Please select administrative ward'})
    City = forms.ModelChoiceField(queryset=City.objects.all(),required=True, error_messages={'required':'Please select city'})
    ElectoralWard = forms.ModelChoiceField(queryset=ElectoralWard.objects.all(), required=True, error_messages={'required':'Please select electoral ward'})
    slum_name = forms.ModelChoiceField(queryset=Slum.objects.all(),required=True, error_messages={'required':'Please select slum'})
    kml_file = forms.FileField(required=True, label="Upload KML file", error_messages={'required':'Please select KML file'})

    def __init__(self, *args, **kwargs):
        super(KMLUpload, self).__init__(*args, **kwargs)
        self.fields["AdministrativeWard"].choices = [("", "--Please select--"),] + list(self.fields["AdministrativeWard"].choices)[1:]
        self.fields["City"].choices = [("", "--Please select--"),] + list(self.fields["City"].choices)[1:]
        self.fields["ElectoralWard"].choices = [("", "--Please select--"),] + list(self.fields["ElectoralWard"].choices)[1:]
        self.fields["slum_name"].choices = [("", "--Please select--"),] + list(self.fields["slum_name"].choices)[1:]
