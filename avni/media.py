"""Read-only helpers for reading Avni program encounters and turning the raw S3
photo URLs stored in their observations into short-lived pre-signed URLs.

Avni's domain model is:

    Subject (= the household)
      ProgramEnrolment
        ProgramEncounter   ("Family factsheet", "Daily Reporting")

Program encounters hang off the *enrolment*, not the subject -- there is no
subject filter on /api/programEncounters. The way to get a household's
encounters is therefore:

    api/subject/<uuid>  ->  ["enrolments"] = [enrolmentUuid, ...]
      api/programEncounters?programEnrolmentId=<enrolmentUuid>

(/api/programEnrolments is not usable here: it returns 400 unless BOTH `subject`
and `program` are supplied, so you cannot filter by subject without already
knowing the program name.)

Photos in observations are raw S3 object URLs and are not publicly fetchable.
They must be exchanged for a pre-signed URL via media/signedUrl.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import quote

import requests
from django.conf import settings

from avni import mappings
from avni.client import client
from avni.locations import slum_location_uuid

logger = logging.getLogger(__name__)

# /api/programEncounters requires lastModifiedDateTime, so send a date old
# enough to mean "everything" (the nightly watermark would hide older encounters).
EPOCH_LMDT = "1900-01-01T00:00:00.000Z"

REQUEST_TIMEOUT_SECONDS = 15
SIGNING_TIMEOUT_SECONDS = 10
SIGNING_MAX_WORKERS = 6
# Parallel Avni reads when resolving one subject's encounters.
FETCH_MAX_WORKERS = 6

# Safety valve so a bad totalPages can never spin forever.
MAX_PAGES = 50

# Avni stores photo answers as raw S3 object URLs. There is no reliable list of
# which concepts are photos -- the agreement photo's concept name appears
# nowhere in this codebase -- so photos are detected by what the value looks
# like rather than by the key it happens to be stored under. That way any photo
# concept added to an Avni form later shows up without a code change here.
MEDIA_URL_RE = re.compile(
    r"^https?://\S*amazonaws\.com/\S+$"
    r"|^https?://\S+\.(?:jpg|jpeg|png|gif|webp|heic|heif)(?:\?\S*)?$",
    re.IGNORECASE,
)

# Households are registered under one of these subject types. "Household" and
# "Structure" come from create_registrationdata_url in avni/watermark.py;
# "Detailed Socio Economic Survey" is a third one used in some cities -- it has
# the same shape (observations["First name"] is the household number, with
# location.Slum / location.City), so the fallback subject search must cover it
# or those households can't be resolved at all.
#
# DSES carries NO photos of its own today (verified against live data), so it is
# listed here purely so those households can be resolved to a subject. If photo
# concepts are added to that form later, they will surface automatically via
# extract_photos' shape-based detection -- only PHOTO_TYPES below would need the
# new key adding for the export filter.
HOUSEHOLD_SUBJECT_TYPES = (
    "Household",
    "Structure",
    "Detailed Socio Economic Survey",
)

# The photo observation keys Avni actually uses, verified against live data.
# Drives the export filter checkboxes. Display still relies on extract_photos'
# shape-based detection, so a newly added photo concept shows on the household
# page even before it is listed here.
#
# The Kobo-era backup only ever has "Family Photo" and "Toilet Photo" -- see
# photos/services/sources.py.
PHOTO_TYPES = (
    ("Family Photo", "Family photo"),
    ("Toilet Photo", "Toilet photo"),
    ("Photo of Agreement", "Agreement photo"),
    ("Family Photo with Toilet (For SBM Uploads)", "Family photo with toilet (SBM)"),
    ("Photo of the Aadhar Card", "Aadhaar card photo"),
    ("ID size photo for SBM Upload", "ID size photo (SBM)"),
)
PHOTO_TYPE_KEYS = tuple(key for key, _label in PHOTO_TYPES)


def get_token():
    """Cached AVNI JWT shared with every other caller in the process."""
    return client().token()


def refresh_token():
    """Force a new JWT; used only when AVNI answers 401."""
    return client().refresh_token()


def utc_now():
    """Current UTC in Avni's ISO format.

    Newer avni-server builds mark `now` as a required parameter on the list
    endpoints, while the published external-api.yaml never mentions it and the
    sync code in this repo never sends it. Sending it is safe either way: a
    server that needs it is satisfied, and one that doesn't ignores the unknown
    query parameter.
    """
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")


def api_get(path, params=None, token=None):
    """GET an Avni API path and return parsed JSON, or None on any failure."""
    token = token or get_token()
    url = settings.AVNI_URL + path
    if params:
        url += "?" + "&".join(
            "{}={}".format(key, quote(str(value), safe=""))
            for key, value in params.items()
            if value is not None
        )
    try:
        response = requests.get(
            url, headers={"AUTH-TOKEN": token}, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        logger.error("Avni request failed for %s: %s", path, exc)
        return None
    if response.status_code != 200:
        logger.error("Avni returned %s for %s", response.status_code, path)
        return None
    try:
        return response.json()
    except ValueError:
        logger.error("Avni returned non-JSON for %s", path)
        return None


def fetch_subject(subject_uuid, token=None):
    """One subject. Its "enrolments" key is a list of enrolment UUIDs."""
    return api_get("api/subject/" + quote(str(subject_uuid), safe=""), token=token)


def fetch_program_encounter(encounter_uuid, token=None):
    """One program encounter. Carries "Subject ID" and "Enrolment ID", so a bare
    encounter UUID is enough to reach the rest of the household's data."""
    return api_get(
        "api/programEncounter/" + quote(str(encounter_uuid), safe=""), token=token
    )


