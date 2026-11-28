"""nginx TLS settings kept in the repo: TLS 1.2+ only, forward-secret AEAD ciphers only."""

import re
import subprocess

from django.test import SimpleTestCase

STRONG_SUITE = re.compile(r"^ECDHE-(RSA|ECDSA)-(AES(128|256)-GCM-SHA(256|384)|CHACHA20-POLY1305)$")


def deploy_files():
    files = subprocess.check_output(["git", "ls-files", "-z", "deploy"]).decode().split("\0")
    return [f for f in files if f]


def values(directive):
    found = []
    for path in deploy_files():
        for line in open(path, errors="replace"):
            match = re.match(r"\s*(?:%s)[\s=]+[\"']?([^;\"']+)" % directive, line)
            if match:
                found.append((path, match.group(1).strip()))
    return found


class TlsConfigTests(SimpleTestCase):
    def test_no_old_protocols(self):
        protocols = values("ssl_protocols|PROTOCOLS")
        self.assertTrue(protocols)
        for path, value in protocols:
            self.assertFalse(set(value.split()) & {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}, path)

    def test_only_strong_cipher_suites(self):
        ciphers = values("ssl_ciphers|CIPHERS")
        self.assertTrue(ciphers)
        for path, value in ciphers:
            weak = [suite for suite in value.split(":") if not STRONG_SUITE.match(suite)]
            self.assertEqual(weak, [], path)
