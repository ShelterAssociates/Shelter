"""Template previews are drawn once and then served from the cache; template_image answers 304 when unchanged."""

from unittest import mock

from django.test import override_settings
from django.urls import reverse

from design_studio.forms import initial_for
from design_studio.services import preview
from design_studio.services.render import DesignRenderer
from design_studio.services.resources import Resources
from design_studio.tests.test_pipeline import DesignStudioTestCase

LOCMEM = {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "design-preview-tests"}


class PreviewCacheTests(DesignStudioTestCase):
    def setUp(self):
        super().setUp()
        from django.conf import settings
        override = override_settings(CACHES=dict(settings.CACHES, design_preview=LOCMEM))
        override.enable()
        self.addCleanup(override.disable)
        from django.core.cache import caches
        caches["design_preview"].clear()
        self.user.is_superuser = True
        self.user.save()
        self.drawn = mock.patch("design_studio.services.preview.DesignRenderer", wraps=DesignRenderer)
        self.renderer = self.drawn.start()
        self.addCleanup(self.drawn.stop)

    def editor_post(self, template, **changes):
        data = {key: value for key, value in initial_for(template.spec(), template.name, template.is_default).items() if value not in (None, False)}
        data.update(changes, base=template.pk)
        return self.client.post(reverse("design_studio:template_preview"), data)

    def test_opening_the_editor_after_the_thumbnail_draws_nothing_new(self):
        template = self.template()
        self.client.get(reverse("design_studio:template_image", args=[template.pk]) + "?small=1")
        self.assertEqual(self.renderer.call_count, 1)
        result = self.editor_post(template).json()
        self.assertTrue(result["image"].startswith("data:image/png;base64,"))
        self.assertEqual(result["problems"], [])
        self.assertEqual(self.renderer.call_count, 1)

    def test_a_changed_value_is_drawn_again_and_a_repeat_is_not(self):
        template = self.template()
        self.editor_post(template)
        self.editor_post(template, qr_caption="SCAN")
        self.editor_post(template, qr_caption="SCAN")
        self.assertEqual(self.renderer.call_count, 2)

    def test_template_image_is_revalidated_with_an_etag(self):
        url = reverse("design_studio:template_image", args=[self.template().pk]) + "?small=1"
        first = self.client.get(url)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first["Cache-Control"], "private, no-cache")
        again = self.client.get(url, HTTP_IF_NONE_MATCH=first["ETag"])
        self.assertEqual((again.status_code, again.content), (304, b""))
        self.assertEqual(self.renderer.call_count, 1)
        self.client.logout()
        self.assertEqual(self.client.get(url, HTTP_IF_NONE_MATCH=first["ETag"]).status_code, 302)

    def test_key_changes_with_the_fonts_and_logos(self):
        spec = self.template().spec()
        resources = Resources.from_database()
        other = Resources(dict(resources.fonts, Extra=("/x.ttf", "")), resources.assets)
        self.assertNotEqual(preview.sample_key(spec, False, 0.5, resources), preview.sample_key(spec, False, 0.5, other))

    def test_fonts_are_loaded_once_per_worker(self):
        first, second = Resources.bundled(), Resources.bundled()
        self.assertIs(first.font("Roboto Bold", 40), second.font("Roboto Bold", 40))
