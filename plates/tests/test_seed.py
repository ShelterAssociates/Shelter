import io
import shutil
import tempfile

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings

from plates.models import PlateAsset, PlateBatch, PlateFont, PlateTemplate
from plates.services.render import PlateRenderer
from plates.services.resources import Resources
from plates.tests.support import row


class SeedTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media, PLATES_GROUPS=["sticker_plates_generation"])
        override.enable()
        self.addCleanup(override.disable)

    def seed(self):
        out = io.StringIO()
        call_command("seed_plate_presets", stdout=out)
        return out.getvalue()

    def test_creates_group_fonts_logos_and_templates(self):
        self.seed()
        self.assertTrue(Group.objects.filter(name="sticker_plates_generation").exists())
        self.assertEqual(PlateFont.objects.count(), 4)
        self.assertEqual(set(PlateAsset.objects.filter(is_default=True).values_list("kind", flat=True)),
                         {"digipin_symbol", "india_post_logo", "maps_logo"})
        defaults = PlateTemplate.objects.filter(is_default=True)
        self.assertEqual(sorted(defaults.values_list("plate_type", flat=True)), ["digipin", "pluscode"])
        digipin = defaults.get(plate_type="digipin")
        self.assertEqual((float(digipin.width_mm), float(digipin.height_mm), digipin.dpi), (127.0, 38.1, 600))
        self.assertEqual(digipin.qr_caption, "SCAN FOR LOCATION")

    def test_seeded_templates_render_from_the_database(self):
        self.seed()
        resources = Resources.from_database()
        for template in PlateTemplate.objects.all():
            image = PlateRenderer(template.spec(), resources).render(row(template.plate_type))
            self.assertEqual(image.size, (3000, 900))

    def test_running_twice_changes_nothing(self):
        self.seed()
        second = self.seed()
        self.assertNotIn("created", second)
        self.assertEqual(PlateTemplate.objects.count(), 2)
        self.assertEqual(PlateFont.objects.count(), 4)
        self.assertEqual(PlateAsset.objects.count(), 3)

    def test_template_edited_in_the_editor_is_left_alone(self):
        self.seed()
        original = PlateTemplate.objects.get(preset_key="digipin_plate")
        PlateTemplate.objects.create(name="Edited", plate_type="digipin", parent=original, version=2,
                                     qr_link_pattern=original.qr_link_pattern, elements=[])
        PlateTemplate.objects.filter(pk=original.pk).update(qr_caption="OLD")
        self.assertIn("left alone", self.seed())
        self.assertEqual(PlateTemplate.objects.get(pk=original.pk).qr_caption, "OLD")

    def test_changed_preset_in_use_gets_a_new_version(self):
        self.seed()
        original = PlateTemplate.objects.get(preset_key="digipin_plate")
        PlateBatch.objects.create(template=original, plate_type="digipin")
        PlateTemplate.objects.filter(pk=original.pk).update(qr_caption="OLD")
        self.assertIn("new version 2", self.seed())
        latest = PlateTemplate.objects.get(preset_key="digipin_plate", version=2)
        self.assertEqual((latest.parent_id, latest.qr_caption, latest.is_default), (original.pk, "SCAN FOR LOCATION", True))
        self.assertFalse(PlateTemplate.objects.get(pk=original.pk).is_active)

    def test_unused_preset_is_updated_in_place(self):
        self.seed()
        PlateTemplate.objects.filter(preset_key="digipin_plate").update(qr_caption="OLD")
        self.assertIn("updated", self.seed())
        self.assertEqual(PlateTemplate.objects.get(preset_key="digipin_plate").qr_caption, "SCAN FOR LOCATION")
