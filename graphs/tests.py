from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase

from graphs.dashboard_card import DashboardCard
from graphs.views import _percentages_summing_to_100


def _make_card():
    """Build a DashboardCard with RHSData.__init__ (DB access) bypassed.

    dashboard_card.py's formulas are what we want to test; RHSData.__init__
    does GeoDjango DB lookups we don't want in a unit test, so we skip it via
    __new__ and stub only the data-access methods each formula calls.
    """
    return DashboardCard.__new__(DashboardCard)


class WaterInfoTests(SimpleTestCase):
    """Water_Info() must return raw household COUNTS, not percentages.

    graphs/views.py::score_cards() computes the city-level water percentage
    as SUM(water_individual_connection_percentile) / SUM(water_data_available)
    * 100 -- a weighted average across every slum in the city. That division
    only produces a real percentage if the per-slum values being summed are
    raw counts. An earlier version of this fix stored per-slum percentages
    instead, which silently broke that city-level weighted average (dividing
    a sum-of-percentages by a sum-of-counts) even though it looked correct
    in isolation. 'other_water_services' must be a raw-count leftover
    (total available minus known categories, floored at 0) to match exactly
    how the Toilet section's 'other_services' is computed."""

    def test_returns_raw_counts_not_percentages(self):
        card = _make_card()
        card.hh_have_water_enc = list(range(500))
        counts = {
            "Individual connection": 300,
            "Shared connection": 100,
            "Water standpost": 50,
        }
        card.get_water_coverage = MagicMock(side_effect=lambda t: counts[t])

        individual, shared, standpost, other, water_data_available = card.Water_Info()

        self.assertEqual(individual, 300)
        self.assertEqual(shared, 100)
        self.assertEqual(standpost, 50)
        self.assertEqual(water_data_available, 500)
        # leftover count, not "100 - counts"
        self.assertEqual(other, 500 - (300 + 100 + 50))

    def test_other_services_floored_at_zero_when_categories_overlap(self):
        card = _make_card()
        card.hh_have_water_enc = list(range(10))
        counts = {
            "Individual connection": 7,
            "Shared connection": 4,
            "Water standpost": 2,
        }
        card.get_water_coverage = MagicMock(side_effect=lambda t: counts[t])

        *_, other, _ = card.Water_Info()

        self.assertEqual(other, 0)


class GetPercOfWaterCoverageTests(SimpleTestCase):
    """occupied_houses() returns a *list* of household numbers, not a count.
    get_perc_of_water_coverage() must len() it before dividing -- dividing by
    the list itself raises TypeError, which is exactly what happened the
    first time this helper was ever actually exercised in production."""

    def test_divides_by_household_count_not_the_list_itself(self):
        card = _make_card()
        card.occupied_houses = MagicMock(return_value=list(range(50)))
        card.get_water_coverage = MagicMock(return_value=25)

        percent = card.get_perc_of_water_coverage("Individual connection")

        self.assertEqual(percent, 50.0)

    def test_returns_zero_when_no_occupied_houses(self):
        card = _make_card()
        card.occupied_houses = MagicMock(return_value=[])
        card.get_water_coverage = MagicMock(return_value=0)

        percent = card.get_perc_of_water_coverage("Individual connection")

        self.assertEqual(percent, 0)


class SaveToiletTests(SimpleTestCase):
    """The toilet 'other_services' leftover must never go negative, even if
    the household-level counts overlap unexpectedly."""

    @patch("graphs.dashboard_card.DashboardData")
    def test_other_services_floored_at_zero(self, mock_dashboard_data):
        card = _make_card()
        card.slum = MagicMock()
        card.hh_have_toilet_enc = list(range(10))
        card.individual_toilet = MagicMock(return_value=6)
        card.ctb_count = MagicMock(return_value=3)
        card.shared_group_toilet_cnt = MagicMock(return_value=4)  # 6+3+4=13 > 10
        card.get_toilet_data = MagicMock(return_value=(0, 0, 0, 0))

        card.save_toilet()

        _, kwargs = mock_dashboard_data.objects.filter().update.call_args
        self.assertEqual(kwargs["other_services_toilet_coverage"], 0)


