"""deploy/shelter_nginx never names the server software: every server block uses the generic error pages."""

import re

from django.test import SimpleTestCase

SNIPPET_INCLUDE = "include /etc/nginx/snippets/shelter-error-pages.conf;"


def server_blocks(path):
    """Top-level server { ... } blocks as (body text, directives at server level)."""
    text = "\n".join(line.split("#", 1)[0] for line in open(path).read().splitlines())
    blocks = []
    for match in re.finditer(r"^server\s*\{", text, re.M):
        depth, i, top = 1, match.end(), []
        start = i
        while depth:
            char = text[i]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            elif depth == 1:
                top.append(char)
            i += 1
        blocks.append((text[start:i], "".join(top)))
    return blocks


class NginxErrorPageTests(SimpleTestCase):
    def test_every_server_block_includes_the_generic_error_pages(self):
        blocks = server_blocks("deploy/shelter_nginx")
        self.assertGreaterEqual(len(blocks), 8)
        for body, _ in blocks:
            self.assertIn(SNIPPET_INCLUDE, body, body[:120])

    def test_no_return_at_server_level(self):
        # A server-level return bypasses error_page and shows nginx's own page.
        for body, top_level in server_blocks("deploy/shelter_nginx"):
            self.assertNotRegex(top_level, r"(^|[;\s])return\s", body[:120])

    def test_snippet_covers_nginx_pages_and_names_nothing(self):
        snippet = open("deploy/nginx_error_pages.conf").read()
        codes = set(re.findall(r"\b\d{3}\b", " ".join(re.findall(r"^error_page ([^;]*);", snippet, re.M))))
        self.assertLessEqual({"301", "400", "403", "404", "413", "494", "497", "500", "502", "503", "504"}, codes)
        self.assertIn("=400 /__error", snippet)
        self.assertIn("internal;", snippet)
        body = re.search(r"return 200 '([^']*)'", snippet).group(1)
        self.assertNotRegex(body.lower(), r"nginx|ubuntu|django|gunicorn")

    def test_script_hides_version_and_header(self):
        script = open("deploy/harden_nginx_headers.sh").read()
        self.assertIn("server_tokens off;", script)
        self.assertIn("more_clear_headers Server;", script)
