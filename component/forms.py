from django import forms
from master.models import City, AdministrativeWard, ElectoralWard, Slum
from component.models import METRIC_UNIT_CHOICES


class KMLUpload(forms.Form):
    level = forms.ChoiceField(
        choices=(("City", "City"), ("Slum", "Slum")),
        required=True,
        error_messages={"required": "Please select the level"},
    )
    AdministrativeWard = forms.ModelChoiceField(
        queryset=AdministrativeWard.objects.all(),
        required=False,
        error_messages={"required": "Please select administrative ward"},
    )
    City = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=True,
        error_messages={"required": "Please select city"},
    )
    ElectoralWard = forms.ModelChoiceField(
        queryset=ElectoralWard.objects.all(),
        required=False,
        error_messages={"required": "Please select electoral ward"},
    )
    slum_name = forms.ModelChoiceField(
        queryset=Slum.objects.all(),
        required=False,
        error_messages={"required": "Please select slum"},
    )
    kml_file = forms.FileField(
        required=True,
        label="Upload KML file",
        error_messages={"required": "Please select KML file"},
    )
    delete_flag = forms.BooleanField(
        required=False, label="Do you want to deleted previous records?"
    )
    metric_value = forms.DecimalField(
        required=False,
        label="Known length/metric (optional)",
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"placeholder": "Value", "step": "0.01"}),
    )
    metric_unit = forms.ChoiceField(
        choices=(("", "--Unit--"),) + METRIC_UNIT_CHOICES,
        required=False,
        label="Unit",
    )
    metric_reason = forms.CharField(
        required=False,
        label="Reason (required if a metric value is given)",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Why are you providing this metric?"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        metric_value = cleaned_data.get("metric_value")
        if metric_value is not None:
            if not cleaned_data.get("metric_unit"):
                self.add_error("metric_unit", "Please select a unit for the metric value.")
            if not (cleaned_data.get("metric_reason") or "").strip():
                self.add_error(
                    "metric_reason", "A reason is required when providing a metric value."
                )
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(KMLUpload, self).__init__(*args, **kwargs)
        self.fields["AdministrativeWard"].choices = [
            ("", "--Please select--"),
        ] + list(
            self.fields["AdministrativeWard"].choices
        )[1:]
        self.fields["City"].choices = [
            ("", "--Please select--"),
        ] + list(
            self.fields["City"].choices
        )[1:]
        self.fields["ElectoralWard"].choices = [
            ("", "--Please select--"),
        ] + list(
            self.fields["ElectoralWard"].choices
        )[1:]
        self.fields["slum_name"].choices = [
            ("", "--Please select--"),
        ] + list(
            self.fields["slum_name"].choices
        )[1:]