class CheckDashboardDataCommandTests(SimpleTestCase):
    """The check_dashboard_data management command must flag any city with
    a negative aggregate, skip cities with no DashboardData yet, and pass
    everything else -- this is the audit that would have caught the
    water/toilet 'other services' bug across every city, not just the ones
    someone happens to spot-check by hand."""

    @patch("graphs.management.commands.check_dashboard_data.City")
    @patch("graphs.management.commands.check_dashboard_data.DashboardData")
    def test_flags_negative_and_skips_empty_cities(self, mock_dashboard_data, mock_city):
        good_city = MagicMock(name="good_city")
        good_city.name.city_name = "GoodCity"
        bad_city = MagicMock(name="bad_city")
        bad_city.name.city_name = "BadCity"
        empty_city = MagicMock(name="empty_city")
        empty_city.name.city_name = "EmptyCity"

        mock_city.objects.all.return_value.order_by.return_value = [
            good_city,
            bad_city,
            empty_city,
        ]

        agg_by_city = {
            id(good_city): {
                "water_other_services__sum": 10.0,
                "waste_other_services__sum": 5.0,
                "other_services_toilet_coverage__sum": 20.0,
            },
            id(bad_city): {
                "water_other_services__sum": -100.0,
                "waste_other_services__sum": 5.0,
                "other_services_toilet_coverage__sum": 20.0,
            },
            id(empty_city): {
                "water_other_services__sum": None,
                "waste_other_services__sum": None,
                "other_services_toilet_coverage__sum": None,
            },
        }

        def fake_filter(city):
            result = MagicMock()
            result.aggregate.return_value = agg_by_city[id(city)]
            return result

        mock_dashboard_data.objects.filter.side_effect = fake_filter

        out = StringIO()
        call_command("check_dashboard_data", stdout=out)
        output = out.getvalue()

        self.assertIn("EmptyCity", output)
        self.assertIn("SKIP", output)
        self.assertIn("BadCity", output)
        self.assertIn("FAIL", output)
        self.assertIn("GoodCity", output)
        self.assertIn("OK", output)
        self.assertIn("1 city(ies) have negative aggregate fields.", output)


class PercentagesSummingTo100Tests(SimpleTestCase):
    """score_cards()'s Water/Toilet/Waste cards divide each category by the
    sum of all categories (not the survey total) so they can't exceed 100%
    -- but independently rounding each share to 2 decimals can still leave
    a +/-0.01 residual. _percentages_summing_to_100() must add that
    residual to the largest share so the displayed values always sum to
    exactly 100, without hiding any category's real proportional size."""

    def test_sums_to_exactly_100_despite_rounding(self):
        # 70/213=32.8638%, 91/213=42.7230%, 52/213=24.4131% independently
        # round to 32.86+42.72+24.41 = 100.09 -- 0.09 over 100.
        counts = [70, 91, 52]
        total = 213
        naive_rounded = [round((c / total) * 100, 2) for c in counts]
        residual = round(100 - sum(naive_rounded), 2)

        result = _percentages_summing_to_100(counts, total)

        self.assertEqual(round(sum(result), 2), 100.0)
        # only the largest share (index 1, the 91) absorbs the residual
        self.assertEqual(result[1], round(naive_rounded[1] + residual, 2))
        self.assertEqual(result[0], naive_rounded[0])
        self.assertEqual(result[2], naive_rounded[2])

    def test_returns_all_zeros_when_total_is_falsy(self):
        self.assertEqual(_percentages_summing_to_100([5, 3, 2], 0), [0, 0, 0])
        self.assertEqual(_percentages_summing_to_100([], None), [])

    def test_matches_input_length(self):
        result = _percentages_summing_to_100([10, 20, 30, 40, 50], 150)
        self.assertEqual(len(result), 5)
        self.assertEqual(round(sum(result), 2), 100.0)
