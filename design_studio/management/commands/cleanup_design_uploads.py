"""Nightly Design Studio housekeeping, run from deploy/CLEANUP_GENERATED_FILES.sh at 05:00 (after the zips are removed)."""

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from design_studio.models import DesignBatch
from design_studio.services import batch as batches, retention


class Command(BaseCommand):
    help = "Expire batches whose zip is gone, delete old uploads and unconfirmed drafts, close batches the orphan sweep stopped."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print what would change; change nothing.")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        now = timezone.now()
        if not self.dry_run:
            batches.reconcile_all()
        self.expire_missing_zips()
        self.drop_old_uploads(now - datetime.timedelta(days=int(getattr(settings, "DESIGN_STUDIO_UPLOAD_KEEP_DAYS", 180))))
        self.drop_old_drafts(now - datetime.timedelta(days=int(getattr(settings, "DESIGN_STUDIO_DRAFT_KEEP_DAYS", 7))))

    def report(self, text):
        self.stdout.write(("would " if self.dry_run else "") + text)

    def expire_missing_zips(self):
        gone = [batch for batch in DesignBatch.objects.filter(status="done") if not retention.file_exists(batch)]
        if not self.dry_run:
            DesignBatch.objects.filter(pk__in=[batch.pk for batch in gone]).update(status="expired")
        self.report("expire {} plate batch(es) whose zip was removed".format(len(gone)))

    def drop_old_uploads(self, cutoff):
        old = DesignBatch.objects.filter(confirmed_on__lt=cutoff).exclude(upload="").exclude(status__in=("queued", "running"))
        count = old.count()
        if not self.dry_run:
            for batch in old:
                batches.delete_upload(batch)
        self.report("delete {} uploaded Excel file(s) of batches confirmed before {}".format(count, cutoff.date()))

    def drop_old_drafts(self, cutoff):
        drafts = DesignBatch.objects.filter(confirmed_on__isnull=True, status__in=("draft", "cancelled"), created_on__lt=cutoff)
        count = drafts.count()
        if not self.dry_run:
            for batch in drafts:
                batches.delete_upload(batch)
                batch.delete()
        self.report("delete {} unconfirmed draft(s) created before {}".format(count, cutoff.date()))
