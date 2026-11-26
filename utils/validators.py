import math
import re

from django.core.exceptions import ValidationError

_MARKUP = re.compile(r"[<>]")
MARKUP_MESSAGE = "Names cannot contain < or >."


def contains_markup(value):
    return bool(value) and bool(_MARKUP.search(str(value)))


def reject_markup(value):
    """Place names are plain text; angle brackets in them only ever carry HTML or script."""
    if contains_markup(value):
        raise ValidationError(MARKUP_MESSAGE)
    return value


def plain_text_form(form_class, fields):
    """Subclass of form_class that refuses < or > in the given text fields."""

    class PlainTextForm(form_class):
        def clean(self):
            cleaned = super().clean()
            for name in fields:
                if name in self.fields and contains_markup(cleaned.get(name)):
                    self.add_error(name, MARKUP_MESSAGE)
            return cleaned

    PlainTextForm.__name__ = form_class.__name__
    return PlainTextForm


class PlainTextAdminMixin:
    """For a ModelAdmin or inline: names typed here are shown on other pages, so they must be plain text."""

    plain_text_fields = ("name",)

    def get_form(self, request, obj=None, **kwargs):
        return plain_text_form(super().get_form(request, obj, **kwargs), self.plain_text_fields)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form = plain_text_form(formset.form, self.plain_text_fields)
        return formset


MAX_AMOUNT = 1000000000


def range_form(form_class, ranges):
    """Subclass of form_class that keeps each listed number finite and within (minimum, maximum)."""

    class RangeForm(form_class):
        def clean(self):
            cleaned = super().clean()
            for name, (minimum, maximum) in ranges.items():
                value = cleaned.get(name)
                if name not in self.fields or value is None:
                    continue
                if not math.isfinite(float(value)) or not minimum <= value <= maximum:
                    self.add_error(name, "Must be between %s and %s." % (minimum, maximum))
            return cleaned

    RangeForm.__name__ = form_class.__name__
    return RangeForm


class AmountRangeAdminMixin:
    """For a ModelAdmin or inline: numbers in amount_ranges must lie in their (minimum, maximum)."""

    amount_ranges = {}

    def get_form(self, request, obj=None, **kwargs):
        return range_form(super().get_form(request, obj, **kwargs), self.amount_ranges)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form = range_form(formset.form, self.amount_ranges)
        return formset
