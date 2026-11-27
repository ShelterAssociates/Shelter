"""One-time switch of a server that ran the old "plates" app over to design_studio: tables, content types,
permissions, the migration record, the group, the email purpose, job keys, stored file paths and media folders.
Safe to run again: once the old tables are gone it does nothing. Run it after pulling the code and before migrate."""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

MODELS = (
    ("plateasset", "designasset"),
    ("platefont", "designfont"),
    ("platetemplate", "designtemplate"),
    ("platebatch", "designbatch"),
    ("plateactivity", "designactivity"),
)
INDEXES = (
    ("plates_plat_status_dbc810_idx", "design_batch_status_idx"),
    ("plates_plat_user_id_d9b254_idx", "design_activity_user_idx"),
)
OLD_GROUP, OLD_PURPOSE, OLD_JOB_KEY = "sticker_plates_generation", "plates_batch", "plate_batch"
NEW_GROUP, NEW_PURPOSE, NEW_JOB_KEY = "design_studio", "design_studio_batch", "design_batch"
JOB_KEY_TABLES = ("notification_jobrequest", "notification_jobrun", "notification_jobdefinition")
ACTIVE_STATUSES = ("queued", "running")


def old_table(model):
    return "plates_" + model


def new_table(model):
    return "design_studio_" + model


def folders():
    """(old folder, new folder, path column updates) under MEDIA_ROOT."""
    new_name = lambda key, default: getattr(settings, "DESIGN_STUDIO_{}_DIR_NAME".format(key), default)  # noqa: E731
    return (
        ("plate_assets", new_name("ASSET", "design_assets"), (("designasset", "image"),)),
        ("plate_fonts", new_name("FONT", "design_fonts"), (("designfont", "file"),)),
        ("plate_uploads", new_name("UPLOAD", "design_uploads"), (("designbatch", "upload"),)),
        ("plate_exports", new_name("EXPORT", "design_exports"), ()),
    )


