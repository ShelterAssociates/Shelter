from collections import OrderedDict

from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.db.models.functions import Intersection, Length, Transform
from django.db.models import Case, CharField, Count, Func, IntegerField, Sum, Value, When

from graphs.models import HouseholdData


class _STGeometryType(Func):
    """Wraps PostGIS's ST_GeometryType(geom), e.g. 'ST_LineString'."""

    function = "ST_GeometryType"
    output_field = CharField()


def _get_line_only_metadata_names(slum):
    """
    Component (type "C") metadata names for this slum whose shapes are
    exclusively LineString/MultiLineString — i.e. genuine line features
    (roads, drainage lines, railway lines, etc.), as opposed to component
    types that are fundamentally points/polygons with the occasional
    mis-digitised line record (e.g. "Structure", "Slum boundary").
    """
    rows = (
        slum.components.filter(metadata__type="C")
        .annotate(geom_type=_STGeometryType("shape"))
        .values("metadata__name")
        .annotate(
            total=Count("id"),
            # `Count("id", filter=Q(...))` compiles to SQL's FILTER (WHERE ...)
            # clause, which older PostgreSQL servers (pre-9.4) reject with a
            # syntax error. COUNT(CASE WHEN ... THEN id END) is equivalent and
            # portable across all PostgreSQL versions this app targets.
            line_count=Count(
                Case(
                    When(
                        geom_type__in=["ST_LineString", "ST_MultiLineString"],
                        then="id",
                    ),
                    output_field=IntegerField(),
                )
            ),
        )
    )
    return [
        row["metadata__name"]
        for row in rows
        if row["total"] > 0 and row["total"] == row["line_count"]
    ]

_HOUSEHOLD_JSON_FIELDS = []
for _field_name in ("hh_data", "rhs_data", "ff_data"):
    try:
        HouseholdData._meta.get_field(_field_name)
        _HOUSEHOLD_JSON_FIELDS.append(_field_name)
    except Exception:
        pass


def _base_household_number(value):
    if value is None:
        return ""
    return str(value).split(".")[0].strip()


def _normalize_text(value):
    return str(value or "").strip().lower()


def _get_household_json(record):
    """
    Return the household JSON blob from whichever field exists in this branch.
    We support `hh_data` first because that is the field you described, then
    fall back to the older RHS/FF fields used elsewhere in the app.
    """
    for field_name in _HOUSEHOLD_JSON_FIELDS:
        if hasattr(record, field_name):
            payload = getattr(record, field_name, None)
            if isinstance(payload, dict) and payload:
                return payload
    return {}


def _get_select_ward_value(payload):
    if not isinstance(payload, dict):
        return ""

    for key, value in payload.items():
        if _normalize_text(key) == "select ward":
            return str(value or "").strip()

    return ""


def _find_admin_ward_component(slum):
    if not slum:
        return None

    for component in slum.components.select_related("metadata").all():
        metadata = getattr(component, "metadata", None)
        if not metadata or metadata.type != "C":
            continue

        name = _normalize_text(metadata.name)
        if "admin ward" in name:
            return component

    return None


def _get_ward_children(slum):
    ward_component = _find_admin_ward_component(slum)
    if not ward_component or not getattr(ward_component, "metadata", None):
        return []

    ward_metadata = ward_component.metadata
    return list(slum.components.filter(metadata=ward_metadata).order_by("housenumber"))


def _get_ward_wise_data(slum, ward_children=None):
    """
    Return ward_id -> list of household numbers for a slum.

    The ward ids come from the Admin Ward component children, while the
    household grouping comes from HouseholdData JSON (`Select Ward`).

    `ward_children` may be passed in by a caller that already computed it
    (e.g. to share it with `_get_ward_road_lengths`) to avoid re-running the
    admin-ward lookup, which scans every component on the slum.
    """
    if ward_children is None:
        ward_children = _get_ward_children(slum)
    if not ward_children:
        return OrderedDict()

    ward_map = OrderedDict()
    ward_alias_map = {}
    ward_seen = {}

    for ward in ward_children:
        ward_id = str(ward.housenumber)
        ward_map[ward_id] = []
        ward_seen[ward_id] = set()
        ward_alias_map[_normalize_text(ward_id)] = ward_id

        # Be tolerant if the JSON stores the same label in a slightly different form.
        ward_label = (
            getattr(getattr(ward, "shape", None), "properties", {}).get("name")
            if getattr(ward, "shape", None)
            else ""
        )
        if ward_label:
            ward_alias_map[_normalize_text(ward_label)] = ward_id

    only_fields = ["household_number"] + _HOUSEHOLD_JSON_FIELDS
    household_rows = HouseholdData.objects.filter(slum=slum).only(*only_fields)

    for household in household_rows.iterator():
        payload = _get_household_json(household)
        ward_value = _get_select_ward_value(payload)
        if not ward_value:
            continue

        ward_id = ward_alias_map.get(_normalize_text(ward_value))
        if not ward_id:
            continue

        household_number = _base_household_number(household.household_number)
        if not household_number or household_number in ward_seen[ward_id]:
            continue

        ward_seen[ward_id].add(household_number)
        ward_map[ward_id].append(household_number)

    return ward_map


def _get_ward_road_lengths(slum, ward_children=None):
    """
    Return ward_id -> {line_component_name: length_in_metres} for a slum,
    covering every component type whose geometry is a line (roads, drainage,
    railway lines, pipelines, etc. — see `_get_line_only_metadata_names`).

    Length per ward is computed by intersecting each line with the ward
    boundary polygon and summing the intersected length, in a metric
    projection (EPSG:3857), via PostGIS (ST_Intersection + ST_Length) rather
    than in Python — this is the same "clip to ward boundary, then measure"
    approach used for whole-slum totals in graphs/analyse_data.py, just
    scoped to each ward's polygon.

    `ward_children` may be passed in by a caller that already computed it
    (e.g. alongside `_get_ward_wise_data`) to avoid re-running the admin-ward
    lookup, which scans every component on the slum.
    """
    if ward_children is None:
        ward_children = _get_ward_children(slum)
    if not ward_children:
        return OrderedDict()

    line_metadata_names = _get_line_only_metadata_names(slum)
    if not line_metadata_names:
        return OrderedDict((str(ward.housenumber), {}) for ward in ward_children)

    road_map = OrderedDict()
    for ward in ward_children:
        ward_id = str(ward.housenumber)
        ward_geom = Value(ward.shape, output_field=GeometryField())

        rows = (
            slum.components.filter(metadata__name__in=line_metadata_names)
            .annotate(
                clipped_length=Length(
                    Intersection(Transform("shape", 3857), Transform(ward_geom, 3857))
                )
            )
            .values("metadata__name")
            .annotate(total_length=Sum("clipped_length"))
        )

        road_map[ward_id] = {
            row["metadata__name"]: round(row["total_length"].m, 1)
            for row in rows
            if row["total_length"] is not None
        }

    return road_map
