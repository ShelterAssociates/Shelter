"""Shared sponsor fixtures for the sponsor tests."""

import shutil
import tempfile

from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.test import override_settings

from sponsor.models import ProjectDocuments, Sponsor, SponsorProject


class SponsorFixtureMixin:
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media)
        self.media_override.enable()
        group, _ = Group.objects.get_or_create(name="sponsor")
        self.owner = User.objects.create_user("hdfclife", password="x")
        self.other = User.objects.create_user("othersponsor", password="x")
        for user in (self.owner, self.other):
            user.groups.add(group)
        self.admin = User.objects.create_superuser("shelter", "s@example.org", "x")
        sponsor = Sponsor.objects.create(organization_name="HDFCLife", address="Pune", user=self.owner)
        Sponsor.objects.create(organization_name="Other", address="Pune", user=self.other)
        self.project = SponsorProject.objects.create(
            name="Toilet facilitation", project_type="1", funds_sponsored=100, status="2",
            created_by=self.admin, sponsor=sponsor,
        )

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def stored_document(self, name, content):
        doc = ProjectDocuments(sponsor_project=self.project)
        doc.document.save(name, ContentFile(content))
        return doc
