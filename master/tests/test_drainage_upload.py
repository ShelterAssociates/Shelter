"""The drainage form keeps only real JPG/PNG images up to 3 MB."""

import io
import os
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from avni.tests.support import make_city, make_slum
from master.models import drainage

INSERT = "/admin/sluminformation/drainage/insert/"


def image(fmt, name):
    data = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(data, fmt)
    return SimpleUploadedFile(name, data.getvalue())


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DrainageUploadTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("shelter", "s@example.org", "x"))
        self.slum = make_slum(make_city())

    def post(self, upload):
        return self.client.post(INSERT, {"slum_name": self.slum.id, "drainage_image": upload})

    def test_png_and_jpg_are_saved(self):
        for upload in (image("PNG", "a.png"), image("JPEG", "b.jpg")):
            self.assertEqual(self.post(upload).status_code, 302, upload.name)
        self.assertEqual(drainage.objects.count(), 2)

    def test_other_files_are_refused(self):
        uploads = (
            image("GIF", "a.gif"), image("BMP", "b.bmp"), image("PNG", "c.jpg"),
            SimpleUploadedFile("d.png", b"<html><script>alert(1)</script></html>"),
            SimpleUploadedFile("e.html", image("PNG", "x.png").read()),
        )
        for upload in uploads:
            self.assertEqual(self.post(upload).status_code, 200, upload.name)
        self.assertEqual(drainage.objects.count(), 0)

    def test_images_over_3_mb_are_refused(self):
        data = io.BytesIO()
        Image.frombytes("RGB", (1100, 1100), os.urandom(1100 * 1100 * 3)).save(data, "PNG")
        self.assertGreater(len(data.getvalue()), 3 * 1024 * 1024)
        self.assertEqual(self.post(SimpleUploadedFile("big.png", data.getvalue())).status_code, 200)
        self.assertEqual(drainage.objects.count(), 0)
