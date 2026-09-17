import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mastersheet.views import AnalyseGisTabData

SLUM = (5, "Test Slum", "Testville")


def household(number):
    return SimpleNamespace(
        household_number=number,
        rhs_data={"Type_of_structure_occupancy": "Occupied house"},
        ff_data=None,
        submission_date=datetime.datetime(2026, 1, 1),
    )


def toilet(number, status):
    return SimpleNamespace(household_number=number, status=status, pocket=None, comment=None)


class AnalyseGisTabDataTests(SimpleTestCase):
    """Kobo-era '0022A' and Avni-era '22A' are the same house."""

    def run_with(self, households, toilets):
        patches = {
            "Slum": {"objects.filter.return_value.values_list.return_value": [SLUM]},
            "SponsorProjectDetails": {"objects.filter.return_value.exclude.return_value": []},
            "ToiletConstruction": {"objects.filter.return_value.exclude.return_value": toilets},
            "HouseholdData": {"objects.filter.return_value": households},
            "FollowupData": {"objects.filter.return_value.values.return_value": []},
            "communityActivityData": {"return_value": {}},
        }
        with patch.multiple(
            "mastersheet.views", **{k: MagicMock(**v) for k, v in patches.items()}
        ), patch("mastersheet.views.ToiletConstruction.get_status_display", lambda s: "Completed"):
            return AnalyseGisTabData(SLUM[0])[0]

    def test_zero_padded_and_plain_spellings_collapse_to_one_row(self):
        rows = self.run_with([household("0022A"), household("22A")], [toilet("22A", "6")])

        self.assertEqual([r["household_number"] for r in rows], ["22A"])
        self.assertEqual(rows[0]["final_status"], "Completed")
