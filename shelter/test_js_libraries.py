"""No JavaScript/CSS library with known vulnerabilities is published under /static/ or linked from a page."""

import re
import subprocess

from django.apps import apps
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase

# (name, banner pattern, lowest safe version)
LIBRARIES = [
    ("jQuery UI", re.compile(r"jQuery UI - v([0-9.]+)|\.ui\.version=\"([0-9.]+)\"|ui\.version = \"([0-9.]+)\""), "1.13.2"),
    ("jQuery", re.compile(r"jQuery (?:JavaScript Library )?v([0-9.]+)"), "3.5.0"),
    ("datepicker", re.compile(r"Datepicker for Bootstrap v([0-9.]+)"), "0"),
    ("Bootstrap", re.compile(r"Bootstrap v([0-9.]+)"), "3.4.1"),
    ("JSZip", re.compile(r"JSZip v([0-9.]+)"), "3.8.0"),
    ("SheetJS", re.compile(r"SheetJS[\s\S]*?\.version=\"([0-9.]+)\""), "0.20.2"),
]

# Old copies still to be replaced, by published path.
PENDING = {
    "js/jquery.min.js": "jQuery 1.12 for every page",
}

STATIC_TAG = re.compile(r"""\{%\s*static\s+['"]([^'"]+\.(?:js|css))['"]\s*%\}""")
COMMENTS = re.compile(r"<!--.*?-->|\{#.*?#\}|\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.DOTALL)
CDN = re.compile(r"""(?:src|href)=["'](https?://[^"']+\.(?:js|css))["']""")


def version(text):
    return tuple(int(part) for part in text.split("."))


def published_files():
    for finder in finders.get_finders():
        for path, storage in finder.list(apps.get_app_config("staticfiles").ignore_patterns + ["*.map"]):
            if path.endswith((".js", ".css")):
                yield path, storage


def identify(storage, path):
    with storage.open(path) as handle:
        data = handle.read().decode("utf-8", "replace")
    for name, pattern, lowest in LIBRARIES:
        text = data if name in ("jQuery UI", "SheetJS") else data[:3000]
        match = pattern.search(text)
        if match:
            return name, next(group for group in match.groups() if group), lowest
    return None


def templates():
    files = subprocess.check_output(["git", "ls-files", "*.html"], universal_newlines=True).split()
    return {path: COMMENTS.sub("", open(path, encoding="utf-8").read()) for path in files}


class PublishedLibraryTests(SimpleTestCase):
    def test_no_old_library_is_published(self):
        old = {}
        for path, storage in published_files():
            hit = identify(storage, path)
            if hit and version(hit[1]) < version(hit[2]):
                old[path] = "%s %s" % hit[:2]
        self.assertEqual(sorted(set(old) - set(PENDING)), [], old)

    def test_pending_list_has_no_stale_entries(self):
        published = {path for path, _ in published_files()}
        self.assertEqual(sorted(set(PENDING) - published), [])

    def test_bootstrap_ships_without_the_button_plugin(self):
        source = open(finders.find("js/bootstrap-3.4.1.js"), encoding="utf-8").read()
        self.assertIn("Bootstrap v3.4.1", source)
        self.assertNotIn("$.fn.button", source)
        self.assertNotIn("data-loading-text", source)


class PageLinkTests(SimpleTestCase):
    def test_every_static_script_and_stylesheet_exists(self):
        missing = [(path, ref) for path, text in templates().items()
                   for ref in STATIC_TAG.findall(text) if not finders.find(ref)]
        self.assertEqual(missing, [])

    def test_cdn_links_have_a_fixed_version(self):
        loose = [(path, url) for path, text in templates().items() for url in CDN.findall(text)
                 if "latest" in url or not re.search(r"[@/-]v?[0-9]+\.[0-9]+", url)]
        self.assertEqual(loose, [])

    def test_pages_use_the_current_files(self):
        old_names = re.compile(r"js/bootstrap\.min\.js|css/bootstrap\.min\.css|js/jszip\.min\.js|admin/js/jquery(\.min)?\.js")
        self.assertEqual([path for path, text in templates().items()
                          if "rest_framework" not in path and old_names.search(text)], [])