def fetch_program_enrolment(enrolment_uuid, token=None):
    """One program enrolment. Carries "Program" (e.g. "Sanitation program"),
    "Enrolment datetime" and "Exit datetime" -- the context that explains why a
    household does or doesn't have Daily Reporting encounters."""
    return api_get(
        "api/programEnrolment/" + quote(str(enrolment_uuid), safe=""), token=token
    )


def fetch_encounter(encounter_uuid, token=None):
    """One direct (non-program) encounter -- Sanitation, Water, Waste,
    Electricity, Property tax. These hang off the subject rather than an
    enrolment, and the subject response lists their UUIDs directly.

    Fetched one at a time on purpose: /api/encounters?subjectId=... exists but
    times out against this server, whereas /api/encounter/<uuid> is instant.
    """
    return api_get(
        "api/encounter/" + quote(str(encounter_uuid), safe=""), token=token
    )


def fetch_encounters_for_enrolment(enrolment_uuid, encounter_type=None, token=None):
    """Every program encounter under one enrolment, following pagination."""
    token = token or get_token()
    encounters = []
    page = 0
    while page < MAX_PAGES:
        params = {
            "lastModifiedDateTime": EPOCH_LMDT,
            "now": utc_now(),
            "programEnrolmentId": enrolment_uuid,
            "page": page,
        }
        if encounter_type:
            params["encounterType"] = encounter_type
        payload = api_get("api/programEncounters", params=params, token=token)
        if not payload:
            break
        encounters.extend(payload.get("content") or [])
        page += 1
        if page >= (payload.get("totalPages") or 0):
            break
    return encounters


def find_subject_uuid(slum_id, household_number, token=None):
    """Locate a household's subject UUID through the API.

    Only needed when HouseholdData has no rhs_uuid for the household -- this is
    a paged scan of every subject in the slum, so it is the fallback, not the
    primary path.
    """
    location_uuid = slum_location_uuid(slum_id)
    if not location_uuid:
        return None

    token = token or get_token()
    target = mappings.household_number_from(household_number)

    for subject_type in HOUSEHOLD_SUBJECT_TYPES:
        page = 0
        while page < MAX_PAGES:
            payload = api_get(
                "api/subjects",
                params={
                    "lastModifiedDateTime": EPOCH_LMDT,
                    "now": utc_now(),
                    "subjectType": subject_type,
                    "locationIds": location_uuid,
                    "page": page,
                },
                token=token,
            )
            if not payload:
                break
            for record in payload.get("content") or []:
                observations = record.get("observations") or {}
                found = observations.get("First name")
                if found is None:
                    continue
                if mappings.household_number_from(found) == target:
                    return record.get("ID")
            page += 1
            if page >= (payload.get("totalPages") or 0):
                break
    return None


