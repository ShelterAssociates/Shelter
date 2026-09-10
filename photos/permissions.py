"""Two distinct access levels for the photos section.

Viewing and downloading are deliberately separated: a city-scoped user may look
at their own city's photos one at a time, but only a superuser may pull them out
in bulk. Bulk export can carry thousands of images, including Aadhaar card
photos, so it is held to a stricter bar than browsing.

Note this intentionally does NOT reuse mastersheet.rim_download_permissions.
can_access_rim_download, which also admits the GIS and Team Leader groups.
"""

from django.conf import settings


def can_view_photos(user):
    """Browse the photos section. Per-slum access is enforced separately by
    Slum.has_permission, so this only covers 'may use the section at all'."""
    return user.is_authenticated and user.has_perm(
        "mastersheet.can_view_mastersheet"
    )


def can_download_photos(user):
    """Download photos, singly or in bulk. Superuser only.

    PHOTO_DOWNLOAD_GROUPS exists so extra groups can be admitted later from
    settings without a code change; it defaults to empty, i.e. superuser only.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    extra_groups = getattr(settings, "PHOTO_DOWNLOAD_GROUPS", []) or []
    if not extra_groups:
        return False
    return user.groups.filter(name__in=extra_groups).exists()


def can_view_protected_media(user):
    """Who may fetch a Kobo-era photo through photos:protected_media.

    Deliberately wider than can_view_photos, because these files were
    previously served by nginx with no authentication at all and are linked
    from two places with different audiences:

      * the mastersheet grid, which requires mastersheet.can_view_mastersheet
      * the sponsor family-factsheet report (component.views.get_kobo_RHS_list),
        which admits superusers and the "sponsor" group

    Matching both keeps every legitimate user working while removing anonymous
    access, which is the actual goal. Narrowing this would silently break the
    sponsor report.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.has_perm("mastersheet.can_view_mastersheet"):
        return True
    return user.groups.filter(name="sponsor").exists()
