"""switch_from_plates: a database and media folder left by the old plates app become design_studio's."""

import io
import os
import shutil
import tempfile

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings

from design_studio.management.commands.switch_from_plates import INDEXES, MODELS
from design_studio.models import DesignAsset, DesignBatch, DesignTemplate
from notification.models import EmailPurpose, JobRequest


class SwitchFromPlatesTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        os.makedirs(os.path.join(self.media, "plate_assets"))
        os.makedirs(os.path.join(self.media, "plate_exports", "r1"))
        open(os.path.join(self.media, "plate_assets", "logo.png"), "wb").close()
        self.asset = DesignAsset.objects.create(name="Logo", kind="other", image="plate_assets/logo.png")
        template = DesignTemplate.objects.create(name="T", plate_type="digipin", qr_link_pattern="https://www.google.com/maps?q={lat},{long}")
        self.batch = DesignBatch.objects.create(template=template, plate_type="digipin", status="done", upload="plate_uploads/abc/u.xlsx",
                                                file_path=os.path.join(self.media, "plate_exports", "r1", "z.zip"))
        Group.objects.create(name="sticker_plates_generation")
        EmailPurpose.objects.create(key="plates_batch", display_name="Plates batch copy", description="Copy of every plates batch email")
        self.request = JobRequest.objects.create(job_key="plate_batch", status="done")
        self.make_old_state()

    def make_old_state(self):
        with connection.cursor() as cursor:
            for old, new in MODELS:
                cursor.execute("ALTER TABLE design_studio_{} RENAME TO plates_{}".format(new, old))
                cursor.execute("ALTER SEQUENCE IF EXISTS design_studio_{}_id_seq RENAME TO plates_{}_id_seq".format(new, old))
                cursor.execute("UPDATE django_content_type SET app_label = 'plates', model = %s WHERE app_label = 'design_studio' AND model = %s", [old, new])
                cursor.execute("UPDATE auth_permission SET codename = replace(codename, %s, %s), name = replace(name, 'design ', 'plate ') "
                               "WHERE content_type_id = (SELECT id FROM django_content_type WHERE app_label = 'plates' AND model = %s)", [new, old, old])
            for old, new in INDEXES:
                cursor.execute("ALTER INDEX {} RENAME TO {}".format(new, old))
            cursor.execute("DELETE FROM django_migrations WHERE app IN ('plates', 'design_studio')")
            cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('plates', '0001_initial', now()), ('plates', '0002_auto', now())")
        ContentType.objects.clear_cache()

    def run_command(self, *args):
        out = io.StringIO()
        call_command("switch_from_plates", *args, stdout=out)
        ContentType.objects.clear_cache()
        return out.getvalue()

    def test_dry_run_changes_nothing(self):
        out = self.run_command("--dry-run")
        self.assertIn("plates_platebatch -> design_studio_designbatch", out)
        self.assertIn("Dry run", out)
        self.assertIn("plates_platebatch", connection.introspection.table_names())
        self.assertTrue(os.path.isdir(os.path.join(self.media, "plate_assets")))

    def test_switch_moves_everything_and_a_second_run_does_nothing(self):
        self.assertIn("Left as is (no longer used): migration record plates.0002_auto", self.run_command())
        tables = connection.introspection.table_names()
        self.assertIn("design_studio_designbatch", tables)
        self.assertNotIn("plates_platebatch", tables)
        self.assertEqual(ContentType.objects.get_for_model(DesignBatch).app_label, "design_studio")
        self.assertTrue(Permission.objects.filter(codename="add_designtemplate", name="Can add design template").exists())
        with connection.cursor() as cursor:
            cursor.execute("SELECT app FROM django_migrations WHERE name = '0001_initial' AND app IN ('plates', 'design_studio')")
            self.assertEqual([row[0] for row in cursor.fetchall()], ["design_studio"])
            cursor.execute("SELECT indexname FROM pg_indexes WHERE indexname IN %s", [tuple(new for _, new in INDEXES)])
            self.assertEqual(len(cursor.fetchall()), 2)
        self.assertTrue(Group.objects.filter(name="design_studio").exists())
        purpose = EmailPurpose.objects.get(key="design_studio_batch")
        self.assertEqual(purpose.display_name, "Design Studio batch copy")
        self.assertEqual(JobRequest.objects.get(pk=self.request.pk).job_key, "design_batch")
        self.assertEqual(DesignAsset.objects.get(pk=self.asset.pk).image.name, "design_assets/logo.png")
        batch = DesignBatch.objects.get(pk=self.batch.pk)
        self.assertEqual(batch.upload.name, "design_uploads/abc/u.xlsx")
        self.assertEqual(batch.file_path, os.path.join(self.media, "design_exports", "r1", "z.zip"))
        self.assertTrue(os.path.isfile(os.path.join(self.media, "design_assets", "logo.png")))
        self.assertFalse(os.path.exists(os.path.join(self.media, "plate_assets")))
        DesignBatch.objects.create(template=batch.template, plate_type="digipin")
        self.assertIn("nothing to do", self.run_command())

    def test_refuses_while_a_batch_is_queued(self):
        with connection.cursor() as cursor:
            cursor.execute("UPDATE plates_platebatch SET status = 'queued'")
        with self.assertRaisesMessage(CommandError, "queued or running"):
            self.run_command()
        self.assertIn("plates_platebatch", connection.introspection.table_names())

    def test_refuses_when_the_new_folder_exists(self):
        os.makedirs(os.path.join(self.media, "design_assets"))
        with self.assertRaisesMessage(CommandError, "already exists"):
            self.run_command()
