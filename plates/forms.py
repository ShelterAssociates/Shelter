"""Single plate, Excel upload, and logo / font upload forms."""

import json
import os
import tempfile

from django import forms
from django.conf import settings
from PIL import Image, ImageFont

from plates.models import ASSET_KINDS, DPI_CHOICES, OUTPUT_KINDS, PLATE_TYPES, TEMPLATE_MODES, PlateAsset, PlateFont, PlateTemplate
from plates.services import codes, editor, excel, rows
from utils.uploads import file_extension

FIELD_FOR_REASON = (
    ("House number", "house_no"), ("DIGIPIN", "code"), ("Invalid DIGIPIN", "code"), ("Plus code", "code"), ("Invalid plus code", "code"),
    ("Latitude/Longitude", "lat"), ("Latitude", "lat"), ("Longitude", "long"), ("Slum Name", "slum"), ("Ward", "ward"), ("City", "city"),
)
NO_ANGLE_BRACKETS = "< and > are not allowed."


def styled(form):
    """The plates input classes on every widget (checkboxes keep the browser look)."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "pl-checkbox")
            continue
        if isinstance(widget, forms.CheckboxSelectMultiple):
            continue
        widget.attrs.setdefault("class", "pl-select" if isinstance(widget, forms.Select) else "pl-input")
    return form


def usable_templates(plate_type=None):
    """Active templates that are the latest version, newest first within each type."""
    templates = PlateTemplate.objects.filter(is_active=True, versions__isnull=True)
    if plate_type:
        templates = templates.filter(plate_type=plate_type)
    return templates.order_by("plate_type", "-is_default", "name")


class TemplateChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, template):
        return "{} ({}, v{}{})".format(template.name, template.get_plate_type_display(), template.version,
                                       ", default" if template.is_default else "")


def check_template_type(cleaned):
    template, plate_type = cleaned.get("template"), cleaned.get("plate_type")
    if template is not None and plate_type and template.plate_type != plate_type:
        raise forms.ValidationError("Pick a {} template for {} plates.".format(template.get_plate_type_display(), dict(PLATE_TYPES)[plate_type]))


class SingleForm(forms.Form):
    plate_type = forms.ChoiceField(choices=PLATE_TYPES)
    template = TemplateChoiceField(queryset=PlateTemplate.objects.none())
    code = forms.CharField(required=False, max_length=30, help_text="DIGIPIN or plus code; leave the DIGIPIN empty to compute it from latitude and longitude")
    lat = forms.CharField(label="Latitude", max_length=30)
    long = forms.CharField(label="Longitude", max_length=30)
    slum = forms.CharField(label="Slum Name", max_length=rows.MAX_SLUM)
    house_no = forms.CharField(label="House No", max_length=rows.MAX_HOUSE_NO)
    ward = forms.CharField(required=False, max_length=rows.MAX_OPTIONAL)
    city = forms.CharField(required=False, max_length=rows.MAX_OPTIONAL)
    holes = forms.BooleanField(required=False, initial=True, label="Drill holes",
                               help_text="Untick for a full plate or sticker without the drill-hole marks")
    side_panel = forms.BooleanField(required=False, label="Side panel (house no. and slum, cut off)",
                                    help_text="Adds a 19.1 mm reference panel at the side; the image gets wider by that much")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = usable_templates()
        self.row, self.warnings = None, []
        styled(self)

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        check_template_type(cleaned)
        values = {key: cleaned.get(key) for key in ("house_no", "code", "lat", "long", "slum", "ward", "city")}
        if cleaned["plate_type"] == "digipin" and not values["code"]:
            values["code"] = self.computed_digipin(values)
        try:
            self.row, self.warnings = rows.clean_row(values, cleaned["plate_type"])
        except rows.RowError as exc:
            self.add_error(field_for(str(exc)), str(exc))
        return cleaned

    def computed_digipin(self, values):
        try:
            return codes.encode_digipin(float(values["lat"]), float(values["long"]))
        except (ValueError, codes.CodeError):
            return ""


def field_for(reason):
    return next((field for prefix, field in FIELD_FOR_REASON if reason.startswith(prefix)), None)


class UploadForm(forms.Form):
    plate_type = forms.ChoiceField(choices=PLATE_TYPES)
    template = TemplateChoiceField(queryset=PlateTemplate.objects.none())
    file = forms.FileField(label="Excel file (.xlsx)")
    sheet_name = forms.CharField(required=False, max_length=120, label="Sheet (leave empty for the first sheet)")
    holes = forms.BooleanField(required=False, initial=True, label="Drill holes",
                               help_text="Untick for full plates or stickers without the drill-hole marks")
    side_panel = forms.BooleanField(required=False, label="Side panel (house no. and slum, cut off)",
                                    help_text="Adds a 19.1 mm reference panel at the side; the image gets wider by that much")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = usable_templates()
        styled(self)

    def clean_file(self):
        upload = self.cleaned_data["file"]
        try:
            excel.check_upload(upload)
        except excel.UploadError as exc:
            raise forms.ValidationError(str(exc))
        return upload

    def clean(self):
        cleaned = super().clean()
        check_template_type(cleaned)
        return cleaned


def plain_name(value):
    if "<" in value or ">" in value:
        raise forms.ValidationError(NO_ANGLE_BRACKETS)
    return value.strip()


def checked_image(upload):
    """A PNG or JPEG whose content matches its extension, within the size limits."""
    expected = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG"}.get(file_extension(upload.name))
    if expected is None:
        raise forms.ValidationError("Upload a PNG or JPEG image (SVG and other types are not accepted).")
    limit_mb = int(getattr(settings, "PLATES_MAX_ASSET_MB", 5))
    if upload.size > limit_mb * 1024 * 1024:
        raise forms.ValidationError("The image is larger than {} MB.".format(limit_mb))
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            image.verify()
            found, size = image.format, image.size
    except Exception:
        raise forms.ValidationError("This file is not a valid PNG or JPEG image.")
    finally:
        upload.seek(0)
    if found != expected:
        raise forms.ValidationError("The file content is not a {} image.".format(file_extension(upload.name).upper()))
    if max(size) > 4000:
        raise forms.ValidationError("The image is larger than 4000 pixels on a side.")
    return upload


class AssetForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        styled(self)

    class Meta:
        model = PlateAsset
        fields = ("name", "kind", "image", "recolourable", "is_default")

    kind = forms.ChoiceField(choices=ASSET_KINDS)

    def clean_name(self):
        return plain_name(self.cleaned_data["name"])

    def clean_image(self):
        return checked_image(self.cleaned_data["image"])


class FontForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        styled(self)

    class Meta:
        model = PlateFont
        fields = ("name", "file", "variation")

    def clean_name(self):
        return plain_name(self.cleaned_data["name"])

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("file")
        if upload is None:
            return cleaned
        if file_extension(upload.name) not in ("ttf", "otf"):
            raise forms.ValidationError("Upload a .ttf or .otf font file.")
        check_font(upload, cleaned.get("variation", ""))
        return cleaned


def check_font(upload, variation):
    """The font must open with Pillow, and the variation must be one of its named styles."""
    handle, path = tempfile.mkstemp(suffix="." + file_extension(upload.name))
    try:
        with os.fdopen(handle, "wb") as target:
            for chunk in upload.chunks():
                target.write(chunk)
        font = ImageFont.truetype(path, 40)
        if variation:
            try:
                names = [name.decode("utf-8", "ignore") for name in font.get_variation_names()]
            except OSError:
                names = []
            if variation not in names:
                raise forms.ValidationError("This font has no style named {}. Styles: {}.".format(variation, ", ".join(names) or "none"))
    except forms.ValidationError:
        raise
    except Exception:
        raise forms.ValidationError("This file is not a font Pillow can open.")
    finally:
        os.remove(path)
        upload.seek(0)


PANEL_FIELDS = (("house_no", "House No"), ("slum", "Slum Name"), ("ward", "Ward"), ("city", "City"))
DEFAULT_GRID = {"on": False, "opacity": 0.094118, "major": 0.5, "divisions": 4}
DEFAULT_BORDER = {"on": False, "inset": 0.037778, "radius": 0.051111, "width": 0.005556, "colour": "#FFFFFF", "opacity": 1}
DEFAULT_STRIP = {"on": False, "position": "bottom", "height": 0.03, "colours": ["#F58220", "#FFFFFF", "#138808"]}


def colour_field(required=True):
    return forms.RegexField(regex=r"^#[0-9A-Fa-f]{6}$", required=required, max_length=7,
                            error_messages={"invalid": "Use a colour like #2A2468."})


class TemplateForm(forms.Form):
    name = forms.CharField(max_length=120)
    plate_type = forms.ChoiceField(choices=PLATE_TYPES)
    output_kind = forms.ChoiceField(choices=OUTPUT_KINDS, help_text="A sticker has no drill holes by default")
    width_mm = forms.DecimalField(min_value=20, max_value=400, decimal_places=2, label="Width (mm, without side panel)")
    height_mm = forms.DecimalField(min_value=10, max_value=200, decimal_places=2, label="Height (mm)")
    dpi = forms.TypedChoiceField(choices=DPI_CHOICES, coerce=int, label="DPI")
    mode = forms.ChoiceField(choices=TEMPLATE_MODES, label="Background")
    background_image = forms.ModelChoiceField(queryset=PlateAsset.objects.filter(kind="background"), required=False)
    fill = forms.ChoiceField(choices=(("gradient", "Gradient"), ("solid", "Solid colour"), ("none", "None")))
    colour_1 = colour_field()
    colour_2 = colour_field(required=False)
    gradient_angle = forms.FloatField(min_value=0, max_value=90)
    grid_on = forms.BooleanField(required=False, label="Faint grid")
    border_on = forms.BooleanField(required=False, label="Rounded border")
    border_colour = colour_field()
    strip_on = forms.BooleanField(required=False, label="Tricolour strip")
    strip_position = forms.ChoiceField(choices=(("bottom", "Bottom"), ("top", "Top")))
    holes_on = forms.BooleanField(required=False, label="Drill holes")
    hole_diameter_mm = forms.FloatField(min_value=1, max_value=10, label="Hole diameter (mm)")
    hole_edge_mm = forms.FloatField(min_value=2, max_value=30, label="Hole centre from edge (mm)")
    hole_position = forms.ChoiceField(choices=(("sides", "Left and right, middle"), ("corners", "Four corners")))
    panel_on = forms.BooleanField(required=False, label="Side reference panel (cut off)")
    panel_side = forms.ChoiceField(choices=(("right", "Right"), ("left", "Left")))
    panel_width_mm = forms.FloatField(min_value=10, max_value=60, label="Panel width (mm)")
    panel_style = forms.ChoiceField(choices=(("labelled", "Labelled"), ("centred", "Centred, grey"), ("old", "Old style")))
    panel_fields = forms.MultipleChoiceField(choices=PANEL_FIELDS, required=False, widget=forms.CheckboxSelectMultiple)
    panel_cut_line = forms.BooleanField(required=False, label="Dashed cut line")
    qr_link_pattern = forms.CharField(max_length=300, label="QR link")
    qr_caption = forms.CharField(max_length=60, required=False, label="Text under QR")
    slum_suffix = forms.CharField(max_length=40, required=False, strip=False, label="Added after the slum name")
    elements_json = forms.CharField(widget=forms.Textarea(attrs={"rows": 14}), label="Elements")
    is_default = forms.BooleanField(required=False, label="Default for this plate type and kind")
    is_active = forms.BooleanField(required=False, label="Active (shown in pickers)")

    def __init__(self, *args, **kwargs):
        self.base = kwargs.pop("base", None) or {}
        self.resources = kwargs.pop("resources", None)
        self.check_layout = kwargs.pop("check_layout", True)
        super().__init__(*args, **kwargs)
        self.spec, self.values = None, {}
        styled(self)

    def clean_name(self):
        return plain_name(self.cleaned_data["name"])

    def clean_qr_caption(self):
        return plain_name(self.cleaned_data["qr_caption"]) if self.cleaned_data["qr_caption"] else ""

    def clean_slum_suffix(self):
        value = self.cleaned_data["slum_suffix"]
        if "<" in value or ">" in value:
            raise forms.ValidationError(NO_ANGLE_BRACKETS)
        return value

    def clean_elements_json(self):
        try:
            elements = json.loads(self.cleaned_data["elements_json"])
        except ValueError:
            raise forms.ValidationError("The elements are not valid JSON.")
        if not isinstance(elements, list):
            raise forms.ValidationError("The elements must be a list.")
        return elements

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        self.spec = build_spec(cleaned, self.base)
        self.values = {"name": cleaned["name"], "is_default": cleaned["is_default"], "is_active": cleaned["is_active"]}
        if self.check_layout:
            found = editor.problems(self.spec, self.resources)
            if found:
                raise forms.ValidationError(found)
        return cleaned


def merged(*parts, **changes):
    result = {}
    for part in parts:
        result.update(part or {})
    result.update(changes)
    return result


def build_spec(cleaned, base):
    """The renderer dict from the form; settings the form does not show (grid opacity, shadows...) are kept from base."""
    background = dict(base.get("background") or {})
    background.update(fill=cleaned["fill"], colours=[cleaned["colour_1"], cleaned["colour_2"] or cleaned["colour_1"]],
                      gradient_angle=cleaned["gradient_angle"])
    background["grid"] = merged(DEFAULT_GRID, background.get("grid"), on=cleaned["grid_on"])
    background["border"] = merged(DEFAULT_BORDER, background.get("border"), on=cleaned["border_on"], colour=cleaned["border_colour"])
    background["strip"] = merged(DEFAULT_STRIP, background.get("strip"), on=cleaned["strip_on"], position=cleaned["strip_position"])
    holes = merged(base.get("holes"), on=cleaned["holes_on"], diameter_mm=cleaned["hole_diameter_mm"],
                   edge_mm=cleaned["hole_edge_mm"], position=cleaned["hole_position"])
    panel = merged(base.get("side_panel"), on=cleaned["panel_on"], side=cleaned["panel_side"], width_mm=cleaned["panel_width_mm"],
                   style=cleaned["panel_style"], fields=list(cleaned["panel_fields"]) or ["house_no", "slum"], cut_line=cleaned["panel_cut_line"])
    image = cleaned.get("background_image")
    return {
        "plate_type": cleaned["plate_type"], "output_kind": cleaned["output_kind"], "width_mm": float(cleaned["width_mm"]),
        "height_mm": float(cleaned["height_mm"]), "dpi": cleaned["dpi"], "mode": cleaned["mode"],
        "background_image": image.pk if image else None, "background": background, "elements": cleaned["elements_json"],
        "holes": holes, "side_panel": panel, "qr_link_pattern": cleaned["qr_link_pattern"].strip(),
        "qr_caption": cleaned["qr_caption"], "slum_suffix": cleaned["slum_suffix"],
    }


def initial_for(spec, name="", is_default=False, is_active=True):
    """Form values for a template spec."""
    background, holes, panel = spec.get("background") or {}, spec.get("holes") or {}, spec.get("side_panel") or {}
    colours = background.get("colours") or ["#2A2468", "#4B42A8"]
    return {
        "name": name, "plate_type": spec["plate_type"], "output_kind": spec.get("output_kind", "plate"), "width_mm": spec["width_mm"],
        "height_mm": spec["height_mm"], "dpi": spec["dpi"], "mode": spec.get("mode", "designed"), "background_image": spec.get("background_image"),
        "fill": background.get("fill", "gradient"), "colour_1": colours[0], "colour_2": colours[-1],
        "gradient_angle": background.get("gradient_angle", 0), "grid_on": (background.get("grid") or {}).get("on", False),
        "border_on": (background.get("border") or {}).get("on", False), "border_colour": (background.get("border") or {}).get("colour", "#FFFFFF"),
        "strip_on": (background.get("strip") or {}).get("on", False), "strip_position": (background.get("strip") or {}).get("position", "bottom"),
        "holes_on": holes.get("on", True), "hole_diameter_mm": holes.get("diameter_mm", 4.5), "hole_edge_mm": holes.get("edge_mm", 5),
        "hole_position": holes.get("position", "sides"), "panel_on": panel.get("on", False), "panel_side": panel.get("side", "right"),
        "panel_width_mm": panel.get("width_mm", 19.1), "panel_style": panel.get("style", "labelled"),
        "panel_fields": panel.get("fields", ["house_no", "slum"]), "panel_cut_line": panel.get("cut_line", True),
        "qr_link_pattern": spec.get("qr_link_pattern", ""), "qr_caption": spec.get("qr_caption", ""), "slum_suffix": spec.get("slum_suffix", ""),
        "elements_json": json.dumps(spec.get("elements") or [], indent=1), "is_default": is_default, "is_active": is_active,
    }
