"""Mapped components (the KML layers) across a re-survey and a merge.

Components point at a slum generically (content type + object id), so they are
invisible to the reverse-relation walk and need their own handling in both
places.
"""

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import LineString, Polygon
from django.test import TestCase

from component.models import Component, ComponentMetric, Metadata, Section
from master.models import Slum
from survey import merging, versioning
from survey.models import SlumVersionBackup
from survey.tests.support import make_city, make_slum

LINE = LineString((0, 0), (0, 1))


def make_metadata(name="Road"):
    section = Section.objects.create(name=name + " section", order=1.0)
    return Metadata.objects.create(
        name=name, section=section, level="s", type="c", visible=True, order=1.0,
    )


def add_component(slum, metadata, housenumber="1"):
    return Component.objects.create(
        metadata=metadata,
        housenumber=housenumber,
        shape=LINE,
        content_type=ContentType.objects.get_for_model(Slum),
        object_id=slum.id,
    )


class ComponentArchiveTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.metadata = make_metadata()
        add_component(self.slum, self.metadata, "1")
        add_component(self.slum, self.metadata, "2")
        ComponentMetric.objects.create(
            slum=self.slum, metadata=self.metadata, value=12.5, unit="m",
        )

    def test_components_are_found_through_the_generic_link(self):
        table = versioning.COMPONENT_TABLES[0]
        self.assertTrue(table.generic)
        self.assertEqual(versioning.rows_for(table, self.slum.id).count(), 2)

    def test_starting_a_version_archives_the_components_and_metrics(self):
        versioning.start_new_version(self.slum.id)

        backups = SlumVersionBackup.objects.filter(slum=self.slum, version=1)
        self.assertEqual(backups.filter(source_model="component.Component").count(), 2)
        self.assertEqual(backups.filter(source_model="component.ComponentMetric").count(), 1)

    def test_the_archived_component_keeps_its_geometry(self):
        versioning.start_new_version(self.slum.id)
        row = SlumVersionBackup.objects.filter(
            slum=self.slum, source_model="component.Component",
        ).first()
        self.assertIn("shape", row.data["fields"])
        self.assertTrue(row.data["fields"]["shape"])
        self.assertEqual(str(row.data["fields"]["housenumber"]), "1")

    def test_going_live_never_deletes_components(self):
        """The team removes and re-draws KML layers by hand, so nothing is cleared."""
        versioning.start_new_version(self.slum.id)
        versioning.go_live(self.slum.id)

        self.assertEqual(Component.objects.filter(object_id=self.slum.id).count(), 2)
        self.assertEqual(ComponentMetric.objects.filter(slum=self.slum).count(), 1)

    def test_the_archive_survives_the_team_replacing_the_layer(self):
        versioning.start_new_version(self.slum.id)
        versioning.go_live(self.slum.id)
        Component.objects.filter(object_id=self.slum.id).delete()
        add_component(self.slum, self.metadata, "99")

        self.assertEqual(
            SlumVersionBackup.objects.filter(
                slum=self.slum, version=1, source_model="component.Component",
            ).count(),
            2,
            "the previous survey's components are still readable",
        )

    def test_each_version_keeps_its_own_components(self):
        versioning.start_new_version(self.slum.id)
        versioning.go_live(self.slum.id)
        Component.objects.filter(object_id=self.slum.id).delete()
        add_component(self.slum, self.metadata, "99")
        versioning.start_new_version(self.slum.id)

        first = SlumVersionBackup.objects.filter(
            slum=self.slum, version=1, source_model="component.Component",
        )
        second = SlumVersionBackup.objects.filter(
            slum=self.slum, version=2, source_model="component.Component",
        )
        self.assertEqual(
            sorted(str(row.data["fields"]["housenumber"]) for row in first), ["1", "2"],
        )
        self.assertEqual([str(row.data["fields"]["housenumber"]) for row in second], ["99"])


