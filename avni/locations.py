"""Slum lookups shared by the sync modules: the AVNI view of survey.SlumAlias."""

import os

from survey.locations import slum_and_city_ids, slum_external_id, slum_id_for_external_id, slum_ids_for  # noqa: F401

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PROVIDER = "avni"


def data_file(name):
    return os.path.join(DATA_DIR, name)


def slum_location_uuid(slum_id):
    """AVNI location uuid for a Slum id, or None when the slum is not mapped."""
    return slum_external_id(PROVIDER, slum_id)


def mapped_slum_ids():
    return slum_ids_for(PROVIDER)


def slum_id_for_location_uuid(location_uuid):
    """Slum id for an AVNI location uuid, or None when no slum is mapped to it.

    Used by the mobile map endpoints (component/avni_map.py), which only know
    the AddressLevel uuid the Avni client synced.
    """
    return slum_id_for_external_id(PROVIDER, location_uuid)
