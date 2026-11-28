"""deploy/nginx/{prod,uat}.conf: same rules on both servers, and nginx never names its software."""

import re

from django.test import SimpleTestCase

SNIPPET_INCLUDE = "include /etc/nginx/snippets/shelter-error-pages.conf;"
SITES = ("deploy/nginx/prod.conf", "deploy/nginx/uat.conf")
# The only differences allowed between the two files (prod -> uat).
PROD_TO_UAT = [
    ("/etc/letsencrypt/live/app.shelter-associates.org-0002/", "/etc/letsencrypt/live/uat.shelter-associates.org/"),
    ("report.shelter-associates.org", "uat-report.shelter-associates.org"),
    ("graphs.shelter-associates.org", "uat-graphs.shelter-associates.org"),
    ("app.shelter-associates.org", "uat.shelter-associates.org"),
]


def without_comment_lines(text):
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


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


class NginxSiteTests(SimpleTestCase):
    def test_uat_is_prod_with_only_names_and_certificate_changed(self):
        prod = without_comment_lines(open(SITES[0]).read())
        for old, new in PROD_TO_UAT:
            prod = prod.replace(old, new)
        self.assertEqual(prod, without_comment_lines(open(SITES[1]).read()))

    def test_no_hostname_of_the_other_environment(self):
        uat = open(SITES[1]).read()
        self.assertNotRegex(uat, r"(?<![-.\w])(app|report|graphs)\.shelter-associates\.org")
        self.assertNotIn("uat", without_comment_lines(open(SITES[0]).read()))

    def test_every_server_block_includes_the_generic_error_pages(self):
        for site in SITES:
            blocks = server_blocks(site)
            self.assertEqual(len(blocks), 8, site)
            for body, _ in blocks:
                self.assertIn(SNIPPET_INCLUDE, body, "%s: %s" % (site, body[:120]))

    def test_no_return_at_server_level(self):
        # A server-level return bypasses error_page and shows nginx's own page.
        for site in SITES:
            for body, top_level in server_blocks(site):
                self.assertNotRegex(top_level, r"(^|[;\s])return\s", "%s: %s" % (site, body[:120]))

    def test_every_https_server_shares_the_tls_settings(self):
        # nginx 1.4.6 crashes when SNI switches between servers with and without a session cache.
        for site in SITES:
            for body, _ in server_blocks(site):
                if re.search(r"listen\s+443", body):
                    self.assertIn("include /etc/letsencrypt/options-ssl-nginx.conf;", body, "%s: %s" % (site, body[:120]))

    def test_sites_serve_nothing_from_nginx_default_folder(self):
        for site in SITES:
            for body, top_level in server_blocks(site):
                if re.search(r"listen\s+443;", body) and "try_files" in body:
                    self.assertIn("root /nonexistent;", top_level, "%s: %s" % (site, body[:120]))

    def test_snippet_covers_nginx_pages_and_names_nothing(self):
        snippet = open("deploy/nginx/error-pages.conf").read()
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
