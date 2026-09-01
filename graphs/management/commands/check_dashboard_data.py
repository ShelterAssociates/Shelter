"""
Data-integrity check for DashboardData: flags any city whose aggregated
"other services" fields are negative -- the exact symptom caused by the
raw-count-vs-percentage bug fixed in graphs/dashboard_card.py and
graphs/analyse_data.py. Run after any dashboard recompute to confirm
every city is sane, not just the ones spot-checked by hand.

Usage: python manage.py check_dashboard_data
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum

from graphs.models import DashboardData
from master.models import City

CHECKED_FIELDS = [
    "water_other_services",
    "waste_other_services",
    "other_services_toilet_coverage",
]


class Command(BaseCommand):
    help = "Audit DashboardData for negative aggregate values, per city."

    def handle(self, *args, **options):
        failures = []

        for city in City.objects.all().order_by("name__city_name"):
            agg = DashboardData.objects.filter(city=city).aggregate(
                *(Sum(field) for field in CHECKED_FIELDS)
            )

            if all(agg[f"{field}__sum"] is None for field in CHECKED_FIELDS):
                self.stdout.write(f"{city.name.city_name:20s} SKIP (no DashboardData yet)")
                continue

            negative_fields = {
                field: agg[f"{field}__sum"]
                for field in CHECKED_FIELDS
                if (agg[f"{field}__sum"] or 0) < 0
            }

            if negative_fields:
                failures.append((city.name.city_name, negative_fields))
                self.stdout.write(
                    self.style.ERROR(f"{city.name.city_name:20s} FAIL {negative_fields}")
                )
            else:
                self.stdout.write(self.style.SUCCESS(f"{city.name.city_name:20s} OK   {agg}"))

        if failures:
            self.stdout.write(
                self.style.ERROR(f"\n{len(failures)} city(ies) have negative aggregate fields.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\nAll cities OK -- no negative aggregate values found.")
            )
