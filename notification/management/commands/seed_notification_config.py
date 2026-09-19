"""Seeds the email address book and job definitions.

Idempotent: existing rows are left as the team edited them. Run once after the
first migrate, and again after adding a new purpose in code.
"""

from django.core.management.base import BaseCommand

from notification.models import (
    EmailContact,
    EmailPurpose,
    EmailRecipient,
    JobDefinition,
    JobStepConfig,
)

DOMAIN = "shelter-associates.org"

CONTACTS = [
    ("developer", "Developer"),
    ("data", "Data Team"),
    ("info", "Shelter Associates"),
    ("dhana", "Dhana"),
    ("gis", "GIS Team"),
]

PURPOSES = [
    {
        "key": "job_digest",
        "display_name": "Scheduled job daily digest",
        "description": "Morning summary of every scheduled job run.",
        "to": ["developer", "data"],
        "cc": ["info", "dhana"],
    },
    {
        "key": "job_failure",
        "display_name": "Scheduled job failure alert",
        "description": "Sent immediately when a scheduled job fails.",
        "to": ["developer", "data"],
        "cc": ["info", "dhana"],
    },
    {
        "key": "gis_reminder",
        "display_name": "GIS server data sync reminder",
        "description": "Monthly reminder to run the GIS server data sync.",
        "to": ["gis"],
        "cc": ["info", "dhana", "developer"],
    },
    {
        "key": "kml_change",
        "display_name": "KML component change notification",
        "description": "KML upload, delete and metric changes.",
        "to": ["gis"],
        "cc": ["developer"],
    },
    {
        "key": "photo_export_failure",
        "display_name": "Photo export failure",
        "description": "Told when a queued photo export fails.",
        "to": ["developer"],
        "cc": [],
    },
    {
        "key": "avni_console_activity",
        "display_name": "AVNI console activity",
        "description": "Every sync someone queues from the AVNI console or the shell: who, what, and the records touched. The requester is CC'd automatically.",
        "to": ["developer", "data"],
        "cc": [],
    },
    {
        "key": "avni_bulk_update",
        "display_name": "AVNI bulk update report",
        "description": "Every spreadsheet pushed into AVNI (dry runs included): who did it and the full list of changes. Developer and data team only.",
        "to": ["developer", "data"],
        "cc": [],
    },
    {
        "key": "dev_redirect",
        "display_name": "Development redirect",
        "description": "With DEBUG on, every outbound mail goes ONLY to these contacts.",
        "to": ["developer"],
        "cc": [],
    },
]

JOBS = [
    {
        "key": "avni_daily_sync",
        "display_name": "Avni daily sync",
        "expected_times": "22:00",
        "max_runtime_minutes": 480,
        "steps": [
            "households:Household",
            "households:Structure",
            "households:Detailed Socio Economic Survey",
            "daily_reporting",
            "family_factsheets",
            "mobilization",
            "household_encounters",
            "members",
        ],
    },
    # Manual jobs: no expected times, so they are listed in the digest but never "missed".
    {"key": "rhs_sync", "display_name": "RHS sync (manual)", "expected_times": "", "max_runtime_minutes": 360},
    {"key": "rim_sync", "display_name": "RIM / toilet sync (manual)", "expected_times": "", "max_runtime_minutes": 180},
    {"key": "mobilization_sync", "display_name": "Mobilization sync (manual)", "expected_times": "", "max_runtime_minutes": 120},
    {"key": "family_factsheet_sync", "display_name": "Family factsheet sync (manual)", "expected_times": "", "max_runtime_minutes": 180},
    {"key": "daily_reporting_sync", "display_name": "Daily reporting sync (manual)", "expected_times": "", "max_runtime_minutes": 180},
    {"key": "encounter_sync", "display_name": "Direct encounter sync (manual)", "expected_times": "", "max_runtime_minutes": 360},
    {"key": "household_encounter_sync", "display_name": "All household encounters sync (manual)", "expected_times": "", "max_runtime_minutes": 600},
    {"key": "member_sync", "display_name": "Family member sync (manual)", "expected_times": "", "max_runtime_minutes": 180},
    {"key": "subject_sync", "display_name": "Subject sync from the explorer (manual)", "expected_times": "", "max_runtime_minutes": 240},
    {"key": "file_import", "display_name": "JSON file import (manual)", "expected_times": "", "max_runtime_minutes": 120},
    {
        "key": "avni_form_cache_refresh",
        "display_name": "AVNI form cache refresh",
        "expected_times": "01:30",
        "max_runtime_minutes": 60,
        "steps": ["form_cache_refresh", "survey_catalog", "slum_locations"],
    },
    {
        "key": "dashboard_update",
        "display_name": "Dashboard update",
        "expected_times": "23:00",
        "expected_days_of_month": "1,16",
        "max_runtime_minutes": 180,
        "steps": ["dashboard_data_Save"],
    },
    {
        "key": "cleanup_generated_files",
        "display_name": "Cleanup generated files",
        "expected_times": "05:00",
        "max_runtime_minutes": 30,
        "runner": "external",
    },
    {
        "key": "job_digest",
        "display_name": "Job digest mailer",
        "expected_times": "06:00",
        "max_runtime_minutes": 30,
    },
    # Reported on their own, never in the digest: bulk updates mail developer + data
    # team as they happen (avni_bulk_update purpose); selftest is a smoke test.
    {"key": "avni_bulk_update", "display_name": "AVNI bulk update", "expected_times": "", "max_runtime_minutes": 240,
     "include_in_digest": False},
    {"key": "selftest", "display_name": "Notification self test", "expected_times": "", "max_runtime_minutes": 10,
     "include_in_digest": False, "alert_on_failure": False},
]

