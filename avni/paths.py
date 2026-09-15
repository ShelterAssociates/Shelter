"""Builders for the AVNI external API paths this project uses."""

from urllib.parse import quote


def list_path(endpoint, type_param, type_value, since, location_uuid=None):
    query = [("lastModifiedDateTime", since), (type_param, type_value)]
    if location_uuid:
        query.append(("locationIds", location_uuid))
    encoded = "&".join("{}={}".format(key, quote(str(value), safe="")) for key, value in query)
    return "{}?{}".format(endpoint, encoded)


def subjects(subject_type, since, location_uuid=None):
    return list_path("api/subjects", "subjectType", subject_type, since, location_uuid)


def encounters(encounter_type, since):
    return list_path("api/encounters", "encounterType", encounter_type, since)


def program_encounters(encounter_type, since):
    return list_path("api/programEncounters", "encounterType", encounter_type, since)


def subject(uuid):
    return "api/subject/" + uuid


def encounter(uuid):
    return "api/encounter/" + uuid


def program_encounter(uuid):
    return "api/programEncounter/" + uuid


def program_enrolment(uuid):
    return "api/programEnrolment/" + uuid
