from django import template

from plates.permissions import can_edit_templates, can_use_plates

register = template.Library()


@register.filter(name="can_use_plates")
def can_use_plates_filter(user):
    return can_use_plates(user)


@register.filter(name="can_edit_plate_templates")
def can_edit_templates_filter(user):
    return can_edit_templates(user)
