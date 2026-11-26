"""Prints plates/templates/plates/partials/guide.html to plates/static/plates/plates-guide.pdf with headless Chrome."""

import os
import shutil
import subprocess
import tempfile

from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string

from plates.views import GUIDE_PDF

BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


class Command(BaseCommand):
    help = "Rebuild the downloadable plates guide (PDF) from the How to use page. Needs Chrome or Chromium on this machine."

    def handle(self, *args, **options):
        browser = next((path for path in (shutil.which(name) for name in BROWSERS) if path), None)
        if browser is None:
            raise CommandError("Chrome or Chromium is needed to print the guide; install one or build it on a developer machine.")
        folder = tempfile.mkdtemp()
        try:
            page = os.path.join(folder, "guide.html")
            with open(page, "w", encoding="utf-8") as handle:
                handle.write(render_to_string("plates/guide_print.html"))
            subprocess.run([browser, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                            "--print-to-pdf={}".format(GUIDE_PDF), "file://" + page], check=True, timeout=120,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finally:
            shutil.rmtree(folder, ignore_errors=True)
        self.stdout.write("Wrote {} ({} KB)".format(GUIDE_PDF, os.path.getsize(GUIDE_PDF) // 1024))
