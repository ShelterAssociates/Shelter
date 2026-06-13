from collections import OrderedDict

from graphs.models import HouseholdData


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


def _get_ward_wise_data(slum):
    """
    Return ward_id -> list of household numbers for a slum.

    The ward ids come from the Admin Ward component children, while the
    household grouping comes from HouseholdData JSON (`Select Ward`).
    """
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
        ward_label = getattr(getattr(ward, "shape", None), "properties", {}).get("name") if getattr(ward, "shape", None) else ""
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
