"""Fixtures shared by the avni tests: a city/slum chain and a scripted fake AVNI."""

import json

from django.contrib.auth.models import User
from django.contrib.gis.geos import Polygon

from avni.client import AvniError
from master.models import AdministrativeWard, City, CityReference, ElectoralWard, Slum

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
    electoral_ward = ElectoralWard.objects.create(administrative_ward=admin_ward, name=name + " ward", shape=SQUARE)
    return Slum.objects.create(electoral_ward=electoral_ward, name=name, shape=SQUARE, shelter_slum_code=code)


def subject_record(uuid="sub-1", slum="Lokmanya Nagar", city="Thane", number="0042", voided=False,
                   observations=None, modified="2026-09-01T06:47:34.548Z", registered="2018-03-20"):
    data = {"First name": number}
    data.update(observations or {})
    return {
        "ID": uuid,
        "Voided": voided,
        "Registration date": registered,
        "External ID": None,
        "location": {"Slum": slum, "City": city, "Admin": "A", "Ward": "W"},
        "observations": data,
        "audit": {"Created at": "2021-08-17T04:37:33.023Z", "Last modified at": modified},
        "enrolments": [],
        "encounters": [],
    }


def encounter_record(uuid="enc-1", encounter_type="Sanitation", subject_uuid="sub-1", voided=False,
                     observations=None, modified="2026-09-01T06:47:35.478Z"):
    return {
        "ID": uuid,
        "Voided": voided,
        "Encounter type": encounter_type,
        "Subject type": "Household",
        "Subject ID": subject_uuid,
        "Encounter date time": modified,
        "observations": observations if observations is not None else {"Date of Survey": "2026-09-01"},
        "cancelObservations": {},
        "audit": {"Created at": "2022-01-17T09:42:20.016Z", "Last modified at": modified},
    }


def program_encounter_record(uuid="penc-1", encounter_type="Daily Reporting", subject_uuid="sub-1",
                             voided=False, observations=None, modified="2026-09-01T07:38:14.398Z"):
    record = encounter_record(uuid, encounter_type, subject_uuid, voided, observations, modified)
    record.update({"Program": "Sanitation program", "Enrolment ID": "enr-1"})
    return record


def page(content, total_pages=1, page_size=20):
    return {"content": content, "totalPages": total_pages, "totalElements": len(content), "pageSize": page_size}


class FakeApi(object):
    """Scripted AVNI: `routes` maps a path (or path prefix before `&page=`) to a JSON body.

    A body may be a list of pages; page N is served for `&page=N`. Unknown paths
    raise AvniError(404). Every call is recorded in `calls`.
    """

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.calls = []
        self.writes = []

    def get_json(self, path, timeout=None):
        self.calls.append(path)
        base, page_number = split_page(path)
        body = self.routes.get(path, self.routes.get(base))
        if body is None:
            raise AvniError(404, path, "not found")
        if isinstance(body, Exception):
            raise body
        if isinstance(body, list):
            body = body[page_number]
        return json.loads(json.dumps(body))

    def iter_pages(self, path, timeout=None):
        first = self.get_json(path)
        yield first.get("content", [])
        for number in range(1, first.get("totalPages", 0)):
            yield self.get_json("{}&page={}".format(path, number)).get("content", [])

    def count(self, path, timeout=None):
        first = self.get_json(path)
        pages = first.get("totalPages", 0)
        size = first.get("pageSize") or len(first.get("content", []))
        if pages <= 1:
            return {"total": len(first.get("content", [])), "pages": pages, "page_size": size}
        last = self.get_json("{}&page={}".format(path, pages - 1))
        return {"total": (pages - 1) * size + len(last.get("content", [])), "pages": pages, "page_size": size}

    def put(self, path, body, timeout=None):
        self.writes.append(("PUT", path, body))
        return FakeResponse(200, body)

    def patch(self, path, body, timeout=None):
        self.writes.append(("PATCH", path, body))
        return FakeResponse(200, body)


class FakeResponse(object):
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        self.text = json.dumps(body)

    def json(self):
        return self.body


def split_page(path):
    if "&page=" not in path:
        return path, 0
    base, _, number = path.rpartition("&page=")
    return base, int(number)
