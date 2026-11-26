import io
import json
import re
import uuid
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse
from PIL import Image

from plates.models import PlateActivity, PlateBatch, PlateTemplate
from plates.permissions import DENIED
from plates.services import activity
from plates.tests.test_pipeline import GROUP, PlatesTestCase

SAMPLE_UUID = uuid.UUID("9f1c0000-0000-4000-8000-000000000000")


def every_url():
    """Every plates URL with sample arguments."""
    return [
        reverse("plates:home"), reverse("plates:single"), reverse("plates:bulk_new"), reverse("plates:batches"),
        reverse("plates:excel_format_download", args=["digipin"]),
        reverse("plates:batch_detail", args=[SAMPLE_UUID]), reverse("plates:bulk_check", args=[SAMPLE_UUID]),
        reverse("plates:bulk_demo_image", args=[SAMPLE_UUID, 2]), reverse("plates:bulk_skipped", args=[SAMPLE_UUID]),
        reverse("plates:bulk_confirm", args=[SAMPLE_UUID]), reverse("plates:batch_download", args=[SAMPLE_UUID]),
        reverse("plates:batch_cancel", args=[SAMPLE_UUID]), reverse("plates:batch_regenerate", args=[SAMPLE_UUID]),
        reverse("plates:templates"), reverse("plates:template_new"), reverse("plates:template_preview"),
        reverse("plates:link_preview"), reverse("plates:asset_upload"), reverse("plates:font_upload"),
        reverse("plates:template_edit", args=[1]), reverse("plates:template_copy", args=[1]), reverse("plates:template_image", args=[1]),
        reverse("plates:templates_archived"), reverse("plates:template_archive", args=[1]), reverse("plates:template_restore", args=[1]), reverse("plates:template_delete", args=[1]),
    ]


class AccessTests(PlatesTestCase):
    def test_every_url_redirects_anonymous_users_to_login(self):
        self.client.logout()
        for url in every_url():
            for method in (self.client.get, self.client.post):
                response = method(url)
                self.assertEqual(response.status_code, 302, url)
                self.assertTrue(response["Location"].startswith("/accounts/login/"), url)

    def test_staff_outside_the_group_gets_403_and_no_menu_link(self):
        outsider = User.objects.create_user("staff", password="x", is_staff=True)
        self.client.force_login(outsider)
        for url in every_url():
            response = self.client.get(url)
            self.assertIn(response.status_code, (403, 405), url)
        self.assertNotContains(self.client.get(reverse("admin:index")), reverse("plates:home"))

    def test_member_sees_the_menu_link(self):
        self.assertContains(self.client.get(reverse("plates:home")), 'href="{}"'.format(reverse("plates:home")))

    def test_other_users_batch_and_missing_batch_both_403_with_the_same_text(self):
        batch = self.draft()
        self.client.force_login(self.member("other"))
        for public_id in (batch.public_id, SAMPLE_UUID):
            for name in ("plates:batch_detail", "plates:bulk_check", "plates:batch_download", "plates:bulk_skipped"):
                response = self.client.get(reverse(name, args=[public_id]))
                self.assertEqual((response.status_code, response.content.decode()), (403, DENIED), name)
            response = self.client.post(reverse("plates:batch_cancel", args=[public_id]))
            self.assertEqual(response.status_code, 403)

    def test_superuser_sees_and_downloads_every_batch(self):
        batch = self.draft()
        admin = User.objects.create_superuser("boss", "boss@shelter-associates.org", "x")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("plates:bulk_check", args=[batch.public_id])).status_code, 200)
        page = self.client.get(reverse("plates:batches"))
        self.assertContains(page, reverse("plates:batch_detail", args=[batch.public_id]))
        self.assertContains(page, "<td>maker</td>")

    def test_template_pages_need_the_template_group(self):
        self.assertEqual(self.client.get(reverse("plates:templates")).status_code, 403)
        editors = Group.objects.create(name="Plate designers")
        self.user.groups.add(editors)
        with override_settings(PLATES_TEMPLATE_GROUPS=["Plate designers"]):
            self.assertEqual(self.client.get(reverse("plates:templates")).status_code, 200)

    def test_state_changing_views_are_post_only(self):
        batch = self.draft()
        for name in ("plates:bulk_confirm", "plates:batch_cancel", "plates:batch_regenerate"):
            self.assertEqual(self.client.get(reverse(name, args=[batch.public_id])).status_code, 405)

    def test_demo_image_only_for_rows_chosen_by_the_check_page(self):
        batch = self.draft()
        self.assertEqual(self.client.get(reverse("plates:bulk_demo_image", args=[batch.public_id, 2])).status_code, 404)
        self.client.get(reverse("plates:bulk_check", args=[batch.public_id]))
        self.assertEqual(self.client.get(reverse("plates:bulk_demo_image", args=[batch.public_id, 2])).status_code, 200)
        self.assertEqual(self.client.get(reverse("plates:bulk_demo_image", args=[batch.public_id, 9])).status_code, 404)

    def test_batch_list_rows_open_the_batch_and_inner_pages_have_a_back_link(self):
        batch = self.draft()
        page = self.client.get(reverse("plates:batches"))
        self.assertContains(page, 'data-href="{}"'.format(reverse("plates:batch_detail", args=[batch.public_id])))
        self.assertContains(page, 'data-grid-search="batch-grid"')
        self.assertContains(self.client.get(reverse("plates:bulk_check", args=[batch.public_id])), "&larr; Back to Excel upload")

    def test_urls_use_the_random_public_id(self):
        batch = self.draft()
        self.assertEqual(resolve(reverse("plates:batch_detail", args=[batch.public_id])).kwargs["public_id"], batch.public_id)
        self.assertEqual(self.client.get("/plates/batches/{}/".format(batch.pk)).status_code, 404)


