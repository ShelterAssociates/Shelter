"""Gathering the photos an export or a page should show.

Turns a household (or a whole slum) into a flat list of entries:

    {"slum_name": ..., "household_number": ..., "photo": {...}}

which photos.services.export writes into a zip. Both photo eras are resolved
through photos.services.sources, so nothing downstream needs to know whether a
photo came from Avni or the Kobo backup.
"""

import logging

from graphs.models import HouseholdData
from avni import media as avni_media
from mastersheet.models import ToiletConstruction
from photos.services import sources
from photos.utils import (
    financial_year_range,
    household_number_variants,
    normalize_household_number,
)

logger = logging.getLogger(__name__)

# ff_data key holding the family factsheet name, as mapped by
# avni_sync.map_ff_keys. Used only as a label.
FAMILY_HEAD_KEY = "group_oh4zf84/Name_of_the_family_head"

# ToiletConstruction date columns offered by the financial-year filter.
FY_DATE_FIELDS = (
    ("completion_date", "Toilet completed"),
    ("agreement_date", "Agreement signed"),
    ("septic_tank_date", "Septic tank given"),
    ("phase_one_material_date", "Phase 1 material given"),
    ("phase_two_material_date", "Phase 2 material given"),
    ("phase_three_material_date", "Phase 3 material given"),
)
FY_DATE_FIELD_NAMES = {name for name, _label in FY_DATE_FIELDS}


def find_household(slum_id, lookup_number):
    """One HouseholdData row, tolerating inconsistent zero padding."""
    variants = household_number_variants(lookup_number)
    if not variants:
        return None
    return (
        HouseholdData.objects.filter(
            slum_id=slum_id, household_number__in=sorted(variants)
        )
        .order_by("household_number")
        .first()
    )


def household_groups(record, allow_avni=True, include_direct_encounters=False):
    """(groups, error) for one household, from whichever era captured it.

    `error` is set only when a lookup genuinely failed (Avni unreachable), not
    when a household simply has no photos.
    """
    ff_data = record.ff_data or {}
    source = sources.household_source(ff_data, record.rhs_data)

    if source == sources.SOURCE_KOBO:
        return sources.kobo_groups(record), None

    if source == sources.SOURCE_AVNI:
        if not allow_avni:
            return [], None
        subject_uuid = (record.rhs_data or {}).get("rhs_uuid")
        if not subject_uuid:
            subject_uuid = avni_media.find_subject_uuid(
                record.slum_id, normalize_household_number(record.household_number)
            )
        if not subject_uuid:
            return None, (
                "Could not work out which Avni subject this household is. It has "
                "no rhs_uuid recorded, and no matching subject was found in Avni "
                "for this slum."
            )
        groups = sources.avni_groups(
            subject_uuid, include_direct_encounters=include_direct_encounters
        )
        if groups is None:
            return None, (
                "Could not read this household from Avni. It may be temporarily "
                "unavailable -- try again shortly."
            )
        return groups, None

    return [], None


def photo_category(label):
    """'Photo of Agreement 2' -> 'Photo of Agreement', so numbered photos from
    one observation filter as a single type."""
    import re

    return re.sub(r"\s+\d+$", "", str(label or "")).strip()


def entries_from_groups(groups, slum_name, household_number, photo_types=None,
                        selected_labels=None):
    """Flatten to export entries, applying the photo-type filter."""
    entries = []
    for group in groups or []:
        for encounter in group.get("encounters") or []:
            for photo in encounter.get("photos") or []:
                label = photo.get("label")
                if photo_types and photo_category(label) not in photo_types:
                    continue
                if selected_labels is not None and label not in selected_labels:
                    continue
                entries.append(
                    {
                        "slum_name": slum_name,
                        "household_number": household_number,
                        "photo": photo,
                    }
                )
    return entries


def households_matching_financial_year(slum_id, date_field, fy_start_year):
    """Normalised household numbers whose construction date falls in that FY.

    Returns None when no FY filter is active, so callers can tell "no filter"
    from "filter matched nothing".
    """
    if not date_field or not fy_start_year:
        return None
    if date_field not in FY_DATE_FIELD_NAMES:
        raise ValueError("Unknown date field: {}".format(date_field))
    start, end = financial_year_range(fy_start_year)
    numbers = ToiletConstruction.objects.filter(
        slum_id=slum_id, **{"{}__range".format(date_field): (start, end)}
    ).values_list("household_number", flat=True)
    return {normalize_household_number(number) for number in numbers}


def slum_household_records(slum_id, household_numbers=None, date_field=None,
                          fy_start_year=None):
    """HouseholdData rows for a slum export, after the household and FY filters.

    Only households that actually have factsheet photo data are considered --
    a household with neither _attachments nor ff_uuid has nothing to export.
    """
    wanted = None
    if household_numbers:
        wanted = {normalize_household_number(n) for n in household_numbers}

    fy_numbers = households_matching_financial_year(
        slum_id, date_field, fy_start_year
    )
    if fy_numbers is not None:
        wanted = fy_numbers if wanted is None else (wanted & fy_numbers)

    queryset = HouseholdData.objects.filter(slum_id=slum_id)
    if wanted is not None:
        if not wanted:
            return []
        variants = set()
        for number in wanted:
            variants |= household_number_variants(number)
        queryset = queryset.filter(household_number__in=sorted(variants))

    records = []
    for record in queryset.order_by("household_number"):
        if sources.household_source(record.ff_data, record.rhs_data) != sources.SOURCE_NONE:
            records.append(record)
    return records


def estimate_slum_photo_count(records, photo_types=None):
    """Cheap local estimate for the disk precheck -- no Avni calls.

    Kobo households can be counted exactly (the filenames are in ff_data). Avni
    households are estimated, since knowing exactly would mean an API call per
    household, which is the thing the estimate exists to avoid.
    """
    avni_types = len(photo_types) if photo_types else 3
    count = 0
    for record in records:
        source = sources.household_source(record.ff_data, record.rhs_data)
        if source == sources.SOURCE_KOBO:
            count += len(sources.kobo_photos(record.ff_data))
        elif source == sources.SOURCE_AVNI:
            count += avni_types
    return count
