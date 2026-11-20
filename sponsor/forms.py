import os

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.urls import reverse

from utils.uploads import validate_document, validate_image, validate_zip

from .models import ProjectDocuments, ProjectImages, Sponsor, SponsorProjectDetailsSubFields

# What the protected view will serve. Wider than the upload rule (PDF/JPG/JPEG/PNG)
# so the older .ppt document keeps downloading; active types never appear here.
SERVED_DOCUMENT_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "ppt", "pptx", "doc", "docx"]
SERVED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "jfif", "png"]


class _Link:
    def __init__(self, url, label):
        self.url = url
        self.label = label

    def __str__(self):
        return self.label


class ProtectedFileInput(forms.ClearableFileInput):
    """Links the current file to the login-checked view instead of /media/."""

    protected_url = None

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.protected_url and context["widget"]["is_initial"]:
            context["widget"]["value"] = _Link(self.protected_url, os.path.basename(str(value)))
        return context


class _ProtectedFileForm(forms.ModelForm):
    file_field = None
    kind = None
    validator = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget = ProtectedFileInput()
        if self.instance.pk:
            widget.protected_url = reverse("sponsor_project_file", args=[self.kind, self.instance.pk])
        self.fields[self.file_field].widget = widget

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get(self.file_field)
        if isinstance(upload, UploadedFile):
            try:
                type(self).validator(upload)
            except forms.ValidationError as error:
                self.add_error(self.file_field, error)
        return cleaned


class ProjectDocumentForm(_ProtectedFileForm):
    file_field = "document"
    kind = "document"
    validator = validate_document

    class Meta:
        model = ProjectDocuments
        fields = "__all__"


class ProjectImageForm(_ProtectedFileForm):
    file_field = "image"
    kind = "image"
    validator = validate_image

    class Meta:
        model = ProjectImages
        fields = "__all__"


class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = "__all__"

    def clean_logo(self):
        upload = self.cleaned_data.get("logo")
        if isinstance(upload, UploadedFile):
            validate_image(upload)
        return upload


class SponsorProjectDetailsSubFieldsForm(forms.ModelForm):
    class Meta:
        model = SponsorProjectDetailsSubFields
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget = ProtectedFileInput()
        if self.instance.pk:
            widget.protected_url = reverse("sponsor_ff_report_zip", args=[self.instance.pk])
        self.fields["zip_file"].widget = widget

    def clean_zip_file(self):
        upload = self.cleaned_data.get("zip_file")
        if isinstance(upload, UploadedFile):
            validate_zip(upload)
        return upload
