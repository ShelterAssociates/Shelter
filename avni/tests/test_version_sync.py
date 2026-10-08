"""AVNI numbers like "0002" are stored normalised ("2").

A real household sync against a slum that has been given a new data version:
the live tables switch over on the first new record, old records stay out, and a
second AVNI location feeds the same slum.
"""

from django.test import TestCase
from django.utils import timezone

from avni import paths
from avni.sync import households
from avni.tests.support import FakeApi, make_city, make_slum, page, subject_record
from graphs.models import HouseholdData
from survey import versioning
from survey.models import Record, SlumAlias, SlumVersionBackup

SINCE = "2020-01-01T00:00:00.000Z"
OLD_STAMP = "2026-01-01T00:00:00.000Z"
NEW_STAMP = "2027-01-01T00:00:00.000Z"
UUID_OLD = "loc-old"
UUID_NEW = "loc-new"


class VersionedHouseholdSyncTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.existing = HouseholdData.objects.create(
            slum=self.slum, city=self.city, household_number="1",
            submission_date=timezone.now(), rhs_data={"rhs_uuid": "old-sub"},
        )

    def sync(self, *records):
        path = paths.subjects("Household", SINCE)
        return households.sync_households(
            "Household", from_date=SINCE, api=FakeApi({path: page(list(records))}),
        )

    def test_without_a_new_version_everything_syncs_as_before(self):
        self.sync(subject_record("a", number="0002", modified=OLD_STAMP))
        self.assertEqual(HouseholdData.objects.filter(slum=self.slum).count(), 2)

    def test_the_first_new_record_clears_the_old_version_and_lands_alone(self):
        versioning.start_new_version(self.slum.id)
        self.sync(subject_record("a", number="0002", modified=NEW_STAMP))

        live = HouseholdData.objects.filter(slum=self.slum)
        self.assertEqual([row.household_number for row in live], ["2"])
        self.assertFalse(HouseholdData.objects.filter(id=self.existing.id).exists())
        # the old row is still readable in the backup
        self.assertEqual(
            SlumVersionBackup.objects.filter(
                slum=self.slum, version=1, source_model="graphs.HouseholdData",
            ).count(), 1,
        )

    def test_an_old_record_arriving_after_the_switch_stays_out_of_the_live_tables(self):
        versioning.start_new_version(self.slum.id)
        self.sync(
            subject_record("new", number="0002", modified=NEW_STAMP),
            subject_record("old", number="0003", modified=OLD_STAMP),
        )

        live = HouseholdData.objects.filter(slum=self.slum)
        self.assertEqual([row.household_number for row in live], ["2"])
        # but both are mirrored, each against its own version
        versions = dict(Record.objects.values_list("external_id", "version"))
        self.assertEqual(versions["new"], 2)
        self.assertEqual(versions["old"], 1)

    def test_a_household_number_can_repeat_in_the_new_version(self):
        versioning.start_new_version(self.slum.id)
        self.sync(subject_record("again", number="0001", modified=NEW_STAMP))

        live = HouseholdData.objects.filter(slum=self.slum)
        self.assertEqual([row.household_number for row in live], ["1"])
        self.assertEqual(live.get().rhs_data["rhs_uuid"], "again")
        self.assertEqual(Record.objects.get(external_id="again").version, 2)

    def test_a_second_location_title_feeds_the_same_slum(self):
        SlumAlias.objects.create(
            slum=self.slum, provider="avni", external_id=UUID_OLD,
            external_name=self.slum.name, is_primary=True,
        )
        SlumAlias.objects.create(
            slum=self.slum, provider="avni", external_id=UUID_NEW,
            external_name="Lokmanya Nagar New", is_primary=False,
        )
        versioning.start_new_version(self.slum.id)
        self.sync(subject_record("n", number="0007", slum="Lokmanya Nagar New", modified=NEW_STAMP))

        live = HouseholdData.objects.filter(slum=self.slum)
        self.assertEqual([row.household_number for row in live], ["7"])
        self.assertEqual(Record.objects.get(external_id="n").slum_id, self.slum.id)
