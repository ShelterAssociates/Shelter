"""Who may make plates and who may change plate templates. Being staff alone never grants access."""

from functools import wraps

from django.conf import settings
from django.http import HttpResponseForbidden

DENIED = "You do not have access to this page."


def in_groups(user, setting_name):
    names = getattr(settings, setting_name, []) or []
    return bool(names) and user.groups.filter(name__in=names).exists()


def can_use_design_studio(user):
    """Superusers and DESIGN_STUDIO_GROUPS members."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    return user.is_superuser or in_groups(user, "DESIGN_STUDIO_GROUPS")


def can_edit_templates(user):
    """Superusers and DESIGN_STUDIO_TEMPLATE_GROUPS members (who must also be able to use plates)."""
    if not can_use_design_studio(user):
        return False
    return user.is_superuser or in_groups(user, "DESIGN_STUDIO_TEMPLATE_GROUPS")


def forbidden():
    return HttpResponseForbidden(DENIED)


def design_studio_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not can_use_design_studio(request.user):
            return forbidden()
        return view(request, *args, **kwargs)
    return guarded


def templates_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not can_edit_templates(request.user):
            return forbidden()
        return view(request, *args, **kwargs)
    return guarded
