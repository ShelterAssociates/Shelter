"""Possible duplicate households flagged when a household is saved, from the household table alone:
the same family registered under two numbers, and a household number typed again that is another household's."""

from django.test import TestCase

from avni.sync import household_checks, households
from avni.tests.support import make_city, make_slum, subject_record
from graphs.models import HouseholdData
from survey.models import SyncDuplicate

MOBILE = "Enter the 10 digit mobile number"
HEAD = "Full name of the head of the household"
AGAIN = "Househhold number"


def household(uuid, number, **observations):
    return subject_record(uuid=uuid, number=number, observations=observations)


class FamilyTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_same_mobile_and_head_under_two_numbers_is_flagged(self):
        households.save_household(household("hh-1", "0042", **{MOBILE: "98765 43210", HEAD: "Asha Ramesh Patil"}))
        households.save_household(household("hh-2", "0077", **{MOBILE: "9876543210", HEAD: "asha ramesh patil"}))
        group = SyncDuplicate.objects.get(kind="family")
        self.assertEqual(group.external_ids, ["hh-1", "hh-2"])
        self.assertEqual(group.details["numbers"], ["42", "77"])
        self.assertEqual(group.details["mobile"], "XXXXXX3210")
        self.assertEqual((group.slum_id, group.city_id), (self.slum.id, self.city.id))

    def test_same_mobile_with_another_head_is_not_a_family(self):
        households.save_household(household("hh-1", "0042", **{MOBILE: "9876543210", HEAD: "Asha Ramesh Patil"}))
        households.save_household(household("hh-2", "0077", **{MOBILE: "9876543210", HEAD: "Sunita Kale Shinde"}))
        self.assertFalse(SyncDuplicate.objects.exists())

    def test_placeholder_mobile_or_short_name_is_ignored(self):
        households.save_household(household("hh-1", "0042", **{MOBILE: "9999999999", HEAD: "Asha Ramesh Patil"}))
        households.save_household(household("hh-2", "0077", **{MOBILE: "9999999999", HEAD: "Asha Ramesh Patil"}))
        households.save_household(household("hh-3", "0078", **{MOBILE: "9123456780", HEAD: "Ram"}))
        households.save_household(household("hh-4", "0079", **{MOBILE: "9123456780", HEAD: "Ram"}))
        self.assertFalse(SyncDuplicate.objects.exists())

    def test_same_family_in_another_slum_is_not_flagged(self):
        other = make_slum(self.city, name="Bhim Nagar", code="BN1")
        households.save_household(household("hh-1", "0042", **{MOBILE: "9876543210", HEAD: "Asha Ramesh Patil"}))
        households.save_household(dict(household("hh-2", "0077", **{MOBILE: "9876543210", HEAD: "Asha Ramesh Patil"}),
                                       location={"Slum": other.name, "City": self.city.name.city_name}))
        self.assertFalse(SyncDuplicate.objects.exists())

    def test_recheck_closes_a_family_no_longer_shared(self):
        households.save_household(household("hh-1", "0042", **{MOBILE: "9876543210", HEAD: "Asha Ramesh Patil"}))
        households.save_household(household("hh-2", "0077", **{MOBILE: "9876543210", HEAD: "Asha Ramesh Patil"}))
        row = HouseholdData.objects.get(household_number="77")
        row.rhs_data["group_el9cl08/Enter_the_10_digit_mobile_number"] = "9000000001"
        row.save()
        self.assertEqual(household_checks.recheck(), 1)
        self.assertEqual(SyncDuplicate.objects.get().status, "resolved")


class NumberAgainTests(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city())

    def test_number_typed_again_that_is_another_households_is_flagged(self):
        households.save_household(household("hh-1", "0043"))
        households.save_household(household("hh-2", "0042", **{AGAIN: "0043"}))
        group = SyncDuplicate.objects.get(kind="number_again")
        self.assertEqual(group.external_ids, ["hh-1", "hh-2"])
        self.assertEqual((group.household_number, group.details["entered_again"]), ("42", "43"))

    def test_matching_or_unknown_number_typed_again_is_fine(self):
        households.save_household(household("hh-1", "0042", **{AGAIN: "42"}))
        households.save_household(household("hh-2", "0050", **{AGAIN: "0051"}))
        self.assertFalse(SyncDuplicate.objects.exists())

    def test_recheck_closes_once_the_number_is_corrected(self):
        households.save_household(household("hh-1", "0043"))
        households.save_household(household("hh-2", "0042", **{AGAIN: "0043"}))
        row = HouseholdData.objects.get(household_number="42")
        row.rhs_data["Enter_household_number_again"] = "42"
        row.save()
        self.assertEqual(household_checks.recheck(), 1)
        self.assertEqual(SyncDuplicate.objects.get().status, "resolved")
