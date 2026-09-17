"""Slum lookups shared by the sync modules."""

import json
import os
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def data_file(name):
    return os.path.join(DATA_DIR, name)


@lru_cache(maxsize=1)
def slum_location_uuids():
    with open(data_file("slum_location_uuids.json")) as handle:
        return json.load(handle)


def slum_location_uuid(slum_id):
    """AVNI location uuid for a Slum id, or None when the slum is not mapped."""
    return slum_location_uuids().get(str(slum_id))


def mapped_slum_ids():
    return sorted(int(slum_id) for slum_id in slum_location_uuids())


# Generic (slum name -> ids), so it lives in the core; re-exported here because
# every sync module already imports it from avni.locations.
from survey.locations import slum_and_city_ids  # noqa: E402,F401 isort:skip
