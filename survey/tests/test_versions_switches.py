"""Per-slum versions and the sync switch hierarchy."""

from django.test import TestCase
from django.utils import timezone

from survey import connector, contracts, switches, versions
from survey.models import SlumDataVersion, SyncSwitch
from survey.tests.fakes import FakeProvider
from survey.tests.support import make_city, make_slum


def moment(text):
    return timezone.make_aware(timezone.datetime.strptime(text, "%Y-%m-%d %H:%M"))


class VersionTests(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city())

    def start(self, version, when):
        return SlumDataVersion.objects.create(slum=self.slum, version=version, started_on=moment(when))

    def test_a_slum_with_no_versions_is_version_one(self):
        self.assertEqual(versions.version_for(self.slum.id, moment("2026-09-01 10:00")), 1)

    def test_before_the_start_stays_on_the_old_version(self):
        self.start(2, "2026-09-10 00:00")
        self.assertEqual(versions.version_for(self.slum.id, moment("2026-09-09 23:59")), 1)

    def test_on_the_start_moment_the_new_version_applies(self):
        self.start(2, "2026-09-10 00:00")
        self.assertEqual(versions.version_for(self.slum.id, moment("2026-09-10 00:00")), 2)

    def test_the_newest_started_version_wins(self):
        self.start(2, "2026-09-10 00:00")
        self.start(3, "2026-09-20 00:00")
        self.assertEqual(versions.version_for(self.slum.id, moment("2026-09-25 00:00")), 3)
        self.assertEqual(versions.version_for(self.slum.id, moment("2026-09-15 00:00")), 2)

    def test_a_record_with_no_slum_is_version_one(self):
        self.assertEqual(versions.version_for(None, moment("2026-09-25 00:00")), 1)

    def test_the_cache_is_read_once_per_slum(self):
        self.start(2, "2026-09-10 00:00")
        cache = {}
        versions.version_for(self.slum.id, moment("2026-09-25 00:00"), cache)
        SlumDataVersion.objects.all().delete()
        self.assertEqual(versions.version_for(self.slum.id, moment("2026-09-25 00:00"), cache), 2)


class SwitchTests(TestCase):
    def setUp(self):
        connector.use_provider(FakeProvider())
        self.addCleanup(connector.reset_provider)

    def switch(self, subject_type="Household", kind="subject", encounter_type="", program="", enabled=True):
        return SyncSwitch.objects.create(
            provider="fake", subject_type=subject_type, kind=kind, program=program,
            encounter_type=encounter_type, is_enabled=enabled,
        )

    def test_a_household_kind_with_no_row_is_enabled(self):
        self.assertTrue(switches.is_enabled("Household", "encounter", encounter_type="Water"))
        self.assertTrue(switches.is_enabled("Detailed Socio Economic Survey", "subject"))

    def test_other_subject_types_wait_for_their_switch(self):
        self.assertFalse(switches.is_enabled("Family Member", "subject"))
        self.assertFalse(switches.is_enabled("Toilet", "encounter", encounter_type="Cleaning"))
        self.switch(subject_type="Family Member")
        self.assertTrue(switches.is_enabled("Family Member", "subject"))
        self.assertTrue(switches.is_enabled("Family Member", "enrolment", program="MHM"))

    def test_a_blank_program_matches_any_program_row(self):
        self.switch(kind="program_encounter", program="Sanitation program", encounter_type="Daily Reporting", enabled=False)
        self.assertFalse(switches.is_enabled("Household", "program_encounter", encounter_type="Daily Reporting"))

    def test_its_own_flag_is_honoured(self):
        self.switch(kind="encounter", encounter_type="Water", enabled=False)
        self.assertFalse(switches.is_enabled("Household", "encounter", encounter_type="Water"))

    def test_a_disabled_subject_disables_its_children(self):
        self.switch(enabled=False)
        child = self.switch(kind="encounter", encounter_type="Water")
        self.assertFalse(switches.effective_enabled(child))
        self.assertFalse(switches.is_enabled("Household", "encounter", encounter_type="Water"))

    def test_a_disabled_subject_also_covers_children_with_no_row(self):
        self.switch(enabled=False)
        self.assertFalse(switches.is_enabled("Household", "program_encounter", encounter_type="Daily Reporting"))

    def test_re_enabling_the_parent_restores_the_children_untouched(self):
        parent = self.switch(enabled=False)
        child = self.switch(kind="encounter", encounter_type="Water")
        parent.is_enabled = True
        parent.save()
        self.assertTrue(switches.effective_enabled(child))
        self.assertTrue(child.is_enabled)

    def test_another_subject_type_is_unaffected(self):
        self.switch(enabled=False)
        self.switch(subject_type="Structure")
        self.assertTrue(switches.is_enabled("Structure", "subject"))

    def test_enabled_kinds_skips_off_and_unavailable_rows(self):
        self.switch()
        self.switch(kind="encounter", encounter_type="Water")
        self.switch(kind="encounter", encounter_type="Waste", enabled=False)
        gone = self.switch(kind="encounter", encounter_type="Old")
        SyncSwitch.objects.filter(pk=gone.pk).update(is_available=False)
        self.assertEqual(switches.enabled_encounter_types("Household"), ["Water"])

    def test_disabled_step_names_lists_only_the_off_steps(self):
        self.switch(enabled=False)
        steps = [
            ("households:Household", ("Household", "subject", "", "")),
            ("households:Structure", ("Structure", "subject", "", "")),
            ("dashboard", None),
        ]
        self.assertEqual(switches.disabled_step_names(steps), {"households:Household"})


