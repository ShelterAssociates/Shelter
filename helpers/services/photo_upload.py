from helpers.models import *
from datetime import date, datetime

VALID_PROJECT_TYPES = {"OHOT", "MHM", "Housing", "Other"}


def normalize_upload_scope(is_city_level, is_other_upload, city_id, slum_id, custom_folder_name):
    """Infers is_city_level / is_other_upload when the client didn't send them explicitly."""
    if not is_city_level and city_id and not slum_id and not custom_folder_name:
        is_city_level = True
    if not is_other_upload and custom_folder_name and not slum_id and not city_id:
        is_other_upload = True
    return is_city_level, is_other_upload


def collect_uploaded_photos(request_files):
    """Reads photos from either the multi-file 'photos' field or the single 'photo' field."""
    uploaded_files = request_files.getlist("photos")
    if not uploaded_files:
        single_file = request_files.get("photo")
        uploaded_files = [single_file] if single_file else []
    return uploaded_files


def validate_photo_date(photo_date):
    """Returns (parsed_date, error_message). error_message is None on success."""
    if not photo_date:
        return None, "Photo date is required."
    try:
        selected_photo_date = datetime.strptime(photo_date, "%Y-%m-%d").date()
    except ValueError:
        return None, "Photo date must be in YYYY-MM-DD format."
    if selected_photo_date > date.today():
        return None, "Photo date cannot be in the future."
    return selected_photo_date, None


def validate_project_type(project_type, project_type_other):
    """Returns (normalized_project_type_other, error_message)."""
    if not project_type:
        return project_type_other, "Project type is required."
    if project_type not in VALID_PROJECT_TYPES:
        return project_type_other, "Please select a valid project type."
    if project_type == "Other" and not project_type_other:
        return project_type_other, "Specify Project Type is required when Project Type is Other."
    return (project_type_other if project_type == "Other" else ""), None


def resolve_photo_type_item(photo_type_item_id, is_city_level, city_id):
    """Returns (photo_type_item, error_message) for the non-'other upload' path."""
    if not photo_type_item_id:
        return None, "Photo type is required."
    photo_type_item = PhotoTypeItem.objects.filter(id=photo_type_item_id, is_visible=True).select_related("parent").first()
    if not photo_type_item:
        return None, "Please select a valid visible category."
    if photo_type_item.has_visible_children():
        return None, "Please choose the most specific sub-category."
    if is_city_level and not city_id:
        return None, "City is required for city level upload."
    return photo_type_item, None


def resolve_sponsor_config(sponsor_config_id):
    """Looks up a SponsorPhotoConfig by id. Returns None if not provided or not found."""
    if not sponsor_config_id:
        return None
    return SponsorPhotoConfig.objects.select_related("sponsor").filter(id=sponsor_config_id).first()


def save_slum_photos(upload_batch, drive_files):
    """Creates SlumPhoto rows from the drive upload result and returns the API-facing file list."""
    files_response = []
    for file_info in drive_files:
        web_view_link = file_info.get("web_view_link") or file_info.get("webViewLink") or ""
        web_content_link = file_info.get("web_content_link") or file_info.get("webContentLink") or ""
        drive_file_id = file_info.get("drive_file_id") or file_info.get("driveFileId") or ""

        SlumPhoto.objects.create(
            upload_batch=upload_batch,
            file_name=file_info.get("name", ""),
            web_view_link=web_view_link,
            web_content_link=web_content_link,
            drive_file_id=drive_file_id,
            size_bytes=file_info.get("size"),
            content_type=file_info.get("content_type", ""),
        )
        files_response.append({
            "name": file_info.get("name", ""),
            "web_view_link": web_view_link,
            "web_content_link": web_content_link,
            "drive_file_id": drive_file_id,
            "webViewLink": web_view_link,
            "webContentLink": web_content_link,
            "driveFileId": drive_file_id,
        })
    return files_response