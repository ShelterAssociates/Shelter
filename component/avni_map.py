"""Endpoints for the Avni mobile app's map picker.

The Shelter Associates build of the Avni client lets a field worker tap the
building they are standing in front of instead of typing the house number.
For that it needs two things from us:

* ``GET  /component/get_structures_for_avni/?avni_uuid=<AddressLevel uuid>``
  every house footprint of the slum (Structure, or HouseBaseLayer for slums
  without one) as a GeoJSON FeatureCollection, plus the slum ``boundary``,
  gzip-compressed when the client accepts it (8-9k polygons is ~5 MB raw,
  ~400 KB gzipped). Downloaded once per sync and cached on the phone.
* ``POST /component/map_subject_to_structure/``
  ``{"subject_uuid", "structure_id", "avni_uuid"}`` — records which footprint
  the household was registered on (SubjectStructureMapping), so survey
  records and polygons are linked at data entry rather than joined by house
  number afterwards.

The slum is resolved from the AddressLevel uuid through the same
slum_location_uuids.json the syncs use (avni.locations), so a slum is
"map-enabled" as soon as it has an Avni location mapped there.

Both endpoints are authenticated with a shared key the app sends in the
``X-Avni-Gis-Key`` header (``settings.AVNI_GIS_API_KEY``, per environment in
local_settings.py). Polygons are public data on the website anyway, but the
POST writes to the database, and one mechanism for both keeps the client
simple. With the key unset the endpoints refuse (503) rather than open up.
"""

import hmac
import json
import logging
from functools import wraps

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.gzip import gzip_page
from django.views.decorators.http import require_GET, require_POST

from avni import mappings
from avni.locations import slum_id_for_location_uuid
from component.models import Component, Metadata, SubjectStructureMapping
from master.models import Slum
from survey.identity import household_number_from

logger = logging.getLogger(__name__)

API_KEY_HEADER = "HTTP_X_AVNI_GIS_KEY"
STRUCTURE_METADATA_NAME = "Structure"
HOUSE_BASE_LAYER_CODE = "HouseBaseLayer"
BOUNDARY_METADATA_NAME = "Slum boundary"


def error(message, status):
    return JsonResponse({"error": message}, status=status)


def requires_api_key(view):
    """Reject the request unless X-Avni-Gis-Key matches settings.AVNI_GIS_API_KEY."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        expected = getattr(settings, "AVNI_GIS_API_KEY", "") or ""
        if not expected:
            logger.error("AVNI_GIS_API_KEY is not set; refusing %s", request.path)
            return error("AVNI_GIS_API_KEY is not configured on the server", 503)
        supplied = request.META.get(API_KEY_HEADER, "")
        if not hmac.compare_digest(supplied, expected):
            return error("missing or invalid X-Avni-Gis-Key header", 401)
        return view(request, *args, **kwargs)

    return wrapped


def slum_for_avni_uuid(avni_uuid):
    """(Slum, None) for a mapped uuid, else (None, error response)."""
    if not avni_uuid:
        return None, error("avni_uuid is required", 400)
    slum_id = slum_id_for_location_uuid(avni_uuid)
    if slum_id is None:
        return None, error("no slum is mapped to avni_uuid {}".format(avni_uuid), 404)
    slum = Slum.objects.filter(id=slum_id).first()
    if slum is None:
        logger.error("slum_location_uuids.json maps %s to slum %s, which does not exist", avni_uuid, slum_id)
        return None, error("slum {} for avni_uuid {} not found".format(slum_id, avni_uuid), 404)
    return slum, None


def structure_components(slum):
    # Slums digitised before the Structure layer existed only have a HouseBaseLayer (as the export view).
    components = Component.objects.filter(component_slum=slum)
    structures = components.filter(metadata__name=STRUCTURE_METADATA_NAME)
    return structures if structures.exists() else components.filter(metadata__code=HOUSE_BASE_LAYER_CODE)


def concepts_for_rhs_key(rhs_key):
    """Avni concept names the sync writes to this rhs_data key; the key itself when it is written through unchanged."""
    concepts = []
    for table in (mappings.RHS_KEYS, mappings.FACTSHEET_KEYS, mappings.SANITATION_KEYS):
        if table.get(rhs_key) and table[rhs_key] not in concepts:
            concepts.append(table[rhs_key])
    for concept, key in mappings.KNOWN_QUESTION_MAP.items():
        if key == rhs_key and concept not in concepts:
            concepts.append(concept)
    return concepts or [rhs_key]


def filter_styles():
    """The website's filter rows as {concepts, answers, colours}, so the app can colour the same answers the same way."""
    styles = []
    for metadata in Metadata.objects.filter(type="F").exclude(code__isnull=True).order_by("section__order", "order", "id"):
        question, separator, options = (metadata.code or "").partition(":")
        blob = metadata.blob or {}
        answers = [option.strip() for option in options.split("|,|") if option.strip()]
        if not separator or not answers or not blob.get("polycolor"):
            continue
        styles.append({
            "name": metadata.name,
            "concepts": concepts_for_rhs_key(question.strip()),
            "answers": answers,
            "polycolor": blob.get("polycolor"),
            "linecolor": blob.get("linecolor"),
        })
    return styles


