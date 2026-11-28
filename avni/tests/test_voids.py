"""Anything voided in AVNI stops counting here; a voided household takes its members and their records along."""

from django.test import TestCase

from avni.provider import AvniProvider
from avni.tests.support import FakeApi, make_city, make_slum
from avni.tests.test_member_sync import enrolment_record, follow_up_record, household_record, member_record
from graphs.models import FollowupData, HouseholdData, MemberData, MemberDataETL, MemberEncounterData, MemberProgramData
from survey import connector
from survey.store import SyncContext


class VoidCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.api = FakeApi()
        self.context = SyncContext(AvniProvider(api=self.api))

    def sync(self, kind, record):
        self.api.routes["api/subject/" + record["ID"]] = record if kind == "subject" else self.api.routes.get(
            "api/subject/" + record["ID"])
        return connector.sync_record(kind, record, self.context)

    def seed_household_with_member(self):
        self.sync("subject", household_record(number="0042"))
        self.sync("subject", member_record())
        self.sync("enrolment", enrolment_record())
        self.sync("program_encounter", follow_up_record())
        FollowupData.objects.create(household_number="42", slum=self.slum, city=self.city,
                                    submission_date="2026-01-01T00:00:00Z", followup_data={})
        self.assertEqual(MemberData.objects.get().household_number, "42")


class VoidedHouseholdTests(VoidCase):
    def test_members_and_their_records_go_with_the_household(self):
        self.seed_household_with_member()
        self.sync("subject", household_record(number="0042", voided=True))
        self.assertFalse(HouseholdData.objects.exists())
        self.assertFalse(MemberData.objects.exists())
        self.assertFalse(MemberProgramData.objects.exists())
        self.assertFalse(MemberEncounterData.objects.exists())
        self.assertFalse(FollowupData.objects.exists())

    def test_a_row_now_held_by_another_household_keeps_its_records(self):
        self.seed_household_with_member()
        HouseholdData.objects.update(rhs_data={"rhs_uuid": "hh-2"})
        self.sync("subject", household_record(number="0042", voided=True))
        self.assertTrue(HouseholdData.objects.filter(rhs_data__contains="hh-2").exists())
        self.assertTrue(MemberData.objects.exists())
        self.assertTrue(FollowupData.objects.exists())

    def test_member_summary_row_goes_too(self):
        self.seed_household_with_member()
        member = MemberData.objects.get()
        MemberDataETL.objects.create(slum=self.slum, member=member, household_number="42")
        self.sync("subject", household_record(number="0042", voided=True))
        self.assertFalse(MemberDataETL.objects.exists())


class VoidedMemberRecordTests(VoidCase):
    def test_voided_member_is_removed_with_her_records(self):
        self.seed_household_with_member()
        self.sync("subject", dict(member_record(), Voided=True))
        self.assertFalse(MemberData.objects.exists())
        self.assertFalse(MemberProgramData.objects.exists())
        self.assertTrue(HouseholdData.objects.exists())

    def test_voided_enrolment_is_removed(self):
        self.seed_household_with_member()
        self.sync("enrolment", enrolment_record(voided=True))
        self.assertFalse(MemberProgramData.objects.exists())
        self.assertTrue(MemberData.objects.exists())

    def test_voided_follow_up_is_removed(self):
        self.seed_household_with_member()
        record = follow_up_record()
        record["Voided"] = True
        self.sync("program_encounter", record)
        self.assertFalse(MemberEncounterData.objects.exists())
        self.assertTrue(MemberProgramData.objects.exists())
