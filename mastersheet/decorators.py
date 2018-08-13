from master.models import Slum
from django.http import HttpResponseForbidden

def deco_city_permission(view_func):
    def _wrapped_view(request, *args, **kwargs):
        permissions = Slum.objects.get(pk = int(request.GET['slumname']))
        if not permissions.has_permission(request.user):
            return HttpResponseForbidden("You do not have a permission to access the slum")
        return view_func(request, *args, **kwargs)
    return _wrapped_view