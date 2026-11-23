"""Servers answer the API in JSON only; Django REST framework's own jQuery/Bootstrap are never published."""

import importlib
import os
import re
import runpy
import sys
import tempfile
import types
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.renderers import JSONRenderer

BROWSER = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


def renderers_with(debug):
    real = importlib.import_module("shelter.local_settings")
    fake = types.ModuleType("shelter.local_settings")
    fake.__dict__.update({k: v for k, v in vars(real).items() if not k.startswith("__")}, DEBUG=debug)
    with mock.patch.dict(sys.modules, {"shelter.local_settings": fake}), mock.patch("builtins.print", print):
        return runpy.run_path("shelter/settings.py")["REST_FRAMEWORK"]["DEFAULT_RENDERER_CLASSES"]


class JsonOnlyApiTests(TestCase):
    @mock.patch("rest_framework.views.APIView.renderer_classes", (JSONRenderer,))
    def test_browser_gets_json_without_any_page_or_script(self):
        for url in ("/api/", "/api/city/", "/admin/rest-auth/user/"):
            response = self.client.get(url, HTTP_ACCEPT=BROWSER)
            self.assertTrue(response["Content-Type"].startswith("application/json"), url)
            self.assertNotIn(b"<script", response.content, url)


class RendererSettingTests(SimpleTestCase):
    def test_servers_json_only_development_also_html(self):
        self.assertEqual(renderers_with(False), ("rest_framework.renderers.JSONRenderer",))
        self.assertIn("rest_framework.renderers.BrowsableAPIRenderer", renderers_with(True))


class CollectstaticTests(SimpleTestCase):
    def test_rest_framework_files_are_not_collected(self):
        with tempfile.TemporaryDirectory() as root, override_settings(STATIC_ROOT=root):
            call_command("collectstatic", interactive=False, verbosity=0)
            published = {os.path.relpath(os.path.join(d, f), root) for d, _, files in os.walk(root) for f in files}
        self.assertFalse([p for p in published if p.startswith("rest_framework/")])
        self.assertIn("admin/js/vendor/jquery/jquery.min.js", published)
        self.assertFalse([p for p in published if re.search(r"jquery-3\.4\.1|bootstrap-theme", p)])
