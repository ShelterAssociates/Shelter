import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from master.models import Slum
from .kmlparser import HOUSE_BASE_LAYER_CODE
from .models import Component

# Members of this Django group (created in the admin) and superusers may use the 3D view.
VIEW_3D_GROUP = "3d_view"


def can_view_3d(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name=VIEW_3D_GROUP).exists()
    )


@require_GET
def get_3d_view_data(request, slum_id):
    """House footprints (Polygon/MultiPolygon only) for the 3D view of one slum.

    The only data source of the 3D view, so the permission check here, not the
    UI, is what gates it.

    Response: {"houses": [{"housenumber": ..., "shape": {GeoJSON}}, ...]}
    """
    if not can_view_3d(request.user):
        return JsonResponse({"error": "Not allowed"}, status=403)

    slum = get_object_or_404(Slum, pk=slum_id)
    components = slum.components.filter(
        metadata__code=HOUSE_BASE_LAYER_CODE,
        metadata__visible=True,
        metadata__type="C",
    ).order_by("housenumber")

    houses = []
    for comp in components:
        shape = json.loads(comp.shape.json)
        if shape["type"] in ("Polygon", "MultiPolygon"):
            houses.append({"housenumber": comp.housenumber, "shape": shape})
    return JsonResponse({"houses": houses})
