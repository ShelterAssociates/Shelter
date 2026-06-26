from django.conf.urls import include, url
from helpers.views import *

urlpatterns = [
    url(r"^digipin_generate/$", digipin_generate, name="digipin_generate"),
    url(r"^photo-upload/$", photo_upload_page, name="photo_upload_page"),
    url(r"^photo-types/$", photo_type_list, name="photo_type_list"),
    url(r"^events/$", event_list, name="event_list"),
    url(r"^sponsor-projects/$", sponsor_project_list, name="sponsor_project_list"),
    url(r"^photo-type-groups/$", photo_type_groups, name="photo_type_groups"),
    url(r"^photo-type-items/$", photo_type_items, name="photo_type_items"),
    # Superuser management
    url(
        r"^manage/photo-type-items/$",
        manage_photo_type_items,
        name="manage_photo_type_items",
    ),
    url(
        r"^manage/photo-type-items/toggle/$",
        manage_toggle_photo_type_item,
        name="manage_toggle_photo_type_item",
    ),
    url(
        r"^manage/photo-type-items/add/$",
        manage_add_photo_type_item,
        name="manage_add_photo_type_item",
    ),
    url(r"^api/send-otp/$", send_otp, name="send_otp"),
    url(r"^api/verify-otp/$", verify_otp, name="verify_otp"),
    url(
        r"^api/upload-slum-photos-to-drive/$",
        upload_slum_photos_to_drive,
        name="upload_slum_photos_to_drive",
    ),
    url(r"^confirm-reminder/", confirm_reminder, name="confirm_reminder"),
    url(r"^photo-type-tree/$", photo_type_tree, name="photo_type_tree"),
]