class SinglePlateTests(PlatesTestCase):
    def post(self, **changes):
        data = {"plate_type": "digipin", "template": self.template().pk, "code": "4J6M8286K8", "lat": "16.6929355",
                "long": "74.45952441", "slum": "Nimajga Mal", "house_no": "1", "action": "download"}
        for option in ("holes", "side_panel"):
            if changes.pop(option, None):
                data[option] = "on"
        data.update(changes)
        return self.client.post(reverse("plates:single"), data)

    def test_download_png_at_print_size(self):
        response = self.post(holes="on")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="4J6M8286K8_1.png"')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (3000, 900))
        self.assertAlmostEqual(image.info["dpi"][0], 600, places=1)
        self.assertTrue(PlateActivity.objects.filter(action="single_plate", user=self.user).exists())

    def test_drill_holes_can_be_switched_off(self):
        with_holes = Image.open(io.BytesIO(self.post(holes="on").content))
        without = Image.open(io.BytesIO(self.post().content))
        self.assertEqual(with_holes.getpixel((118 + 26, 450 + 26)), (255, 255, 255))
        self.assertNotEqual(without.getpixel((118 + 26, 450 + 26)), (255, 255, 255))

    def test_side_panel_option_widens_the_plate(self):
        image = Image.open(io.BytesIO(self.post(holes="on", side_panel="on").content))
        self.assertEqual(image.size, (3000 + 451, 900))

    def test_checkboxes_come_before_their_text(self):
        page = self.client.get(reverse("plates:single")).content.decode()
        self.assertRegex(page, r'<label class="pl-check-line"[^>]*><input type="checkbox" name="holes"[^>]*> <span>Drill holes</span>')
        self.assertRegex(page, r'<input type="checkbox" name="side_panel"[^>]*> <span>Side panel')

    def test_required_fields_show_an_asterisk(self):
        page = self.client.get(reverse("plates:single")).content.decode()
        self.assertIn('House No <span class="pl-required" title="Required">*</span>', page)
        self.assertNotIn('Ward <span class="pl-required"', page)

    def test_preview_and_digipin_from_lat_long(self):
        response = self.post(action="preview", code="")
        self.assertContains(response, "data:image/png;base64,")

    def test_errors_next_to_the_field(self):
        response = self.post(code="BAD-123", action="preview")
        self.assertContains(response, 'Invalid DIGIPIN &quot;BAD-123&quot;')
        response = self.post(slum="Nimajga <b>", action="preview")
        self.assertContains(response, "Slum Name contains &lt; or &gt;")
        response = self.post(slum="Ambedkar " * 8, action="preview")
        self.assertContains(response, "The slum name is too long for this template")

    def test_template_must_match_the_plate_type(self):
        response = self.post(plate_type="pluscode", code="7J8PMFV5+5RCH")
        self.assertContains(response, "Pick a DIGIPIN template for Plus Code plates")

    def test_sixty_a_minute(self):
        with mock.patch.object(activity, "SINGLE_PLATES_PER_MINUTE", 2):
            self.post()
            self.post()
            response = self.post(action="preview")
        self.assertContains(response, "You have made 60 plates in the last minute")


