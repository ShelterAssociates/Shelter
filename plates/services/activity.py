"""The PlateActivity audit trail and the single-plate rate limit (counted in the database, so all workers share it)."""

import datetime

from django.core.validators import validate_ipv46_address
from django.core.exceptions import ValidationError
from django.utils import timezone

from shelter.auth_throttle import client_ip

SINGLE_PLATES_PER_MINUTE = 60


def request_ip(request):
    ip = client_ip(request)
    try:
        validate_ipv46_address(ip)
    except ValidationError:
        return None
    return ip


def log(request, action, batch=None, template=None, detail=""):
    from plates.models import PlateActivity

    return PlateActivity.objects.create(
        user=request.user if request.user.is_authenticated else None, action=action, batch=batch,
        template=template, detail=(detail or "")[:200], ip=request_ip(request),
    )


def single_plates_left(user):
    from plates.models import PlateActivity

    since = timezone.now() - datetime.timedelta(minutes=1)
    used = PlateActivity.objects.filter(user=user, action="single_plate", created_on__gte=since).count()
    return SINGLE_PLATES_PER_MINUTE - used
