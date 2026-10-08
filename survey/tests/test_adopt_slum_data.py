"""adopt_slum_data: move a re-survey's data onto the original slum."""

from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from component.models import Component, ComponentMetric
from graphs.models import FollowupData, HouseholdData, SlumData
from master.models import Rapid_Slum_Appraisal, Slum
from survey import versioning
from survey.models import SlumVersionBackup
from survey.tests.support import make_city, make_slum
from survey.tests.test_component_versions import add_component, make_metadata


class AdoptSlumDataTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.target = make_slum(self.city, name="Antule Nagar", code="AN1")
        self.source = make_slum(self.city, name="Antule Nagar New", code="AN2")

        self.shared = make_metadata("Structure")
        self.only_target = make_metadata("Chambers")
        self.only_source = make_metadata("Dambar road")

        # target: an older survey
        self.old_household = HouseholdData.objects.create(
            slum=self.target, city=self.city, household_number="1",
            submission_date=timezone.now(), rhs_data={"rhs_uuid": "old"},
        )
        FollowupData.objects.create(
            slum=self.target, city=self.city, household_number="1",
            submission_date=timezone.now(), followup_data={},
        )
        SlumData.objects.create(
            slum=self.target, city=self.city, submission_date=timezone.now(),
            rim_data={"General": {"landmark": "target"}},
        )
        Rapid_Slum_Appraisal.objects.create(slum_name=self.target, approximate_population="1250")
        add_component(self.target, self.shared, "t1")
        add_component(self.target, self.only_target, "t2")

        # source: the re-survey
        HouseholdData.objects.create(
            slum=self.source, city=self.city, household_number="1",
            submission_date=timezone.now(), rhs_data={"rhs_uuid": "new"},
        )
        HouseholdData.objects.create(
            slum=self.source, city=self.city, household_number="2",
            submission_date=timezone.now(), rhs_data={"rhs_uuid": "new2"},
        )
        add_component(self.source, self.shared, "s1")
        add_component(self.source, self.only_source, "s2")
        Rapid_Slum_Appraisal.objects.create(slum_name=self.source, approximate_population="999")

        versioning.start_new_version(self.target.id)

    def run_command(self, *extra):
        out = StringIO()
        call_command(
            "adopt_slum_data", "--from", str(self.source.id), "--into", str(self.target.id),
            stdout=out, *extra
        )
        return out.getvalue()

    def components_of(self, slum):
        return sorted(
            Component.objects.filter(
                content_type=ContentType.objects.get_for_model(Slum), object_id=slum.id,
            ).values_list("metadata__name", "housenumber")
        )

    def test_a_dry_run_changes_nothing(self):
        out = self.run_command()
        self.assertIn("DRY RUN", out)
        self.assertEqual(HouseholdData.objects.filter(slum=self.target).count(), 1)
        self.assertEqual(HouseholdData.objects.filter(slum=self.source).count(), 2)

    def test_the_dry_run_names_what_it_would_clear_and_move(self):
        out = self.run_command()
        self.assertIn("would clear from the target", out)
        self.assertIn("would move from the source", out)
        self.assertIn("RIM is not moved", out)

    def test_apply_clears_the_target_then_moves_the_source(self):
        self.run_command("--apply")

        rows = HouseholdData.objects.filter(slum=self.target)
        self.assertEqual(
            sorted(row.rhs_data["rhs_uuid"] for row in rows), ["new", "new2"],
        )
        self.assertFalse(HouseholdData.objects.filter(id=self.old_household.id).exists())
        self.assertFalse(HouseholdData.objects.filter(slum=self.source).exists())
        self.assertEqual(FollowupData.objects.filter(slum=self.target).count(), 0)

    def test_the_cleared_rows_are_still_in_the_backup(self):
        self.run_command("--apply")
        self.assertEqual(
            SlumVersionBackup.objects.filter(
                slum=self.target, version=1, source_model="graphs.HouseholdData",
            ).count(), 1,
        )

    def test_rim_is_left_on_both_slums(self):
        self.run_command("--apply")
        self.assertEqual(SlumData.objects.filter(slum=self.target).count(), 1)
        self.assertEqual(
            SlumData.objects.get(slum=self.target).rim_data["General"]["landmark"], "target",
        )
        self.assertEqual(Rapid_Slum_Appraisal.objects.filter(slum_name=self.target).count(), 1)
        self.assertEqual(Rapid_Slum_Appraisal.objects.filter(slum_name=self.source).count(), 1)

    def test_components_replace_per_layer_and_keep_the_rest(self):
        self.run_command("--apply")

        self.assertEqual(
            self.components_of(self.target),
            [("Chambers", "t2"), ("Dambar road", "s2"), ("Structure", "s1")],
        )
        self.assertEqual(self.components_of(self.source), [])

    def test_missing_only_leaves_the_shared_layer_alone(self):
        self.run_command("--apply", "--components", "missing-only")

        self.assertEqual(
            self.components_of(self.target),
            [("Chambers", "t2"), ("Dambar road", "s2"), ("Structure", "t1")],
        )
        self.assertEqual(self.components_of(self.source), [("Structure", "s1")])

    def test_all_replaces_every_component(self):
        self.run_command("--apply", "--components", "all")

        self.assertEqual(
            self.components_of(self.target), [("Dambar road", "s2"), ("Structure", "s1")],
        )

    def test_the_source_slum_is_kept(self):
        self.run_command("--apply")
        self.assertTrue(Slum.objects.filter(id=self.source.id).exists())

    def test_component_metrics_follow_their_layer(self):
        ComponentMetric.objects.create(slum=self.target, metadata=self.shared, value=1, unit="m")
        ComponentMetric.objects.create(slum=self.target, metadata=self.only_target, value=2, unit="m")
        ComponentMetric.objects.create(slum=self.source, metadata=self.shared, value=9, unit="m")

        self.run_command("--apply")

        held = dict(
            ComponentMetric.objects.filter(slum=self.target).values_list("metadata__name", "value")
        )
        self.assertEqual(int(held["Structure"]), 9, "the re-survey's metric replaces it")
        self.assertEqual(int(held["Chambers"]), 2, "a layer only the target has is untouched")

    def test_anything_unbacked_is_archived_before_a_row_is_removed(self):
        SlumVersionBackup.objects.filter(slum=self.target).delete()

        self.run_command("--apply")

        backed = SlumVersionBackup.objects.filter(slum=self.target, version=1)
        self.assertEqual(
            backed.filter(source_model="graphs.HouseholdData").count(), 1,
            "the household cleared from the target is recoverable",
        )
        self.assertTrue(backed.filter(source_model="component.Component").exists())

    def test_it_refuses_when_no_version_is_waiting(self):
        from survey.models import SlumDataVersion

        SlumDataVersion.objects.filter(slum=self.target).delete()
        with self.assertRaises(CommandError):
            self.run_command("--apply")
        self.assertEqual(HouseholdData.objects.filter(slum=self.target).count(), 1)

    def test_it_refuses_the_same_slum_twice(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command(
                "adopt_slum_data", "--from", str(self.target.id), "--into", str(self.target.id),
                stdout=out,
            )

    def test_a_dump_records_every_row_that_moves(self):
        import json
        import tempfile

        path = tempfile.mkstemp(suffix=".json")[1]
        self.run_command("--apply", "--dump", path)
        with open(path) as handle:
            payload = json.load(handle)
        self.assertEqual(len(payload["rows"]["graphs.householddata"]), 2)
        self.assertEqual(payload["components_mode"], "per-layer")
        self.assertIn("component.component.target", payload["rows"])