class Command(BaseCommand):
    help = "Switch a server from the old plates app to design_studio (run once, before migrate)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only print what would change.")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("This command is written for PostgreSQL.")
        tables = set(connection.introspection.table_names())
        if old_table("platetemplate") not in tables:
            self.stdout.write("No plates tables found: nothing to do (already switched, or a new server).")
            return
        if new_table("designtemplate") in tables:
            raise CommandError("Both plates_* and design_studio_* tables exist. Was migrate run before this command? "
                               "Drop the empty design_studio_* tables (check they are empty first) and run this again.")
        self.check_no_active_batch()
        moves = self.check_folders()
        for line in self.plan(moves):
            self.stdout.write(line)
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: nothing changed."))
            return
        moved = []
        try:
            with transaction.atomic():
                self.switch_database()
                for source, target in moves:
                    os.rename(source, target)
                    moved.append((source, target))
        except Exception:
            for source, target in reversed(moved):
                os.rename(target, source)
            raise
        self.stdout.write(self.style.SUCCESS("Switched to design_studio. Now run: manage.py migrate design_studio"))

    def check_no_active_batch(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM {} WHERE status IN %s".format(old_table("platebatch")), [ACTIVE_STATUSES])
            active = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM notification_jobrequest WHERE job_key = %s AND status IN %s", [OLD_JOB_KEY, ("queued", "running")])
            pending = cursor.fetchone()[0]
        if active or pending:
            raise CommandError("{} batch(es) queued or running and {} job request(s) pending. Wait for them to finish, "
                               "stop the job queue cron, then run this again.".format(active, pending))

    def check_folders(self):
        moves = []
        for old, new, _ in folders():
            source, target = os.path.join(settings.MEDIA_ROOT, old), os.path.join(settings.MEDIA_ROOT, new)
            if os.path.exists(target):
                raise CommandError("{} already exists. Move its files into {} (or remove it if empty) and run this again.".format(target, source))
            if os.path.isdir(source):
                moves.append((source, target))
        return moves

    def plan(self, moves):
        lines = ["Tables: {} -> {}".format(old_table(old), new_table(new)) for old, new in MODELS]
        lines += ["Content types, permissions and the migration record: app plates -> design_studio",
                  "Group {} -> {}; email purpose {} -> {}; job key {} -> {}".format(OLD_GROUP, NEW_GROUP, OLD_PURPOSE, NEW_PURPOSE, OLD_JOB_KEY, NEW_JOB_KEY)]
        lines += ["Folder: {} -> {}".format(source, target) for source, target in moves]
        return lines

    def switch_database(self):
        with connection.cursor() as cursor:
            for old, new in MODELS:
                cursor.execute("ALTER TABLE {} RENAME TO {}".format(old_table(old), new_table(new)))
                cursor.execute("ALTER SEQUENCE IF EXISTS {}_id_seq RENAME TO {}_id_seq".format(old_table(old), new_table(new)))
            for old, new in INDEXES:
                cursor.execute("ALTER INDEX IF EXISTS {} RENAME TO {}".format(old, new))
            for old, new in MODELS:
                cursor.execute("SELECT id FROM django_content_type WHERE app_label = 'plates' AND model = %s", [old])
                row = cursor.fetchone()
                if row:
                    cursor.execute("UPDATE django_content_type SET app_label = 'design_studio', model = %s WHERE id = %s", [new, row[0]])
                    cursor.execute("UPDATE auth_permission SET codename = replace(codename, %s, %s), name = replace(name, 'plate ', 'design ') "
                                   "WHERE content_type_id = %s", [old, new, row[0]])
            cursor.execute("UPDATE django_migrations SET app = 'design_studio' WHERE app = 'plates' AND name = '0001_initial'")
            cursor.execute("SELECT name FROM django_migrations WHERE app = 'plates'")
            for (name,) in cursor.fetchall():
                self.stdout.write("Left as is (no longer used): migration record plates.{}".format(name))
            self.rename_row(cursor, "auth_group", "name", OLD_GROUP, NEW_GROUP)
            if self.rename_row(cursor, "notification_emailpurpose", "key", OLD_PURPOSE, NEW_PURPOSE):
                cursor.execute("UPDATE notification_emailpurpose SET display_name = 'Design Studio batch copy', "
                               "description = replace(description, 'plates batch', 'Design Studio batch') WHERE key = %s", [NEW_PURPOSE])
            for table in JOB_KEY_TABLES:
                column = "key" if table == "notification_jobdefinition" else "job_key"
                cursor.execute("UPDATE {} SET {} = %s WHERE {} = %s".format(table, column, column), [NEW_JOB_KEY, OLD_JOB_KEY])
            for old, new, columns in folders():
                for model, column in columns:
                    cursor.execute("UPDATE {table} SET {col} = %s || substr({col}, %s) WHERE {col} LIKE %s".format(table=new_table(model), col=column),
                                   [new + "/", len(old) + 2, old + "/%"])
            old_exports, new_exports = folders()[3][:2]
            cursor.execute("UPDATE {} SET file_path = replace(file_path, %s, %s) WHERE file_path LIKE %s".format(new_table("designbatch")),
                           ["/{}/".format(old_exports), "/{}/".format(new_exports), "%/{}/%".format(old_exports)])

    def rename_row(self, cursor, table, column, old, new):
        """Rename one row's key unless the new one exists already (then say so and leave both)."""
        cursor.execute("SELECT count(*) FROM {} WHERE {} = %s".format(table, column), [new])
        if cursor.fetchone()[0]:
            self.stdout.write(self.style.WARNING("{} {} already exists; {} left as is. Merge them in the admin.".format(table, new, old)))
            return False
        cursor.execute("UPDATE {} SET {} = %s WHERE {} = %s".format(table, column, column), [new, old])
        return cursor.rowcount > 0
