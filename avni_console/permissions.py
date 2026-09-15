"""Who may open the console and who may push data into AVNI."""

from functools import wraps

from django.conf import settings
from django.http import HttpResponseForbidden


def group_names(user):
    return set(user.groups.values_list("name", flat=True))


def can_use_console(user):
    """Superusers, AVNI_SYNC_GROUPS members, and anyone who can write (writing implies reading)."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    allowed = set(getattr(settings, "AVNI_SYNC_GROUPS", [])) | set(getattr(settings, "AVNI_WRITE_GROUPS", []))
    return bool(allowed & group_names(user))


def can_write_avni(user):
    """Superusers and AVNI_WRITE_GROUPS members only; this changes data in AVNI itself."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    return bool(set(getattr(settings, "AVNI_WRITE_GROUPS", [])) & group_names(user))


def console_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not can_use_console(request.user):
            return HttpResponseForbidden("The AVNI sync console is limited to the data team.")
        return view(request, *args, **kwargs)
    return guarded


def write_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if not can_write_avni(request.user):
            return HttpResponseForbidden("Updating AVNI is limited to the AVNI write group.")
        return view(request, *args, **kwargs)
    return guarded
