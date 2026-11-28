"""Records of a duplicate household (its members, their programme records, its forms) wait until AVNI resolves
the duplicate, then sync; programme work recorded on such a household is mailed to the city team."""

from unittest import mock

from django.test import TestCase

from avni.jobs import duplicates as job
from avni.provider import AvniProvider
from avni.tests.support import FakeApi, encounter_record, make_city, make_slum
from avni.tests.test_member_sync import enrolment_record, follow_up_record, household_record, member_record
from graphs.models import HouseholdData, MemberData, MemberProgramData
from notification.models import EmailContact, EmailPurpose, EmailRecipient
from survey import connector
from survey.models import SyncDuplicate
from survey.store import SyncContext


class HoldCase(TestCase):
    def setUp(self):
        self.city = make_city("Pune")
        self.slum = make_slum(self.city)
        self.api = FakeApi()
        self.context = SyncContext(AvniProvider(api=self.api))
        self.sync("subject", household_record(uuid="hh-1", number="0042"))
        self.sync("subject", household_record(uuid="hh-2", number="0042"))

    def sync(self, kind, record):
        if kind == "subject":
            self.api.routes["api/subject/" + record["ID"]] = record
        return connector.sync_record(kind, record, self.context)

    def group(self):
        return SyncDuplicate.objects.get(kind="household")


class HoldTests(HoldCase):
    def test_member_of_a_duplicate_household_waits(self):
        self.sync("subject", member_record(groups=("hh-2",)))
        self.assertFalse(MemberData.objects.exists())
        self.assertIn(["subject", "mem-1"], self.group().details["held"])

    def test_programme_records_of_her_wait_and_are_flagged(self):
        self.api.routes["api/subject/mem-1"] = member_record(groups=("hh-1",))
        self.sync("enrolment", enrolment_record())
        self.assertFalse(MemberProgramData.objects.exists())
        alerts = self.group().details["alerts"]
        self.assertEqual([alert["what"] for alert in alerts], ["Menstrual hygiene enrolment"])

    def test_sanitation_form_on_a_duplicate_household_waits_and_is_flagged(self):
        form = encounter_record(uuid="enc-1", subject_uuid="hh-2", encounter_type="Sanitation",
                                observations={"Current place of defecation": "Own toilet"})
        self.sync("encounter", form)
        self.assertNotIn("group_oi8ts04/Current_place_of_defecation", HouseholdData.objects.get().rhs_data)
        self.assertEqual(self.group().details["alerts"][0]["what"], "Sanitation form")

    def test_other_households_are_not_held(self):
        self.sync("subject", household_record(uuid="hh-9", number="0099"))
        self.sync("subject", member_record(uuid="mem-9", groups=("hh-9",)))
        self.assertTrue(MemberData.objects.filter(member_uuid="mem-9").exists())


class ReleaseTests(HoldCase):
    def test_held_records_sync_once_the_duplicate_is_resolved(self):
        self.sync("subject", member_record(groups=("hh-2",)))
        self.api.routes["api/subject/hh-1"] = household_record(uuid="hh-1", number="0042", voided=True,
                                                              modified="2026-10-01T00:00:00.000Z")
        job.recheck(context=self.context)
        self.assertEqual(self.group().status, "resolved")
        self.assertEqual(MemberData.objects.get().household_number, "42")
        self.assertEqual(self.group().details.get("held"), [])


class AlertMailTests(HoldCase):
    def recipients(self):
        purpose = EmailPurpose.objects.create(key=job.purpose_key("Pune"), display_name="Duplicates Pune")
        EmailRecipient.objects.create(purpose=purpose, contact=EmailContact.objects.create(name="t", email="pmc@example.org"))

    def test_work_on_a_duplicate_household_is_mailed_once(self):
        self.recipients()
        self.api.routes["api/subject/mem-1"] = member_record(groups=("hh-1",))
        self.sync("program_encounter", follow_up_record())
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            self.assertEqual(job.send_alerts(), {"Pune": 1})
            self.assertEqual(job.send_alerts(), {})
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args[0][0], ["pmc@example.org"])
        self.assertEqual(self.group().details["alerts"], [])
        self.assertEqual(len(self.group().details["alerted"]), 1)
