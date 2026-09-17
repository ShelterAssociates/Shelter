"""Fixtures for the survey tests. Nothing here imports a provider app."""

from django.contrib.auth.models import User
from django.contrib.gis.geos import Polygon

from master.models import AdministrativeWard, City, CityReference, ElectoralWard, Slum
from survey import contracts

SQUARE = Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))


def make_city(name="Thane"):
    user, _ = User.objects.get_or_create(username="fixture", defaults={"is_staff": True})
    reference = CityReference.objects.create(
        city_name=name, city_code=name[:3].upper(), district_name="D", district_code="D",
        state_name="MH", state_code="MH",
    )
    return City.objects.create(
        name=reference, city_code=reference.city_code, state_name="MH", state_code="MH",
        district_name="D", district_code="D", shape=SQUARE, created_by=user,
    )


def make_slum(city, name="Lokmanya Nagar", code="LN1"):
    admin_ward = AdministrativeWard.objects.create(city=city, name=name + " admin", shape=SQUARE)
    electoral_ward = ElectoralWard.objects.create(
        administrative_ward=admin_ward, name=name + " ward", shape=SQUARE
    )
    return Slum.objects.create(electoral_ward=electoral_ward, name=name, shape=SQUARE, shelter_slum_code=code)


def ref(name, data_type="text", external_id=""):
    return contracts.ConceptRef(external_id=external_id, name=name, data_type=data_type)


def observation(name, value, data_type="text", group=None, repeat_index=0, position=0, answer_name=""):
    return contracts.Observation(
        question=ref(name, data_type), value=value, group=group,
        repeat_index=repeat_index, position=position, answer_name=answer_name,
    )


def normalized(kind="subject", external_id="sub-1", **overrides):
    fields = {
        "kind": kind,
        "external_id": external_id,
        "subject_external_id": overrides.pop("subject_external_id", external_id),
        "subject_type": "Household",
        "slum_name": "Lokmanya Nagar",
        "city_name": "Thane",
        "household_number": "42",
        "record_datetime": "2026-09-01T06:47:34.548Z",
        "last_modified_at": "2026-09-01T06:47:34.548Z",
        "created_at": "2021-08-17T04:37:33.023Z",
        "observations": (),
    }
    fields.update(overrides)
    return contracts.NormalizedRecord(**fields)