class SyncCatalogTests(TestCase):
    def setUp(self):
        self.provider = FakeProvider()
        connector.use_provider(self.provider)
        self.addCleanup(connector.reset_provider)

    def entry(self, subject_type="Household", kind="subject", encounter_type="", label="Registration"):
        return contracts.CatalogEntry(
            subject_type=subject_type, kind=kind, encounter_type=encounter_type,
            label=label, form_external_id="form-1", concepts=[],
        )

    def test_rows_are_created_for_every_entry(self):
        self.provider.catalog_entries = [self.entry(), self.entry(kind="encounter", encounter_type="Water", label="Water form")]
        counts = switches.sync_catalog(self.provider)
        self.assertEqual(counts["created"], 2)
        self.assertEqual(SyncSwitch.objects.get(kind="encounter").label, "Water form")

    def test_household_types_arrive_on_and_others_off(self):
        self.provider.catalog_entries = [self.entry(), self.entry(subject_type="Family Member"), self.entry(subject_type="Toilet")]
        switches.sync_catalog(self.provider)
        self.assertTrue(SyncSwitch.objects.get(subject_type="Household").is_enabled)
        self.assertFalse(SyncSwitch.objects.get(subject_type="Family Member").is_enabled)
        self.assertFalse(SyncSwitch.objects.get(subject_type="Toilet").is_enabled)

    def test_a_form_that_vanished_is_marked_unavailable_not_deleted(self):
        self.provider.catalog_entries = [self.entry(), self.entry(kind="encounter", encounter_type="Water")]
        switches.sync_catalog(self.provider)
        self.provider.catalog_entries = [self.entry()]
        counts = switches.sync_catalog(self.provider)
        self.assertEqual(counts["deactivated"], 1)
        self.assertFalse(SyncSwitch.objects.get(kind="encounter").is_available)
        self.assertEqual(SyncSwitch.objects.count(), 2)

    def test_a_returning_form_becomes_available_again(self):
        self.provider.catalog_entries = [self.entry()]
        switches.sync_catalog(self.provider)
        SyncSwitch.objects.update(is_available=False, is_enabled=False)
        switches.sync_catalog(self.provider)
        row = SyncSwitch.objects.get()
        self.assertTrue(row.is_available)
        self.assertFalse(row.is_enabled, "an admin's off switch survives a catalog refresh")

    def test_running_it_twice_creates_nothing_new(self):
        self.provider.catalog_entries = [self.entry()]
        switches.sync_catalog(self.provider)
        self.assertEqual(switches.sync_catalog(self.provider)["created"], 0)
