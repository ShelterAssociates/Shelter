"""Every {% url %} in a template names a route that exists, so no page fails with NoReverseMatch."""

import re
import subprocess

from django.test import SimpleTestCase
from django.urls import get_resolver

URL_TAG = re.compile(r"""\{%\s*url\s+['"]([^'"]+)['"](?![^%]*\sas\s)""")
COMMENTS = re.compile(r"<!--.*?-->|\{#.*?#\}|\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}", re.DOTALL)


def route_names(resolver=None, namespace=""):
    names = set()
    for pattern in (resolver or get_resolver()).url_patterns:
        if hasattr(pattern, "url_patterns"):
            names |= route_names(pattern, namespace + (pattern.namespace + ":" if pattern.namespace else ""))
        elif pattern.name:
            names.add(namespace + pattern.name)
    return names


class TemplateLinkTests(SimpleTestCase):
    maxDiff = None

    def test_every_url_tag_names_an_existing_route(self):
        known = route_names()
        files = subprocess.check_output(["git", "ls-files", "*.html"], universal_newlines=True).split()
        missing = [(path, name) for path in files
                   for name in URL_TAG.findall(COMMENTS.sub("", open(path, encoding="utf-8").read()))
                   if name not in known and not name.startswith("admin:")]
        self.assertEqual(missing, [])
