"""Per-slum sync control and location filtering in the connector, the nightly
location match, the merge, and the superuser-only page.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from graphs.models import HouseholdData
from master.models import Slum
from notification.models import JobRun, JobStep
from notification.services import reporting
from survey import connector, locations, merging, slum_sync, versioning
from survey.models import Record, SlumAlias, SlumVersionBackup
from survey.store import SyncContext
from survey.tests.fakes import FakeProvider, raw
from survey.tests.support import make_city, make_slum, normalized

UUID_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
UUID_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


class ConnectorScopeTestCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.provider = FakeProvider()
        connector.use_provider(self.provider)
        self.addCleanup(connector.reset_provider)
        self.context = SyncContext(self.provider)


class SyncOffTests(ConnectorScopeTestCase):
    def test_a_slum_with_sync_on_is_stored_as_before(self):
        self.assertTrue(connector.sync_record("subject", raw(normalized()), self.context))
        self.assertEqual(Record.objects.count(), 1)

    def test_a_slum_with_sync_off_is_skipped_entirely(self):
        slum_sync.update(self.slum.id, sync_enabled=False)
        self.assertFalse(connector.sync_record("subject", raw(normalized()), self.context))
        self.assertEqual(Record.objects.count(), 0)
        self.assertEqual(HouseholdData.objects.count(), 0)
        self.assertEqual(self.provider.legacy_calls, [])
        self.assertEqual(self.context.counts["sync_off"], 1)

    def test_turning_sync_back_on_takes_effect_at_once(self):
        slum_sync.update(self.slum.id, sync_enabled=False)
        connector.sync_record("subject", raw(normalized()), self.context)
        slum_sync.update(self.slum.id, sync_enabled=True)
        self.assertTrue(connector.sync_record("subject", raw(normalized()), self.context))


class SyncOffReportingTests(TestCase):
    """Data arriving for a switched-off slum has to show up in the digest."""

    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        slum_sync.update(self.slum.id, sync_enabled=False)

    def test_the_step_counts_the_skip_and_names_the_slum(self):
        recorder = reporting.start("rhs_sync", trigger="manual")
        with recorder.step("households:Household"):
            slum_sync.report_skipped(self.slum.name)
            slum_sync.report_skipped(self.slum.name)
            slum_sync.report_skipped("Another Nagar")
        step = recorder.finish().steps.get()

        self.assertEqual(step.records_skipped, 3)
        self.assertEqual(
            step.extras[slum_sync.SYNC_OFF_EXTRA],
            ", ".join(sorted(["Another Nagar", self.slum.name])),
        )

    def test_the_digest_email_names_those_slums(self):
        from notification.services import email

        run = JobRun.objects.create(job_key="avni_daily_sync", status="success", started_on=timezone.now(),
                                    finished_on=timezone.now())
        JobStep.objects.create(run=run, name="households:Household", status="success", order=0,
                              records_ok=1, records_skipped=2,
                              extras={slum_sync.SYNC_OFF_EXTRA: self.slum.name})
        payload = email.digest_payload("08 Oct 2026", "OK", [run], [], [], timezone.now(), timezone.now())
        self.assertEqual(payload["runs"][0]["steps"][0]["sync_off_slums"], self.slum.name)
        self.assertIn(self.slum.name, "\n".join(email.run_lines(run)))


class LocationFilterTests(ConnectorScopeTestCase):
    def setUp(self):
        super(LocationFilterTests, self).setUp()
        self.other = make_slum(self.city, name="Other Nagar", code="ON9")
        SlumAlias.objects.create(slum=self.slum, provider="fake", external_id=UUID_A)
        SlumAlias.objects.create(slum=self.other, provider="fake", external_id=UUID_B)

    def test_no_filter_keeps_every_slum(self):
        self.assertIsNone(connector.slums_for_locations(None, self.context))
        self.assertIsNone(connector.slums_for_locations([], self.context))

    def test_locations_resolve_to_their_slums(self):
        self.assertEqual(connector.slums_for_locations([UUID_A], self.context), {self.slum.id})
        self.assertEqual(
            connector.slums_for_locations([UUID_A, UUID_B], self.context), {self.slum.id, self.other.id},
        )

    def test_an_unknown_location_filters_everything_out(self):
        self.assertEqual(connector.slums_for_locations(["no-such-uuid"], self.context), set())

    def test_records_outside_the_chosen_locations_are_left_alone(self):
        saved = connector.sync_record("subject", raw(normalized()), self.context, only_slums={self.other.id})
        self.assertFalse(saved)
        self.assertEqual(Record.objects.count(), 0)
        self.assertEqual(self.context.counts["out_of_scope"], 1)

    def test_records_inside_the_chosen_locations_are_stored(self):
        saved = connector.sync_record("subject", raw(normalized()), self.context, only_slums={self.slum.id})
        self.assertTrue(saved)
        self.assertEqual(Record.objects.count(), 1)

    def test_the_location_is_passed_down_to_the_provider(self):
        key = ("subject", "Household", "", "")
        self.provider.listings[key] = [raw(normalized())]
        connector.sync_kind("subject", "Household", context=self.context, locations=[UUID_A])
        self.assertEqual(self.provider.locations_asked, [UUID_A])


class SeveralLocationsTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_one_slum_can_hold_several_locations(self):
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id=UUID_A, is_primary=True)
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id=UUID_B, is_primary=False)

        self.assertEqual(locations.slum_external_id("avni", self.slum.id), UUID_A)
        self.assertEqual(locations.slum_external_ids("avni", self.slum.id), [UUID_A, UUID_B])
        self.assertEqual(locations.slum_ids_for("avni"), [self.slum.id])
        self.assertEqual(locations.slum_id_for_external_id("avni", UUID_B), self.slum.id)

    def test_an_alias_title_routes_records_to_its_slum(self):
        other = make_slum(self.city, name="Antule Nagar", code="AN1")
        SlumAlias.objects.create(
            slum=other, provider="avni", external_id=UUID_B, external_name="Antule Nagar New", is_primary=True,
        )
        self.assertEqual(locations.slum_id_for_title("Antule Nagar New"), other.id)
        self.assertEqual(locations.slum_and_city_ids("Antule Nagar New"), (other.id, self.city.id))
        # a plain slum name still resolves the way it always did
        self.assertEqual(locations.slum_and_city_ids(self.slum.name), (self.slum.id, self.city.id))

    def test_an_unknown_title_still_raises_lookuperror(self):
        with self.assertRaises(LookupError):
            locations.slum_and_city_ids("Nowhere Nagar")


class MergeTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.target = make_slum(self.city, name="Antule Nagar", code="AN1")
        self.source = make_slum(self.city, name="Antule Nagar New", code="AN2")
        SlumAlias.objects.create(slum=self.source, provider="avni", external_id=UUID_B, is_primary=True)
        self.household = HouseholdData.objects.create(
            slum=self.source, city=self.city, household_number="501",
            submission_date=timezone.now(), rhs_data={},
        )

    def test_dry_run_reports_what_would_move(self):
        report = merging.plan_merge(self.source.id, self.target.id)
        self.assertEqual(report["moving"]["graphs.householddata"], 1)
        self.assertEqual(report["blocked"], {})
        self.assertEqual(report["aliases"][0]["external_id"], UUID_B)
        # nothing changed
        self.assertTrue(Slum.objects.filter(id=self.source.id).exists())

    def test_merge_moves_the_data_and_deletes_the_source(self):
        moved = merging.merge(self.source.id, self.target.id, version=2)

        self.assertEqual(moved["graphs.householddata"], 1)
        self.assertFalse(Slum.objects.filter(id=self.source.id).exists())
        self.household.refresh_from_db()
        self.assertEqual(self.household.slum_id, self.target.id)
        alias = SlumAlias.objects.get(external_id=UUID_B)
        self.assertEqual(alias.slum_id, self.target.id)
        self.assertFalse(alias.is_primary)

    def test_moved_records_take_the_new_version(self):
        Record.objects.create(
            provider="avni", kind="subject", external_id="sub-501", version=1,
            slum=self.source, city=self.city, slum_name=self.source.name, household_number="501",
        )
        merging.merge(self.source.id, self.target.id, version=2)
        record = Record.objects.get(external_id="sub-501")
        self.assertEqual(record.slum_id, self.target.id)
        self.assertEqual(record.version, 2)
        self.assertEqual(record.slum_name, self.target.name)

    def test_a_clashing_household_number_blocks_the_merge(self):
        HouseholdData.objects.create(
            slum=self.target, city=self.city, household_number="501",
            submission_date=timezone.now(), rhs_data={},
        )
        report = merging.plan_merge(self.source.id, self.target.id)
        self.assertIn("graphs.householddata", report["blocked"])
        with self.assertRaises(ValueError):
            merging.merge(self.source.id, self.target.id)
        # refused without moving or deleting anything
        self.assertTrue(Slum.objects.filter(id=self.source.id).exists())
        self.household.refresh_from_db()
        self.assertEqual(self.household.slum_id, self.source.id)

    def test_an_unreadable_table_stops_the_merge(self):
        """A table whose columns do not match its model must not be stepped over."""
        from django.db import DatabaseError

        real = merging.rows_of

        def explode(relation, slum_id):
            if relation.related_model is HouseholdData:
                raise DatabaseError('column "nope" does not exist')
            return real(relation, slum_id)

        merging.rows_of = explode
        self.addCleanup(setattr, merging, "rows_of", real)

        report = merging.plan_merge(self.source.id, self.target.id)
        self.assertIn("graphs.householddata", report["unreadable"])
        with self.assertRaises(ValueError):
            merging.merge(self.source.id, self.target.id)
        self.assertTrue(Slum.objects.filter(id=self.source.id).exists())

    def test_a_slum_cannot_be_merged_into_itself(self):
        with self.assertRaises(ValueError):
            merging.merge(self.target.id, self.target.id)


class PageAccessTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.url = "/slum-versions/{}/".format(self.slum.id)

    def test_anonymous_is_refused(self):
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_a_staff_user_who_is_not_a_superuser_is_refused(self):
        User.objects.create_user("staffer", password="pw", is_staff=True)
        self.client.login(username="staffer", password="pw")
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_a_superuser_sees_the_page(self):
        User.objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.login(username="boss", password="pw")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.slum.name)


class PageActionTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        User.objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.login(username="boss", password="pw")
        HouseholdData.objects.create(
            slum=self.slum, city=self.city, household_number="101",
            submission_date=timezone.now(), rhs_data={},
        )

    def post(self, path, data):
        return self.client.post("/slum-versions/{}/{}".format(self.slum.id, path), data, follow=True)

    def test_starting_a_version_needs_the_confirmation_word(self):
        self.post("version/start/", {"confirm": "nope"})
        self.assertEqual(versioning.current_number(self.slum.id), 1)

        self.post("version/start/", {"confirm": "start", "rim_choice": versioning.RIM_KEEP})
        self.assertEqual(versioning.current_number(self.slum.id), 2)
        self.assertEqual(SlumVersionBackup.objects.filter(slum=self.slum).count(), 1)
        # the live row stays until new data arrives
        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 1)

    def test_mapping_a_location_and_moving_the_rim_source(self):
        self.post("locations/add/", {"external_id": UUID_A, "external_name": "First"})
        self.post("locations/add/", {"external_id": UUID_B, "external_name": "Second"})
        aliases = SlumAlias.objects.filter(slum=self.slum).order_by("-is_primary")
        self.assertEqual([a.is_primary for a in aliases], [True, False])
        self.assertEqual(aliases[0].external_id, UUID_A)

        self.post("locations/primary/", {"external_id": UUID_B})
        self.assertEqual(
            SlumAlias.objects.get(slum=self.slum, is_primary=True).external_id, UUID_B,
        )

    def test_a_location_already_mapped_elsewhere_is_refused(self):
        other = make_slum(self.city, name="Elsewhere", code="EW1")
        SlumAlias.objects.create(slum=other, provider="avni", external_id=UUID_A)
        self.post("locations/add/", {"external_id": UUID_A})
        self.assertFalse(SlumAlias.objects.filter(slum=self.slum).exists())

    def test_saving_the_sync_settings(self):
        self.post("settings/", {"alias_locked": "1", "note": "re-survey"})
        setting = slum_sync.setting_for(self.slum.id)
        self.assertFalse(setting.sync_enabled)
        self.assertTrue(setting.alias_locked)
        self.assertEqual(setting.note, "re-survey")
