from django import forms

class KMLUpload(forms.Form):
    kml_file = forms.FileField(label="Upload KML file")
    flag = forms.BooleanField(label="Is household")