class BackfillTests(TestCase):
    """A version started before a table joined the registry can still be filled."""

    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.metadata = make_metadata()
        add_component(self.slum, self.metadata, "1")

    def test_a_table_archived_later_is_reported_as_missing(self):
        versioning.start_new_version(self.slum.id)
        # pretend the components were not in the registry when the version began
        SlumVersionBackup.objects.filter(
            slum=self.slum, source_model="component.Component",
        ).delete()

        missing = [table.label for table in versioning.missing_backup_tables(self.slum.id, 1)]
        self.assertIn("Components (KML)", missing)

    def test_ensure_backup_fills_only_what_is_missing(self):
        versioning.start_new_version(self.slum.id)
        SlumVersionBackup.objects.filter(
            slum=self.slum, source_model="component.Component",
        ).delete()
        before = SlumVersionBackup.objects.filter(slum=self.slum, version=1).count()

        added = versioning.ensure_backup(self.slum.id, 1)

        self.assertEqual(added, {"Components (KML)": 1})
        self.assertEqual(SlumVersionBackup.objects.filter(slum=self.slum, version=1).count(), before + 1)
        # running it again adds nothing
        self.assertEqual(versioning.ensure_backup(self.slum.id, 1), {})

    def test_the_page_offers_the_backfill(self):
        from django.contrib.auth.models import User

        versioning.start_new_version(self.slum.id)
        SlumVersionBackup.objects.filter(
            slum=self.slum, source_model="component.Component",
        ).delete()
        User.objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.login(username="boss", password="pw")

        page = self.client.get("/slum-versions/{}/".format(self.slum.id))
        self.assertContains(page, "Back up what is missing")

        self.client.post("/slum-versions/{}/version/backfill/".format(self.slum.id), {}, follow=True)
        self.assertEqual(
            SlumVersionBackup.objects.filter(
                slum=self.slum, version=1, source_model="component.Component",
            ).count(), 1,
        )

    def test_the_backfill_is_refused_once_the_version_is_live(self):
        versioning.start_new_version(self.slum.id)
        versioning.go_live(self.slum.id)
        SlumVersionBackup.objects.filter(
            slum=self.slum, source_model="component.Component",
        ).delete()
        from django.contrib.auth.models import User

        User.objects.create_superuser("boss2", "boss2@example.com", "pw")
        self.client.login(username="boss2", password="pw")

        self.client.post("/slum-versions/{}/version/backfill/".format(self.slum.id), {}, follow=True)
        self.assertFalse(
            SlumVersionBackup.objects.filter(
                slum=self.slum, source_model="component.Component",
            ).exists(),
            "after go-live the live rows are the new version, so they must not be filed as the old one",
        )


class ComponentMergeTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.target = make_slum(self.city, name="Antule Nagar", code="AN1")
        self.source = make_slum(self.city, name="Antule Nagar New", code="AN2")
        self.metadata = make_metadata()
        add_component(self.source, self.metadata, "7")

    def test_the_dry_run_counts_the_components(self):
        report = merging.plan_merge(self.source.id, self.target.id)
        self.assertEqual(report["moving"].get("component.component"), 1)

    def test_a_merge_moves_the_components_instead_of_orphaning_them(self):
        moved = merging.merge(self.source.id, self.target.id)

        self.assertEqual(moved.get("component.component"), 1)
        self.assertFalse(Slum.objects.filter(id=self.source.id).exists())
        self.assertEqual(Component.objects.filter(object_id=self.target.id).count(), 1)
        self.assertFalse(
            Component.objects.filter(object_id=self.source.id).exists(),
            "a component left on a deleted slum id would be orphaned geometry",
        )

    def test_the_dump_includes_the_components(self):
        import json
        import tempfile

        path = tempfile.mkstemp(suffix=".json")[1]
        merging.merge(self.source.id, self.target.id, dump_path=path)
        with open(path) as handle:
            payload = json.load(handle)
        self.assertEqual(len(payload["rows"]["component.component"]), 1)