def slum_boundary(slum):
    uploaded = Component.objects.filter(component_slum=slum, metadata__name=BOUNDARY_METADATA_NAME).first()
    shape = uploaded.shape if uploaded is not None else slum.shape
    return json.loads(shape.geojson) if shape is not None else None


@require_GET
@requires_api_key
@gzip_page
def get_structures_for_avni(request):
    slum, failure = slum_for_avni_uuid(request.GET.get("avni_uuid"))
    if failure:
        return failure
    features = [
        {"type": "Feature", "geometry": json.loads(component.shape.geojson), "properties": {"s": component.housenumber}}
        for component in structure_components(slum).only("housenumber", "shape")
    ]
    collection = {
        "type": "FeatureCollection",
        "avni_uuid": request.GET.get("avni_uuid"),
        "slum_id": slum.id,
        "slum_name": slum.name,
        "boundary": slum_boundary(slum),
        "filters": filter_styles(),
        "total": len(features),
        "features": features,
    }
    # Compact separators: "s" instead of "housenumber" and no whitespace save
    # a few hundred KB before gzip on a large slum.
    return HttpResponse(json.dumps(collection, separators=(",", ":")), content_type="application/json")


def find_structure(slum, structure_id):
    """The Structure footprint numbered structure_id in slum, or None.

    The map sends Component.housenumber verbatim, but numbers reach us in
    both '35' and '0035' form, so both spellings are tried.
    """
    candidates = {structure_id, household_number_from(structure_id)}
    return structure_components(slum).filter(housenumber__in=candidates).order_by("id").first()


@csrf_exempt
@require_POST
@requires_api_key
def map_subject_to_structure(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return error("request body must be JSON", 400)
    if not isinstance(payload, dict):
        return error("request body must be a JSON object", 400)

    subject_uuid = str(payload.get("subject_uuid") or "").strip()
    structure_id = str(payload.get("structure_id") or "").strip()
    if not subject_uuid or not structure_id:
        return error("subject_uuid and structure_id are required", 400)

    slum, failure = slum_for_avni_uuid(payload.get("avni_uuid"))
    if failure:
        return failure

    component = find_structure(slum, structure_id)
    if component is None:
        logger.warning("No Structure #%s in slum %s (%s) for subject %s", structure_id, slum.id, slum.name, subject_uuid)

    mapping, created = SubjectStructureMapping.objects.update_or_create(
        subject_uuid=subject_uuid,
        defaults={"slum": slum, "structure_id": household_number_from(structure_id), "component": component},
    )
    return JsonResponse({
        "status": "ok",
        "created": created,
        "subject_uuid": mapping.subject_uuid,
        "structure_id": mapping.structure_id,
        "slum_id": slum.id,
        "component_id": component.id if component else None,
    })