def extract_photos(observations):
    """[(label, raw S3 url), ...] for every media-looking value.

    A single observation can hold several photos -- "Photo of Agreement" on
    Daily Reporting is always a list -- so when one key yields more than one
    photo the label is numbered ("Photo of Agreement 1", "... 2") to keep the
    buttons on the page distinguishable.
    """
    photos = []
    for key, value in (observations or {}).items():
        candidates = value if isinstance(value, (list, tuple)) else [value]
        matched = [
            candidate.strip()
            for candidate in candidates
            if isinstance(candidate, str)
            and candidate.strip()
            and MEDIA_URL_RE.match(candidate.strip())
        ]
        if len(matched) == 1:
            photos.append((key, matched[0]))
        else:
            for index, candidate in enumerate(matched, start=1):
                photos.append(("{} {}".format(key, index), candidate))
    return photos


def sign_one(raw_url, token):
    """Exchange one raw S3 URL for a pre-signed one. The response body IS the
    signed URL (plain text, not JSON). Falls back to the raw URL so a signing
    failure degrades to a dead link rather than a broken page."""
    url = settings.AVNI_URL + "media/signedUrl?url=" + quote(raw_url, safe="")
    try:
        response = requests.get(
            url, headers={"AUTH-TOKEN": token}, timeout=SIGNING_TIMEOUT_SECONDS
        )
        if response.status_code == 401:
            response = requests.get(
                url,
                headers={"AUTH-TOKEN": refresh_token()},
                timeout=SIGNING_TIMEOUT_SECONDS,
            )
        if response.status_code != 200:
            logger.error("Signing returned %s for %s", response.status_code, raw_url)
            return raw_url, raw_url
        return raw_url, response.text.strip()
    except requests.RequestException as exc:
        logger.error("Signing failed for %s: %s", raw_url, exc)
        return raw_url, raw_url


def sign_urls(raw_urls):
    """{raw url: signed url} for many URLs, minting the token once."""
    unique = [url for url in dict.fromkeys(raw_urls) if url]
    if not unique:
        return {}
    token = get_token()
    signed = {}
    with ThreadPoolExecutor(max_workers=SIGNING_MAX_WORKERS) as executor:
        for raw, url in executor.map(lambda item: sign_one(item, token), unique):
            signed[raw] = url
    return signed


def encounter_avni_url(encounter_uuid):
    """Deep link into the Avni web app for one program encounter."""
    return "{}#/app/subject/viewProgramEncounter?uuid={}".format(
        settings.AVNI_URL, encounter_uuid
    )


def encounter_entry(encounter):
    """Flatten one raw API encounter into what the templates render."""
    return {
        "uuid": encounter.get("ID"),
        "encounter_type": encounter.get("Encounter type"),
        "encounter_date": encounter.get("Encounter date time"),
        "program": encounter.get("Program"),
        "subject_uuid": encounter.get("Subject ID"),
        "enrolment_uuid": encounter.get("Enrolment ID"),
        "avni_url": encounter_avni_url(encounter.get("ID")),
        "photos": [
            {"label": label, "raw_url": raw_url}
            for label, raw_url in extract_photos(encounter.get("observations"))
        ],
    }


def attach_signed_urls(entries, sign=True):
    """Attach a display URL to every photo.

    Signing costs one HTTP round trip to Avni per photo, which is the single
    slowest thing about rendering a household page -- and the signature only
    lasts 120 seconds anyway. So `sign=False` leaves `url` empty and lets the
    browser fetch each signed URL asynchronously (see photos.views.photo_sign),
    which renders the page immediately.

    The exporter always passes sign=False too: it signs in one batch inside
    write_photos_to_zip, so signing here as well was pure duplicated work.
    """
    if not sign:
        for entry in entries:
            for photo in entry["photos"]:
                photo["url"] = None
        return entries

    raw_urls = [
        photo["raw_url"] for entry in entries for photo in entry["photos"]
    ]
    signed = sign_urls(raw_urls)
    for entry in entries:
        for photo in entry["photos"]:
            photo["url"] = signed.get(photo["raw_url"], photo["raw_url"])
    return entries


