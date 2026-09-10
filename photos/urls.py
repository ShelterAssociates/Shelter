from django.conf.urls import url

from photos.views import (
    photo_encounter,
    photo_redirect,
    photo_sign,
    protected_media,
    photo_export_download,
    photo_export_list,
    photo_export_submit,
    photo_household,
    photo_household_download,
    photo_index,
    photo_slum,
)

app_name = "photos"

HOUSEHOLD_RE = r"(?P<household_number>[0-9]{1,4}[A-Za-z]?)"

urlpatterns = [
    url(r"^$", photo_index, name="photo_index"),
    url(r"^slum/(?P<slum_id>[0-9]+)/$", photo_slum, name="photo_slum"),
    url(
        r"^slum/(?P<slum_id>[0-9]+)/household/" + HOUSEHOLD_RE + r"/$",
        photo_household,
        name="photo_household",
    ),
    url(
        r"^slum/(?P<slum_id>[0-9]+)/household/" + HOUSEHOLD_RE + r"/download/$",
        photo_household_download,
        name="photo_household_download",
    ),
    url(
        r"^slum/(?P<slum_id>[0-9]+)/export/$",
        photo_export_submit,
        name="photo_export_submit",
    ),
    url(r"^exports/$", photo_export_list, name="photo_export_list"),
    url(
        r"^exports/(?P<export_id>[0-9]+)/download/$",
        photo_export_download,
        name="photo_export_download",
    ),
    url(r"^encounter/$", photo_encounter, name="photo_encounter"),
    # Re-signs an Avni photo URL at click time (Avni signatures last 120s).
    url(r"^photo/$", photo_redirect, name="photo_redirect"),
    # Signs one photo for the browser, so thumbnails load after first paint.
    url(r"^sign/$", photo_sign, name="photo_sign"),
    # Authenticated access to the Kobo photo backup. nginx denies the raw
    # /media/shelter/attachments/ path, so this is the only way in.
    url(
        r"^file/(?P<relative_path>shelter/attachments/[^\s]+)$",
        protected_media,
        name="protected_media",
    ),
]
