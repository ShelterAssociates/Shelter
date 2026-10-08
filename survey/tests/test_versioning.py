"""Starting a new version, going live, the RIM choices, and per-slum sync control."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from graphs.models import FollowupData, HouseholdData, SlumData
from master.models import Rapid_Slum_Appraisal
from mastersheet.models import ToiletConstruction
from survey import slum_sync, versioning
from survey.models import SlumAlias, SlumDataVersion, SlumVersionBackup
from survey.tests.support import make_city, make_slum

UUID_OLD = "11111111-1111-1111-1111-111111111111"
UUID_NEW = "22222222-2222-2222-2222-222222222222"


def populate_households(slum, city, number="101"):
    """One row in each household table the versioning registry covers."""
    HouseholdData.objects.create(
        slum=slum, city=city, household_number=number, submission_date=timezone.now(),
        rhs_data={"rhs_uuid": "sub-" + number},
    )
    FollowupData.objects.create(
        slum=slum, city=city, household_number=number, submission_date=timezone.now(),
        followup_data={"a": 1},
    )
    ToiletConstruction.objects.create(slum=slum, household_number=number)


def populate_rim(slum, city):
    SlumData.objects.create(slum=slum, city=city, submission_date=timezone.now(), rim_data={"General": {}})
    Rapid_Slum_Appraisal.objects.create(slum_name=slum, approximate_population="1250")


def populate(slum, city, number="101"):
    populate_households(slum, city, number)
    populate_rim(slum, city)


class StartNewVersionTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        populate(self.slum, self.city)
        self.user = User.objects.create(username="super", is_superuser=True)

    def test_backs_everything_up_and_leaves_the_live_tables_alone(self):
        result = versioning.start_new_version(self.slum.id, user=self.user)

        self.assertEqual(result["version"].version, 2)
        self.assertIsNone(result["version"].switched_on)
        # every live row is still there: the old version stays in use
        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 1)
        self.assertEqual(SlumData.objects.filter(slum=self.slum).count(), 1)
        self.assertEqual(Rapid_Slum_Appraisal.objects.filter(slum_name=self.slum).count(), 1)
        # and each one is backed up against the version it belonged to
        backups = SlumVersionBackup.objects.filter(slum=self.slum, version=1)
        self.assertEqual(backups.count(), 5)
        self.assertEqual(
            set(backups.values_list("source_model", flat=True)),
            {"graphs.HouseholdData", "graphs.FollowupData", "mastersheet.ToiletConstruction",
             "graphs.SlumData", "master.Rapid_Slum_Appraisal"},
        )

    def test_backup_keeps_the_row_contents(self):
        versioning.start_new_version(self.slum.id)
        row = SlumVersionBackup.objects.get(slum=self.slum, source_model="graphs.HouseholdData")
        self.assertEqual(row.data["fields"]["household_number"], "101")

    def test_versions_stack(self):
        versioning.start_new_version(self.slum.id)
        versioning.go_live(self.slum.id)
        # the re-survey fills the household tables again; RIM was never cleared
        populate_households(self.slum, self.city, number="202")
        versioning.start_new_version(self.slum.id)

        self.assertEqual(versioning.current_number(self.slum.id), 3)
        self.assertEqual(SlumVersionBackup.objects.filter(slum=self.slum, version=1).count(), 5)
        self.assertEqual(SlumVersionBackup.objects.filter(slum=self.slum, version=2).count(), 5)

    def test_other_slums_are_untouched(self):
        other = make_slum(self.city, name="Other Nagar", code="ON1")
        populate(other, self.city, number="301")
        versioning.start_new_version(self.slum.id)
        versioning.go_live(self.slum.id)

        self.assertEqual(HouseholdData.objects.filter(slum=other).count(), 1)
        self.assertFalse(SlumVersionBackup.objects.filter(slum=other).exists())


class GoLiveTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        populate(self.slum, self.city)

    def test_clears_household_tables_but_never_rim(self):
        versioning.start_new_version(self.slum.id)
        removed = versioning.go_live(self.slum.id)

        self.assertEqual(removed["Households"], 1)
        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 0)
        self.assertEqual(FollowupData.objects.filter(slum=self.slum).count(), 0)
        self.assertEqual(ToiletConstruction.objects.filter(slum=self.slum).count(), 0)
        # RIM is decided explicitly, so going live leaves it alone
        self.assertEqual(SlumData.objects.filter(slum=self.slum).count(), 1)
        self.assertEqual(Rapid_Slum_Appraisal.objects.filter(slum_name=self.slum).count(), 1)
        self.assertIsNotNone(versioning.latest_version(self.slum.id).switched_on)

    def test_a_version_made_outside_the_page_is_backed_up_before_clearing(self):
        """The admin can add a version directly; nothing may be deleted unbacked."""
        SlumDataVersion.objects.create(
            slum=self.slum, version=2, started_on=timezone.now(), switched_on=None,
        )
        self.assertFalse(SlumVersionBackup.objects.filter(slum=self.slum).exists())

        versioning.go_live(self.slum.id)

        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 0)
        backups = SlumVersionBackup.objects.filter(slum=self.slum, version=1)
        self.assertEqual(backups.count(), 5)
        self.assertEqual(
            backups.filter(source_model="graphs.HouseholdData").get().data["fields"]["household_number"], "101",
        )

    def test_an_existing_backup_is_not_doubled(self):
        versioning.start_new_version(self.slum.id)
        before = SlumVersionBackup.objects.filter(slum=self.slum, version=1).count()
        versioning.go_live(self.slum.id)
        self.assertEqual(SlumVersionBackup.objects.filter(slum=self.slum, version=1).count(), before)

    def test_go_live_is_idempotent(self):
        versioning.start_new_version(self.slum.id)
        versioning.go_live(self.slum.id)
        self.assertEqual(versioning.go_live(self.slum.id), {})

    def test_unversioned_slum_always_writes(self):
        self.assertTrue(versioning.allows_write(self.slum.id, timezone.now()))
        self.assertTrue(versioning.allows_write(None, timezone.now()))

    def test_new_record_switches_over_and_then_old_records_stay_out(self):
        versioning.start_new_version(self.slum.id)
        started = versioning.latest_version(self.slum.id).started_on

        # while the new version waits, the live tables still are the old version,
        # so an edit to old data belongs in them
        self.assertTrue(versioning.allows_write(self.slum.id, started - timedelta(days=1)))
        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 1)

        # the first record from after the start switches the live tables over
        self.assertTrue(versioning.allows_write(self.slum.id, started + timedelta(minutes=1)))
        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 0)

        # from then on an old record is kept out, whatever order records arrive in
        self.assertFalse(versioning.allows_write(self.slum.id, started - timedelta(days=1)))
        self.assertTrue(versioning.allows_write(self.slum.id, started + timedelta(days=1)))

    def test_record_with_no_date_does_not_switch(self):
        versioning.start_new_version(self.slum.id)
        self.assertTrue(versioning.allows_write(self.slum.id, None))
        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 1)


class RimChoiceTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        populate(self.slum, self.city)
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id=UUID_OLD, is_primary=True)
        SlumAlias.objects.create(slum=self.slum, provider="avni", external_id=UUID_NEW, is_primary=False)

    def test_keep_leaves_rim_in_place(self):
        versioning.start_new_version(self.slum.id, rim_choice=versioning.RIM_KEEP)
        self.assertEqual(SlumData.objects.filter(slum=self.slum).count(), 1)

    def test_clear_empties_rim_only(self):
        versioning.start_new_version(self.slum.id, rim_choice=versioning.RIM_CLEAR)
        self.assertEqual(SlumData.objects.filter(slum=self.slum).count(), 0)
        self.assertEqual(Rapid_Slum_Appraisal.objects.filter(slum_name=self.slum).count(), 0)
        # the household data is still live, because no new household has arrived
        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 1)
        # and the cleared rows are recoverable
        self.assertEqual(
            SlumVersionBackup.objects.filter(slum=self.slum, source_model="graphs.SlumData").count(), 1,
        )

    def test_resync_moves_the_rim_source(self):
        versioning.start_new_version(
            self.slum.id, rim_choice=versioning.RIM_RESYNC, rim_location=UUID_NEW,
        )
        primary = SlumAlias.objects.get(slum=self.slum, is_primary=True)
        self.assertEqual(primary.external_id, UUID_NEW)
        self.assertEqual(SlumData.objects.filter(slum=self.slum).count(), 0)

    def test_resync_needs_a_location(self):
        with self.assertRaises(ValueError):
            versioning.start_new_version(self.slum.id, rim_choice=versioning.RIM_RESYNC)
        # nothing was committed
        self.assertFalse(SlumDataVersion.objects.filter(slum=self.slum).exists())
        self.assertEqual(SlumData.objects.filter(slum=self.slum).count(), 1)

    def test_rim_source_must_be_mapped_here(self):
        with self.assertRaises(ValueError):
            versioning.set_rim_source(self.slum.id, "33333333-3333-3333-3333-333333333333")


class SlumSyncSettingTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)

    def test_absent_setting_means_synced_and_unlocked(self):
        self.assertTrue(slum_sync.is_enabled(self.slum.id))
        self.assertFalse(slum_sync.is_alias_locked(self.slum.id))
        self.assertTrue(slum_sync.is_enabled(None))

    def test_turning_sync_off(self):
        slum_sync.update(self.slum.id, sync_enabled=False, note="re-survey pending")
        self.assertFalse(slum_sync.is_enabled(self.slum.id))
        self.assertEqual(slum_sync.disabled_slum_ids(), {self.slum.id})
        # the lock is a separate decision and stays off
        self.assertFalse(slum_sync.is_alias_locked(self.slum.id))

    def test_locking_locations(self):
        slum_sync.update(self.slum.id, alias_locked=True)
        self.assertEqual(slum_sync.locked_slum_ids(), {self.slum.id})
        self.assertTrue(slum_sync.is_enabled(self.slum.id))

    def test_update_leaves_unnamed_flags_alone(self):
        slum_sync.update(self.slum.id, sync_enabled=False, alias_locked=True)
        slum_sync.update(self.slum.id, note="just a note")
        setting = slum_sync.setting_for(self.slum.id)
        self.assertFalse(setting.sync_enabled)
        self.assertTrue(setting.alias_locked)
        self.assertEqual(setting.note, "just a note")