def sorted_entries(entries):
    """Newest encounter first; undated ones last."""
    return sorted(entries, key=lambda e: (e["encounter_date"] or ""), reverse=True)


def resolve_subject_programs(subject_uuid, include_direct_encounters=False, sign=False):
    """A subject's enrolments, each with its encounters and signed photo URLs.

    Grouped by enrolment rather than returned flat because programme enrolment
    is what decides whether a household has photos at all: Family factsheet and
    Daily Reporting encounters only exist under a Sanitation program enrolment,
    and most households are enrolled in nothing. Showing the programme makes
    "no photos" explainable instead of just blank.

    Returns None when the subject cannot be read from Avni, so callers can tell
    "lookup failed" apart from "genuinely not enrolled" ([]).
    """
    token = get_token()
    subject = fetch_subject(subject_uuid, token=token)
    if subject is None:
        return None

    programs = []
    all_entries = []

    # Direct (non-program) encounters hang off the subject, not an enrolment.
    # Sampling found no photos on these, so bulk exports skip them by default;
    # the single-household view asks for them. Fetched in parallel because
    # serially they were over half the page's Avni time (4 calls x ~0.33s) for
    # data that is usually empty.
    if include_direct_encounters:
        direct = []
        encounter_uuids = list(subject.get("encounters") or [])
        if encounter_uuids:
            with ThreadPoolExecutor(
                max_workers=min(FETCH_MAX_WORKERS, len(encounter_uuids))
            ) as pool:
                fetched = pool.map(
                    lambda uuid: fetch_encounter(uuid, token=token), encounter_uuids
                )
            for encounter in fetched:
                if not encounter or encounter.get("Voided"):
                    continue
                entry = encounter_entry(encounter)
                if entry["photos"]:
                    direct.append(entry)
        if direct:
            all_entries.extend(direct)
            programs.append(
                {
                    "enrolment_uuid": None,
                    "program": "Other encounters",
                    "enrolment_date": None,
                    "exit_date": None,
                    "encounters": sorted_entries(direct),
                    "photo_count": sum(len(e["photos"]) for e in direct),
                }
            )

    for enrolment_uuid in subject.get("enrolments") or []:
        # The enrolment's own details and its encounters are independent
        # requests, so overlap them rather than paying for both in sequence.
        with ThreadPoolExecutor(max_workers=2) as pool:
            enrolment_future = pool.submit(
                fetch_program_enrolment, enrolment_uuid, token
            )
            encounters_future = pool.submit(
                fetch_encounters_for_enrolment, enrolment_uuid, None, token
            )
            enrolment = enrolment_future.result() or {}
            encounters = encounters_future.result()

        entries = []
        for encounter in encounters:
            if encounter.get("Voided"):
                continue
            entries.append(encounter_entry(encounter))
        all_entries.extend(entries)
        programs.append(
            {
                "enrolment_uuid": enrolment_uuid,
                "program": enrolment.get("Program"),
                "enrolment_date": enrolment.get("Enrolment datetime"),
                "exit_date": enrolment.get("Exit datetime"),
                "encounters": sorted_entries(entries),
                "photo_count": sum(len(e["photos"]) for e in entries),
            }
        )

    # Not signed by default -- the browser asks for each signed URL as it
    # renders, so the page is not held up by a round trip per photo.
    attach_signed_urls(all_entries, sign=sign)
    return programs


def resolve_encounter_photos(encounter_uuid, sign=False):
    """One program encounter looked up directly by UUID."""
    encounter = fetch_program_encounter(encounter_uuid)
    if encounter is None:
        return None
    entry = encounter_entry(encounter)
    attach_signed_urls([entry], sign=sign)
    return entry
