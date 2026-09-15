from django import template

from avni_console.permissions import can_use_console

register = template.Library()


@register.filter
def can_use_avni_console(user):
    return can_use_console(user)