# Flags the seed enforces even on existing rows, so a job created on first sight
# by run_job (defaults: in digest) is corrected by the next seed.
ENFORCED_FLAGS = ("include_in_digest", "alert_on_failure")


def enforce_flags(job, spec):
    """Apply the spec's ENFORCED_FLAGS to an existing row; True when something changed."""
    changed = [flag for flag in ENFORCED_FLAGS if flag in spec and getattr(job, flag) != spec[flag]]
    for flag in changed:
        setattr(job, flag, spec[flag])
    if changed:
        job.save(update_fields=changed)
    return bool(changed)


class Command(BaseCommand):
    help = "Seed email contacts, purposes and job definitions."

    def handle(self, *args, **options):
        contacts = {}
        for slug, name in CONTACTS:
            contact, created = EmailContact.objects.get_or_create(
                email="{}@{}".format(slug, DOMAIN), defaults={"name": name}
            )
            contacts[slug] = contact
            self.stdout.write("{} contact {}".format(
                "created" if created else "kept", contact.email
            ))

        for spec in PURPOSES:
            purpose, created = EmailPurpose.objects.get_or_create(
                key=spec["key"],
                defaults={
                    "display_name": spec["display_name"],
                    "description": spec["description"],
                },
            )
            self.stdout.write("{} purpose {}".format(
                "created" if created else "kept", purpose.key
            ))
            for kind in ("to", "cc"):
                for slug in spec[kind]:
                    EmailRecipient.objects.get_or_create(
                        purpose=purpose, contact=contacts[slug], kind=kind
                    )

        for spec in JOBS:
            job, created = JobDefinition.objects.get_or_create(
                key=spec["key"],
                defaults={
                    "display_name": spec["display_name"],
                    "expected_times": spec["expected_times"],
                    "expected_days_of_month": spec.get("expected_days_of_month", ""),
                    "max_runtime_minutes": spec["max_runtime_minutes"],
                    "runner": spec.get("runner", "internal"),
                    "include_in_digest": spec.get("include_in_digest", True),
                    "alert_on_failure": spec.get("alert_on_failure", True),
                },
            )
            verb = "created" if created else "kept"
            if not created and enforce_flags(job, spec):
                verb = "updated"
            self.stdout.write("{} job {}".format(verb, job.key))
            for order, step_name in enumerate(spec.get("steps", [])):
                JobStepConfig.objects.get_or_create(
                    job=job, step_name=step_name, defaults={"order": order}
                )

        self.stdout.write(self.style.SUCCESS("Seed complete."))
