"""Resolving a household's photos from whichever system captured them.

Photos come from two eras and two entirely different places:

* **Kobo** (the majority -- ~17,766 households). Surveys ran on KoboToolbox
  before Avni. Those factsheet photos were backed up onto this server and are
  plain local files, so reading them needs no API call, no signing and no
  throttling. Only two photo types exist for this era: family and toilet.
* **Avni** (~5,792 households). Photos are raw S3 object URLs held in encounter
  observations, which must be exchanged for short-lived pre-signed URLs before
  they can be fetched. Six photo types exist, including the agreement photos on
  Daily Reporting encounters.

A household is one or the other, never both, decided by `household_source()`.

Both eras are normalised into the same "groups -> encounters -> photos" shape so
templates and the exporter don't need to care which one they're looking at.
"""

import logging
import os

from django.conf import settings
from django.urls import reverse

from avni import media as avni_media

logger = logging.getLogger(__name__)

SOURCE_KOBO = "kobo"
SOURCE_AVNI = "avni"
SOURCE_NONE = "none"

# Kobo-era ff_data keys, mapped to the label shown in the UI and used as the
# folder name inside an export zip. Deliberately matched to the Avni labels
# ("Family Photo", not "Family_Photo") so a mixed export has consistent folders.
KOBO_PHOTO_KEYS = (
    ("Family Photo", "Family_Photo"),
    ("Toilet Photo", "Toilet_Photo"),
)

# Where the Kobo backup lives, relative to MEDIA_ROOT. The _attachments
# filenames already start with this prefix.
KOBO_ATTACHMENT_ROOT = "shelter/attachments"


def household_source(ff_data, rhs_data=None):
    """Which system holds this household's photos.

    The rhs_data check is essential, not a nicety: a household can have Daily
    Reporting agreement photos in Avni while having NO factsheet at all (empty
    ff_data). Deciding on ff_data alone would classify those as "nothing to
    show" and never ask Avni -- silently hiding exactly the households with
    agreement photos. rhs_data["rhs_uuid"] is the subject UUID, which is what
    actually makes an Avni lookup possible.
    """
    ff_data = ff_data or {}
    if ff_data.get("_attachments"):
        return SOURCE_KOBO
    if ff_data.get("ff_uuid"):
        return SOURCE_AVNI
    if (rhs_data or {}).get("rhs_uuid"):
        return SOURCE_AVNI
    return SOURCE_NONE


def _attachment_dir(ff_data, photo_name):
    """Directory (relative to MEDIA_ROOT) holding one Kobo photo.

    Attachment filenames look like
    `shelter/attachments/<xform_hash>/<instance_uuid>/1601359565209.jpg`, while
    ff_data["Family_Photo"] holds just the basename.

    Prefer the attachment whose basename actually matches the photo we want,
    and fall back to the first attachment's directory. Sampling showed every
    attachment of a household sharing one directory, so the fallback matches
    the long-standing behaviour in mastersheet.views -- but matching by name
    costs nothing and won't mispair if that ever stops being true.
    """
    attachments = ff_data.get("_attachments") or []
    for attachment in attachments:
        filename = str(attachment.get("filename") or "")
        if filename and os.path.basename(filename) == photo_name:
            return os.path.dirname(filename)
    for attachment in attachments:
        filename = str(attachment.get("filename") or "")
        if filename:
            return os.path.dirname(filename)
    return None


def kobo_photos(ff_data):
    """[{label, relative_path, abs_path, url, exists}] for a Kobo household.

    `exists` is checked here because the backup lives on the production server
    only -- it is absent from dev checkouts -- so callers must be able to show
    or record a missing photo rather than crashing on it.
    """
    ff_data = ff_data or {}
    photos = []
    for label, key in KOBO_PHOTO_KEYS:
        photo_name = ff_data.get(key)
        if not photo_name or not str(photo_name).strip():
            continue
        photo_name = str(photo_name).strip()
        directory = _attachment_dir(ff_data, photo_name)
        if not directory:
            continue
        relative_path = "{}/{}".format(directory.rstrip("/"), photo_name)
        abs_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        photos.append(
            {
                "label": label,
                "relative_path": relative_path,
                "abs_path": abs_path,
                # Deliberately NOT settings.MEDIA_URL: nginx denies that path
                # now, so photos are reachable only through the authenticated
                # photos:protected_media view.
                "url": reverse("photos:protected_media", args=[relative_path]),
                "exists": os.path.exists(abs_path),
            }
        )
    return photos


def kobo_groups(record):
    """Kobo photos shaped like avni_media.resolve_subject_programs' output, so
    the same template partial and the same exporter code handle both eras."""
    photos = kobo_photos(record.ff_data)
    if not photos:
        return []
    encounter = {
        "uuid": None,
        "encounter_type": "Family factsheet",
        "encounter_date": (
            record.submission_date.isoformat() if record.submission_date else None
        ),
        "program": None,
        "subject_uuid": None,
        "enrolment_uuid": None,
        "avni_url": None,
        "photos": [
            {
                "label": photo["label"],
                "url": photo["url"],
                # Kobo photos are served by our own view, so the thumbnail URL
                # is already permanent -- nothing to re-sign.
                "link_url": photo["url"],
                "raw_url": photo["relative_path"],
                "abs_path": photo["abs_path"],
                "exists": photo["exists"],
                "source": SOURCE_KOBO,
            }
            for photo in photos
        ],
    }
    return [
        {
            "program": "Family factsheet (KoboToolbox)",
            "enrolment_uuid": None,
            "enrolment_date": None,
            "exit_date": None,
            "encounters": [encounter],
            "photo_count": len(photos),
            "source": SOURCE_KOBO,
        }
    ]


def avni_groups(subject_uuid, include_direct_encounters=False, sign=False):
    """Avni photos. Returns None when the subject can't be read (so callers can
    tell 'lookup failed' from 'genuinely has nothing')."""
    groups = avni_media.resolve_subject_programs(
        subject_uuid, include_direct_encounters=include_direct_encounters, sign=sign
    )
    if groups is None:
        return None
    from photos.views import avni_photo_url

    for group in groups:
        group["source"] = SOURCE_AVNI
        for encounter in group["encounters"]:
            for photo in encounter["photos"]:
                photo["source"] = SOURCE_AVNI
                photo["exists"] = True
                # `url` (the signed one) is fine for an <img src> that loads
                # straight away, but expires in 120s -- so the click-through
                # link re-signs instead.
                photo["link_url"] = avni_photo_url(photo.get("raw_url"))
    return groups


def all_photos(groups):
    """Flatten groups -> encounters -> photos into one list."""
    return [
        photo
        for group in (groups or [])
        for encounter in group["encounters"]
        for photo in encounter["photos"]
    ]
