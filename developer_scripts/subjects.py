"""One subject at a time, by uuid: read it, shift its household number, void it.

    from developer_scripts import subjects
    subjects.summary("efe784a4-aee9-48cc-8bc4-f3cdff50919c")
    subjects.rename_household("efe784a4-...", "0844")
    subjects.void_subject("efe784a4-...")

Both writes hit live AVNI straight away - there is no dry run.
"""

from avni import paths
from avni.client import client
from developer_scripts.payload import subject_put_body
from survey import identity


def fetch(subject_uuid, api=None):
    """The raw subject record from AVNI."""
    return (api or client()).get_json(paths.subject(subject_uuid))


def summary(subject_uuid, api=None):
    """Where the subject sits and which household number it carries."""
    record = fetch(subject_uuid, api)
    location = record.get("location") or {}
    observations = record.get("observations") or {}
    return {
        "city": location.get("City"),
        "slum": location.get("Slum"),
        "household_number": identity.household_number_from(observations.get("First name")),
        "last_modified": (record.get("audit") or {}).get("Last modified at"),
        "voided": bool(record.get("Voided")),
    }


def rename_household(subject_uuid, new_household_number, api=None):
    """Shift a household's number, which AVNI keeps in 'First name'.

    Does not check whether another household in the slum already uses the new
    number - confirm that first. Keep the zero padding the sheet uses ("0844").
    """
    api = api or client()
    body = subject_put_body(fetch(subject_uuid, api))
    old_number = body.get("First name")
    body["First name"] = new_household_number
    label = "{} -> {}".format(old_number, new_household_number)
    return write(api, subject_uuid, body, "RENAME", label)


def void_subject(subject_uuid, api=None):
    """Void one subject, leaving the rest of the record as it is."""
    api = api or client()
    body = subject_put_body(fetch(subject_uuid, api), Voided=True)
    return write(api, subject_uuid, body, "VOID", "voided")


def write(api, subject_uuid, body, tag, label):
    response = api.put(paths.subject(subject_uuid), body)
    if response.status_code != 200:
        print("[{}] {} {} FAILED: {} {}".format(tag, subject_uuid, label, response.status_code, response.text[:300]))
        return False
    print("[{}] {} {}".format(tag, subject_uuid, label))
    return True
