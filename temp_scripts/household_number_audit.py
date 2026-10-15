from collections import Counter
from graphs.models import MemberData, HouseholdData

total_members = MemberData.objects.count()
blank_household_number = MemberData.objects.filter(household_number__in=["", None]).count()
print(f"Total MemberData rows: {total_members}")
print(f"MemberData rows with blank/null household_number: {blank_household_number}")

total_households = HouseholdData.objects.count()
null_rhs = HouseholdData.objects.filter(rhs_data__isnull=True).count()
print(f"\nTotal HouseholdData rows: {total_households}")
print(f"HouseholdData rows with rhs_data IS NULL: {null_rhs}")

no_uuid_count = 0
for hh in HouseholdData.objects.all().only("id", "rhs_data", "ff_data"):
    rhs = (hh.rhs_data or {}).get("rhs_uuid") if isinstance(hh.rhs_data, dict) else None
    ff = (hh.ff_data or {}).get("ff_uuid") if isinstance(hh.ff_data, dict) else None
    if not (rhs or ff):
        no_uuid_count += 1
print(f"HouseholdData rows with NEITHER rhs_uuid NOR ff_uuid present: {no_uuid_count} / {total_households}")

# For every distinct (slum_id, household_number) in MemberData, check if a matching HouseholdData row exists at all
member_household_keys = set(
    MemberData.objects.exclude(household_number__in=["", None]).values_list("slum_id", "household_number")
)
print(f"\nDistinct (slum_id, household_number) pairs referenced by MemberData: {len(member_household_keys)}")

household_keys_available = set(
    HouseholdData.objects.values_list("slum_id", "household_number")
)

from photos.utils import normalize_household_number, household_number_variants
missing_household_row = 0
for slum_id, hn in member_household_keys:
    variants = household_number_variants(normalize_household_number(hn))
    if not any((slum_id, v) in household_keys_available for v in variants):
        missing_household_row += 1

print(f"(slum_id, household_number) pairs from MemberData with NO matching HouseholdData row at all: {missing_household_row}")