class TemplateEditorTests(PlatesTestCase):
    def setUp(self):
        super().setUp()
        override = override_settings(PLATES_TEMPLATE_GROUPS=["Plate designers"])
        override.enable()
        self.addCleanup(override.disable)
        self.user.groups.add(Group.objects.create(name="Plate designers"))

    def form_data(self, template):
        page = self.client.get(reverse("plates:template_edit", args=[template.pk]))
        return dict(page.context["form"].initial, background_image="")

    def payload(self, template, **changes):
        data = {key: value for key, value in self.form_data(template).items() if value not in (None, False)}
        data.update(changes)
        return data

    def test_editor_pages_load(self):
        for url in (reverse("plates:templates"), reverse("plates:template_new") + "?type=pluscode",
                    reverse("plates:template_edit", args=[self.template().pk])):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        image = self.client.get(reverse("plates:template_image", args=[self.template().pk]))
        self.assertEqual(Image.open(io.BytesIO(image.content)).size, (3000, 900))

    def test_a_look_change_saves_a_new_version_and_the_old_one_is_read_only(self):
        original = self.template()
        response = self.client.post(reverse("plates:template_edit", args=[original.pk]), self.payload(original, qr_caption="SCAN HERE"))
        latest = PlateTemplate.objects.get(parent=original)
        self.assertRedirects(response, reverse("plates:template_edit", args=[latest.pk]))
        self.assertEqual((latest.version, latest.qr_caption, latest.is_default), (2, "SCAN HERE", True))
        original.refresh_from_db()
        self.assertFalse(original.is_active)
        self.assertContains(self.client.get(reverse("plates:template_edit", args=[original.pk])), "older version and is read-only")
        self.client.post(reverse("plates:template_edit", args=[original.pk]), self.payload(original, qr_caption="AGAIN"))
        self.assertEqual(PlateTemplate.objects.filter(parent=original).count(), 1)
        self.assertTrue(PlateActivity.objects.filter(action="template_changed", template=latest).exists())

    def test_fixed_text_that_does_not_fit_is_refused(self):
        original = self.template()
        response = self.client.post(reverse("plates:template_edit", args=[original.pk]), self.payload(original, qr_caption="SCAN FOR LOCATION NOW"))
        self.assertContains(response, "&quot;qr_caption&quot; cannot fit")
        self.assertFalse(PlateTemplate.objects.filter(parent=original).exists())

    def test_a_name_change_keeps_the_version(self):
        original = self.template()
        self.client.post(reverse("plates:template_edit", args=[original.pk]), self.payload(original, name="Renamed"))
        original.refresh_from_db()
        self.assertEqual((original.name, original.version), ("Renamed", 1))

    def test_overlap_and_bad_link_are_refused(self):
        original = self.template()
        elements = json.loads(self.form_data(original)["elements_json"])
        next(element for element in elements if element["id"] == "code")["box"][2] = 0.6
        response = self.client.post(reverse("plates:template_edit", args=[original.pk]), self.payload(
            original, elements_json=json.dumps(elements), qr_link_pattern="https://evil.example.com/{digipin}"))
        self.assertContains(response, "may only point to")
        response = self.client.post(reverse("plates:template_edit", args=[original.pk]), self.payload(original, elements_json=json.dumps(elements)))
        self.assertTrue(re.search(r"&quot;(code|qr_card)&quot; overlaps &quot;(code|qr_card)&quot;", response.content.decode()))
        self.assertFalse(PlateTemplate.objects.filter(parent=original).exists())

    def test_copy_sticker_without_holes_and_side_panel(self):
        original = self.template()
        self.client.post(reverse("plates:template_copy", args=[original.pk]))
        copy = PlateTemplate.objects.latest("pk")
        self.assertEqual((copy.name, copy.parent_id, copy.is_default), ("Copy of " + original.name, None, False))
        elements = json.loads(self.form_data(copy)["elements_json"])
        next(element for element in elements if element["id"] == "slum")["min_size"] = 0.07
        data = self.payload(copy, output_kind="sticker", height_mm="31.75", panel_on="on", panel_fields=["house_no", "slum"],
                            elements_json=json.dumps(elements))
        data.pop("holes_on", None)
        response = self.client.post(reverse("plates:template_edit", args=[copy.pk]), data)
        latest = PlateTemplate.objects.latest("pk")
        if response.status_code != 302:
            self.fail(response.context["form"].errors)
        self.assertEqual((latest.output_kind, latest.holes["on"], latest.side_panel["on"], float(latest.height_mm)), ("sticker", False, True, 31.75))
        image = Image.open(io.BytesIO(self.client.get(reverse("plates:template_image", args=[latest.pk])).content))
        self.assertEqual(image.size, (3000 + 451, 750))

    def test_live_preview_and_link_helper(self):
        original = self.template()
        response = self.client.post(reverse("plates:template_preview"), dict(self.payload(original), base=original.pk))
        self.assertTrue(response.json()["image"].startswith("data:image/png;base64,"))
        self.assertEqual(response.json()["problems"], [])
        response = self.client.post(reverse("plates:link_preview"), {"plate_type": "pluscode", "pattern": "https://www.google.com/maps/search/?api=1&query={pluscode}"})
        self.assertEqual(response.json()["link"], "https://www.google.com/maps/search/?api=1&query=7J8PMFV5%2B5RCH")
        response = self.client.post(reverse("plates:link_preview"), {"plate_type": "digipin", "pattern": "https://evil.example.com/{x}"})
        self.assertEqual(response.json()["link"], "")
        self.assertTrue(response.json()["problems"])

    def copied(self):
        self.client.post(reverse("plates:template_copy", args=[self.template().pk]))
        return PlateTemplate.objects.latest("pk")

    def test_archive_hides_the_template_and_restore_brings_it_back(self):
        from plates.forms import usable_templates

        original = self.template()
        response = self.client.post(reverse("plates:template_archive", args=[original.pk]))
        self.assertIn("Archived", response["Location"])
        original.refresh_from_db()
        self.assertEqual((original.is_active, original.is_default), (False, False))
        self.assertNotIn(original, usable_templates())
        self.assertContains(self.client.get(reverse("plates:templates")), "Archived templates (1)")
        self.assertContains(self.client.get(reverse("plates:templates_archived")), reverse("plates:template_restore", args=[original.pk]))
        self.client.post(reverse("plates:template_restore", args=[original.pk]))
        original.refresh_from_db()
        self.assertTrue(original.is_active)
        self.assertIn(original, usable_templates())

    def test_delete_removes_an_unused_archived_template_with_all_its_versions(self):
        copy = self.copied()
        self.client.post(reverse("plates:template_edit", args=[copy.pk]), self.payload(copy, qr_caption="SCAN HERE"))
        latest = PlateTemplate.objects.get(parent=copy)
        self.client.post(reverse("plates:template_archive", args=[latest.pk]))
        page = self.client.get(reverse("plates:template_delete", args=[latest.pk]))
        self.assertContains(page, "all 2 versions of it")
        response = self.client.post(reverse("plates:template_delete", args=[latest.pk]))
        self.assertIn("Deleted", response["Location"])
        self.assertFalse(PlateTemplate.objects.filter(pk__in=[copy.pk, latest.pk]).exists())
        self.assertTrue(PlateActivity.objects.filter(action="template_changed", detail__startswith="deleted").exists())

    def test_delete_is_refused_for_a_used_or_active_template(self):
        copy = self.copied()
        response = self.client.post(reverse("plates:template_delete", args=[copy.pk]))
        self.assertIn("Only+an+archived+template", response["Location"])
        PlateBatch.objects.create(template=copy, plate_type="digipin")
        self.client.post(reverse("plates:template_archive", args=[copy.pk]))
        self.assertContains(self.client.get(reverse("plates:template_delete", args=[copy.pk])), "used by 1 batch")
        response = self.client.post(reverse("plates:template_delete", args=[copy.pk]))
        self.assertIn("cannot+be+deleted", response["Location"])
        self.assertTrue(PlateTemplate.objects.filter(pk=copy.pk).exists())

    def test_uploads_are_checked(self):
        svg = SimpleUploadedFile("logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>")
        response = self.client.post(reverse("plates:asset_upload"), {"name": "Logo", "kind": "other", "image": svg})
        self.assertIn("PNG+or+JPEG", response["Location"])
        fake_png = SimpleUploadedFile("logo.png", b"not an image")
        response = self.client.post(reverse("plates:asset_upload"), {"name": "Logo", "kind": "other", "image": fake_png})
        self.assertIn("not+a+valid", response["Location"])
        buffer = io.BytesIO()
        Image.new("RGBA", (40, 40), (255, 0, 0, 255)).save(buffer, "PNG")
        response = self.client.post(reverse("plates:asset_upload"), {"name": "Red", "kind": "other", "image": SimpleUploadedFile("red.png", buffer.getvalue())})
        self.assertIn("Saved+Red", response["Location"])
        self.assertTrue(PlateActivity.objects.filter(action="asset_uploaded").exists())
        response = self.client.post(reverse("plates:font_upload"), {"name": "Bad", "file": SimpleUploadedFile("bad.ttf", b"nope")})
        self.assertIn("not+a+font", response["Location"])


class DeployRuleTests(SimpleTestCase):
    def test_nginx_blocks_every_plates_folder_on_both_servers(self):
        for site in ("deploy/nginx/prod.conf", "deploy/nginx/uat.conf"):
            text = open(site).read()
            self.assertRegex(text, r"location \^~ /media/plate_ \{\s*deny all;\s*return 403;\s*\}", site)

    def test_runserver_blocks_plates_media_too(self):
        for path in ("plate_exports/abc/x.zip", "plate_uploads/abc/x.xlsx", "plate_assets/x.png", "plate_fonts/x.ttf"):
            response = self.client.get("/media/" + path)
            self.assertEqual(response.status_code, 403, path)

    def test_cleanup_script_lists_plate_exports_and_runs_the_command(self):
        text = open("deploy/CLEANUP_GENERATED_FILES.sh").read()
        self.assertIn('"plate_exports")', text)
        self.assertIn("cleanup_plate_uploads", text)

    def test_registry_has_the_job(self):
        from notification.services import registry

        self.assertIs(registry.resolve("plate_batch"), __import__("plates.services.batch", fromlist=["run"]).run)
