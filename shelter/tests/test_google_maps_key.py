"""The Google Maps key comes from settings (one per server), never from the source code."""

import re
import subprocess

from django.test import SimpleTestCase, TestCase, override_settings

from avni.tests.support import make_city
from master.forms import LocationWidget
from utils.checks import google_maps_key_is_set

GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_-]{30,}")
MAPS_SCRIPT = re.compile(r'maps\.googleapis\.com/maps/api/js\?key=([^&"]*)&')


class NoKeyInSourceTests(SimpleTestCase):
    def test_no_google_key_in_any_tracked_file(self):
        files = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
        found = [f for f in files if f and GOOGLE_KEY.search(open(f, "rb").read().decode("utf-8", "replace"))]
        self.assertEqual(found, [])


@override_settings(GOOGLE_API_KEY="key-of-this-server")
class MapPagesTests(TestCase):
    def setUp(self):
        make_city("Thane")

    def key_in(self, html):
        keys = MAPS_SCRIPT.findall(html)
        self.assertEqual(len(keys), 1, html[:300])
        return keys[0]

    def test_public_city_map_uses_the_setting(self):
        self.assertEqual(self.key_in(self.client.get("/city::Thane").content.decode()), "key-of-this-server")

    def test_city_dashboard_uses_the_setting(self):
        self.assertEqual(self.key_in(self.client.get("/dashboard/city::Thane").content.decode()), "key-of-this-server")

    def test_admin_polygon_widget_uses_the_setting(self):
        self.assertEqual(self.key_in(LocationWidget().render("shape", None)), "key-of-this-server")

    @override_settings(GOOGLE_API_KEY='a"b&c')
    def test_key_cannot_break_out_of_the_url(self):
        self.assertEqual(self.key_in(self.client.get("/city::Thane").content.decode()), "a%22b%26c")


class KeyCheckTests(SimpleTestCase):
    @override_settings(DEBUG=False, GOOGLE_API_KEY="")
    def test_missing_key_warns(self):
        self.assertEqual([m.id for m in google_maps_key_is_set(None)], ["shelter.W004"])

    @override_settings(DEBUG=False, GOOGLE_API_KEY="set")
    def test_key_set_passes(self):
        self.assertEqual(google_maps_key_is_set(None), [])

    @override_settings(DEBUG=True, GOOGLE_API_KEY="")
    def test_development_is_not_checked(self):
        self.assertEqual(google_maps_key_is_set(None), [])
