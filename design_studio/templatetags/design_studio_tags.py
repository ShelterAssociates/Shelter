from django import template

from design_studio.permissions import can_edit_templates, can_use_design_studio

register = template.Library()


@register.filter(name="can_use_design_studio")
def can_use_design_studio_filter(user):
    return can_use_design_studio(user)


@register.filter(name="can_edit_design_templates")
def can_edit_templates_filter(user):
    return can_edit_templates(user)
