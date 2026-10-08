"""Slum lookups shared by the sync modules: the AVNI view of survey.SlumAlias."""

import os

from survey.locations import (  # noqa: F401
    slum_and_city_ids,
    slum_external_id,
    slum_external_ids,
    slum_id_for_external_id,
    slum_id_for_name,
    slum_id_for_title,
    slum_ids_for,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PROVIDER = "avni"


def data_file(name):
    return os.path.join(DATA_DIR, name)


def slum_location_uuid(slum_id):
    """Primary AVNI location uuid for a Slum id, or None when the slum is not mapped.

    A re-surveyed slum has more than one location; the primary one is what the
    slum-level syncs (RIM, toilets) read.
    """
    return slum_external_id(PROVIDER, slum_id)


def slum_location_uuids(slum_id):
    """Every AVNI location uuid mapped to a Slum id, primary first."""
    return slum_external_ids(PROVIDER, slum_id)


def slum_id_for_location_title(title):
    """Slum id of the alias carrying this AVNI location title, or None."""
    return slum_id_for_title(title, PROVIDER)


def mapped_slum_ids():
    return slum_ids_for(PROVIDER)


def slum_id_for_location_uuid(location_uuid):
    """Slum id for an AVNI location uuid, or None when no slum is mapped to it.

    Used by the mobile map endpoints (component/avni_map.py), which only know
    the AddressLevel uuid the Avni client synced.
    """
    return slum_id_for_external_id(PROVIDER, location_uuid)
