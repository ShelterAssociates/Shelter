"""The body shape AVNI's PUT api/subject/<uuid> expects.

A GET gives back a `location` dict and keeps the household number in
observations; a PUT wants a flat `Address` string and the household number as a
top-level `First name`. Sending a GET body back unchanged loses the address and
the household number, so every subject write goes through subject_put_body().
"""


def subject_put_body(fetched, **top_level):
    """A PUT body built from a fetched subject, with any top-level edits applied.

    subject_put_body(record, Voided=True) voids it; the rest of the record is
    re-sent as it came back.
    """
    body = dict(fetched)
    observations = dict(body.get("observations") or {})
    body["Address"] = address_of(body.pop("location", None) or {})
    if "First name" in observations:
        body["First name"] = observations.pop("First name")
    observations.pop("Last name", None)
    body["observations"] = observations
    body.update(top_level)
    return body


def address_of(location):
    """'City, Admin, Ward, Slum', skipping the levels this location does not have."""
    levels = (location.get("City"), location.get("Admin"), location.get("Ward"), location.get("Slum"))
    return ", ".join(level for level in levels if level)
