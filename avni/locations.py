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


def slum_and_city_ids(slum_name):
    from master.models import Slum

    row = Slum.objects.filter(name=slum_name).values_list(
        "id", "electoral_ward_id__administrative_ward__city__id"
    ).first()
    if row is None:
        raise LookupError("No slum named '{}'".format(slum_name))
    return row[0], row[1]
