"""The photo upload accepts real JPEG/PNG photos only, judged by content, not by name or Content-Type."""

import io
from datetime import date
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from PIL import Image

from helpers.services.google_drive import compress_uploaded_image
from utils.uploads import PHOTO_MAX_BYTES

URL = "/helpers/api/upload-slum-photos-to-drive/"
HTML = b"<html><script>alert('UPLOAD-TEST')</script></html>"


def image_bytes(fmt, size=(40, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, "green").save(buf, fmt)
    return buf.getvalue()


def photo(name, content, content_type="image/jpeg"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class PhotoUploadValidationTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user("staffer", password="x", is_staff=True))
        self.drive = mock.patch(
            "helpers.views.upload_photos_to_slum_drive_folder", return_value={"files": [], "hierarchy": []}
        ).start()
        self.addCleanup(mock.patch.stopall)

    def post(self, *files, client=None):
        return (client or self.client).post(URL, {
            "photos": list(files), "is_other_upload": "1", "custom_folder_name": "Field visit", "slum_id": "",
            "project_type": "OHOT", "photo_date": date.today().isoformat(),
        })

    def assert_refused(self, response, text):
        self.assertEqual(response.status_code, 400)
        self.assertIn(text, response.json()["message"])
        self.drive.assert_not_called()

    def test_auditor_file_types_are_refused(self):
        for name in ("test.js", "test.html", "test.svg", "test.php", "test.txt", "test.json"):
            self.assert_refused(self.post(photo(name, HTML, "image/jpeg")), "only JPG and PNG")

    def test_html_renamed_to_jpg_is_refused(self):
        self.assert_refused(self.post(photo("fake.jpg", HTML)), "not a valid JPG or PNG")

    def test_png_named_jpg_is_refused(self):
        self.assert_refused(self.post(photo("mixed.jpg", image_bytes("PNG"))), "not a JPG image")

    def test_gif_named_png_is_refused(self):
        self.assert_refused(self.post(photo("anim.png", image_bytes("GIF"), "image/png")), "not a PNG image")

    def test_one_bad_file_uploads_nothing(self):
        self.assert_refused(self.post(photo("ok.jpg", image_bytes("JPEG")), photo("evil.php", HTML)), "evil.php")

    def test_oversized_photo_is_refused(self):
        self.assertEqual(PHOTO_MAX_BYTES, 20 * 1024 * 1024)
        content = image_bytes("JPEG")
        with mock.patch("utils.uploads.PHOTO_MAX_BYTES", len(content) - 1):
            self.assert_refused(self.post(photo("big.jpg", content)), "larger than")

    def test_real_jpg_jpeg_and_png_are_accepted(self):
        response = self.post(photo("a.jpg", image_bytes("JPEG")), photo("b.JPEG", image_bytes("JPEG")),
                             photo("c.png", image_bytes("PNG"), "image/png"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(self.drive.call_args[1]["uploaded_files"]), 3)

    def test_upload_now_needs_the_csrf_token(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(User.objects.get(username="staffer"))
        self.assertEqual(self.post(photo("a.jpg", image_bytes("JPEG")), client=strict).status_code, 403)


class ReencodeTests(TestCase):
    def test_name_and_type_come_from_the_image_not_the_client(self):
        upload = photo("holiday.php", image_bytes("PNG"), "text/html")
        data, extension, content_type = compress_uploaded_image(upload)
        self.assertEqual((extension, content_type), ("png", "image/png"))
        self.assertEqual(Image.open(io.BytesIO(data)).format, "PNG")

    def test_non_image_is_never_passed_through(self):
        with self.assertRaises(Exception):
            compress_uploaded_image(photo("x.jpg", HTML))

    def test_large_photo_is_resized(self):
        data, extension, _ = compress_uploaded_image(photo("big.jpg", image_bytes("JPEG", (3200, 2400))))
        self.assertEqual(extension, "jpg")
        self.assertLessEqual(max(Image.open(io.BytesIO(data)).size), 1600)
