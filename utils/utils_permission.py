from django.http import HttpResponseForbidden
from django.core.exceptions import PermissionDenied

def deco_rhs_permission(view_func):
    """
    Decorator to check if user is superuser/sponsor/ulb
    :param view_func: 
    :return: 
    """
    def _wrapped_view(request, *args, **kwargs):
        permissions = [
            request.user.is_superuser,
            request.user.groups.filter(name='sponsor').exists(),
            request.user.groups.filter(name='ulb').exists()
        ]
        if not any(permissions):
            return HttpResponseForbidden("You do not have a permission")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def apply_permissions_ajax(perms):
    """
    Parameterised decorator for handling ajax permissions.
    :param perms: permission to check
    :return: Forbidden if does not have a permission else the function call.
    """
    def real_decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # it is possible to add some other checks, that return booleans
            # or do it in a separate `if` statement
            # for example, check for some user permissions or properties

            permissions = [
                request.is_ajax(),
                request.user.has_perm(perms)
            ]
            if not all(permissions):
                return HttpResponseForbidden("Permission denied")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return real_decorator

def access_right(func):
	def wrapper(request, *args, **kwargs):
		# if request.META.get('HTTP_REFERER')==None or "app.shelter-associates.org" not in request.META.get('HTTP_REFERER'):
		# 	raise PermissionDenied()
		return func(request, *args, **kwargs)
	return wrapper