"""
utils_permissions.py — View permission decorators for the Shelter project.

Environment behaviour is driven by BASE_APP_URL from local_settings.py:
    Local dev   → BASE_APP_URL = "http://127.0.0.1:8000"
    Production  → BASE_APP_URL = "https://shelter-associates.org"

No separate files needed — the same file behaves correctly in both
environments automatically.
"""

import functools
from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.conf import settings


def _is_production():
    """
    Returns True if running in production, based on BASE_APP_URL.
    Local dev URLs contain '127.0.0.1' or 'localhost'.
    """
    base_url = getattr(settings, 'BASE_APP_URL', '')
    return '127.0.0.1' not in base_url and 'localhost' not in base_url


def deco_rhs_permission(view_func):
    """
    Restricts a view to superusers, sponsors, or ULB group members.
    Any user outside these three groups gets a 403 Forbidden response.
    """
    @functools.wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        permissions = [
            request.user.is_superuser,
            request.user.groups.filter(name='sponsor').exists(),
            request.user.groups.filter(name='ulb').exists(),
        ]
        if not any(permissions):
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def apply_permissions_ajax(perms):
    """
    Parameterised decorator for AJAX views.
    Checks that:
      1. The request was made via AJAX (X-Requested-With: XMLHttpRequest header)
      2. The user has the specified permission

    Note: request.is_ajax() was removed in Django 3.1. We now read the
    X-Requested-With header directly, which is what is_ajax() did internally.
    jQuery sends this header automatically. For fetch() calls add:
        headers: { 'X-Requested-With': 'XMLHttpRequest' }

    Usage:
        @apply_permissions_ajax('myapp.can_do_thing')
        def my_view(request): ...
    """
    def real_decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            permissions = [
                is_ajax,
                request.user.has_perm(perms),
            ]
            if not all(permissions):
                return HttpResponseForbidden("Permission denied.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return real_decorator


def access_right(func):
    """
    Checks that the request originates from the correct domain by inspecting
    the HTTP Referer header.

    Behaviour is automatic based on BASE_APP_URL in local_settings.py:

        Local dev   (BASE_APP_URL contains 127.0.0.1 or localhost):
            → Referer check is SKIPPED. All requests allowed through so
              you can test freely from localhost, Postman, or any browser tab.

        Production  (BASE_APP_URL is the live domain):
            → Referer check is ENFORCED. Requests with a missing or
              non-matching Referer header are rejected with 403 PermissionDenied.

    Note: Referer headers can be spoofed — this is a convenience guard,
    not a hard security boundary. Use proper authentication and Django
    permissions for sensitive operations.
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if _is_production():
            allowed_domain = settings.BASE_APP_URL.replace('https://', '').replace('http://', '')
            referer = request.META.get('HTTP_REFERER', '')
            if not referer or allowed_domain not in referer:
                raise PermissionDenied()
        return func(request, *args, **kwargs)

    return wrapper