from collections import OrderedDict

from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.db.models.functions import (
    Intersection,
    Length,
    PointOnSurface,
    Transform,
)
from django.db.models import Case, CharField, Count, Func, IntegerField, Sum, Value, When

from component.models import Metadata
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


def _get_ward_children(slum):
    """
    Return this slum's Admin Ward component children, ordered by ward number.

    The Metadata table is small and global (not per-slum), and the admin-ward
    row is uniquely identifiable by name, so we look it up directly instead
    of scanning every component on the slum (which used to pull full
    geometry for every row just to find the one metadata match).
    """
    ward_metadata = Metadata.objects.filter(
        type="C", name__icontains="admin ward"
    ).first()
    if not ward_metadata:
        return []

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


# Component types that represent one polygon per household (plot boundary
# outlines), as opposed to independently digitised/KML-uploaded map features
# (handpumps, poles, garbage bins, etc.). For these, ward assignment must
# come from the same authority as household ward assignment — the RHS
# survey's "Select Ward" field, matched by household number — not from
# where the digitized outline happens to sit relative to a ward boundary
# polygon. A household's survey ward and its plot polygon are collected
# independently, so a plot near a boundary can be drawn slightly across it
# even though the survey unambiguously assigned the household to one ward.
_HOUSEHOLD_LINKED_COMPONENT_NAMES = {"Structure", "Other Structures"}


def _fetch_countable_components(slum, line_metadata_names):
    """
    Non-line "C"-type components for this slum (structures, handpumps, water
    tanks, garbage bins, etc. — anything a ward count makes sense for), each
    annotated with a representative point (`rep_point`) used, for the
    non-household-linked ones, to test which ward polygon contains it.

    Deliberately `PointOnSurface`, not `Centroid`: a centroid is only
    guaranteed to fall inside convex shapes, and a concave polygon's
    centroid can fall outside it entirely, occasionally landing in a
    neighbouring ward across a shared boundary. `PointOnSurface` is
    guaranteed to lie within the geometry — for a Point it's that point, so
    this still works uniformly across Point/Polygon/MultiPolygon.

    Line features (roads, drainage, etc.) are excluded — "which ward
    contains this line" isn't a meaningful question, they're covered by
    `_get_ward_road_lengths` instead.
    """
    return list(
        slum.components.filter(metadata__type="C")
        .exclude(metadata__name__in=line_metadata_names)
        .select_related("metadata")
        .annotate(rep_point=PointOnSurface("shape"))
    )


def _split_household_linked_components(components):
    """Partition components into (household-linked, spatially-assigned)."""
    household_linked = []
    spatial_candidates = []
    for component in components:
        if component.metadata.name in _HOUSEHOLD_LINKED_COMPONENT_NAMES:
            household_linked.append(component)
        else:
            spatial_candidates.append(component)
    return household_linked, spatial_candidates


def _build_household_to_ward_map(ward_data):
    """
    Invert ward_data (ward_id -> [household_number, ...], as returned by
    `_get_ward_wise_data`) into household_number -> ward_id, so
    household-linked components can look their ward up directly.
    """
    household_to_ward = {}
    for ward_id, household_numbers in ward_data.items():
        for household_number in household_numbers:
            household_to_ward[household_number] = ward_id
    return household_to_ward


def _record_component(ward_map, ward_id, component):
    ward_map[ward_id].setdefault(component.metadata.name, []).append(
        component.housenumber
    )


def _assign_by_household_ward(ward_map, components, household_to_ward):
    """
    Assign household-linked components (see `_HOUSEHOLD_LINKED_COMPONENT_NAMES`)
    to a ward via their household's surveyed "Select Ward" value.

    Returns the components that couldn't be matched this way (no household
    with that number, or no Select Ward value recorded for it), so the
    caller can fall back to spatial containment for just those instead of
    dropping them.
    """
    unassigned = []
    for component in components:
        household_number = _base_household_number(component.housenumber)
        ward_id = household_to_ward.get(household_number)
        if ward_id is None or ward_id not in ward_map:
            unassigned.append(component)
            continue

        _record_component(ward_map, ward_id, component)

    return unassigned


def _assign_by_spatial_containment(ward_map, components, ward_children):
    """
    Assign each component to the ward whose polygon contains its
    representative point, using GEOS spatial predicates on geometry already
    materialised in Python (the same GEOS engine PostGIS's ST_Contains uses
    under the hood, so this agrees with the database rather than a
    hand-written point-in-polygon check).

    Returns the components whose point didn't fall strictly inside any ward
    polygon, typically because it sits almost exactly on a shared boundary
    between two wards — the caller falls back to nearest-ward for those.
    """
    unmatched = []
    for component in components:
        rep_point = component.rep_point
        if rep_point is None:
            unmatched.append(component)
            continue

        matched_ward = next(
            (ward for ward in ward_children if ward.shape.contains(rep_point)),
            None,
        )
        if matched_ward is None:
            unmatched.append(component)
            continue

        _record_component(ward_map, str(matched_ward.housenumber), component)

    return unmatched


def _assign_orphans_to_nearest_ward(ward_map, unmatched, ward_children):
    """
    Fallback for components that didn't land strictly inside any ward
    polygon (see `_assign_by_spatial_containment`) — assigns each to
    whichever ward polygon is closest, so a boundary-hugging point still
    counts toward exactly one ward instead of none.
    """
    for component in unmatched:
        rep_point = component.rep_point
        if rep_point is None:
            continue

        nearest_ward = min(
            ward_children, key=lambda ward: ward.shape.distance(rep_point)
        )
        _record_component(ward_map, str(nearest_ward.housenumber), component)


def _get_ward_component_counts(slum, ward_children=None, ward_data=None):
    """
    Return ward_id -> {metadata_name: [housenumber, ...]} for every
    non-line "C"-type component in this slum.

    Plot-boundary components (`_HOUSEHOLD_LINKED_COMPONENT_NAMES`) are
    assigned via their household's surveyed ward; every other component
    (independently digitised/KML-uploaded map features) is assigned via
    spatial containment against the ward boundary polygons, using the same
    GEOS predicates PostGIS itself uses — replacing the old client-side
    approach of computing each feature's centroid and testing it with a
    hand-written ray-casting algorithm in JS.

    `ward_children` and `ward_data` may be passed in by a caller that
    already computed them (e.g. alongside `_get_ward_wise_data`) to avoid
    redoing that work.
    """
    if ward_children is None:
        ward_children = _get_ward_children(slum)
    if not ward_children:
        return OrderedDict()

    if ward_data is None:
        ward_data = _get_ward_wise_data(slum, ward_children=ward_children)
    household_to_ward = _build_household_to_ward_map(ward_data)

    line_metadata_names = _get_line_only_metadata_names(slum)
    components = _fetch_countable_components(slum, line_metadata_names)
    household_linked, spatial_candidates = _split_household_linked_components(
        components
    )

    ward_map = OrderedDict((str(ward.housenumber), {}) for ward in ward_children)

    unassigned = _assign_by_household_ward(
        ward_map, household_linked, household_to_ward
    )
    spatial_candidates.extend(unassigned)

    unmatched = _assign_by_spatial_containment(
        ward_map, spatial_candidates, ward_children
    )
    _assign_orphans_to_nearest_ward(ward_map, unmatched, ward_children)

    return ward_map
