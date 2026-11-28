"""Households AVNI holds twice are kept apart and flagged, re-checked nightly, and mailed weekly per city;
visits entered twice are flagged."""

from unittest import mock

from django.test import TestCase
from django.utils import timezone

from avni.jobs import duplicates as job
from avni.provider import AvniProvider
from avni.tests.support import FakeApi, make_city, make_slum, program_encounter_record
from avni.tests.test_member_sync import household_record
from graphs.models import HouseholdData
from notification.models import EmailContact, EmailPurpose, EmailRecipient
from survey import connector, duplicates
from survey.models import Record, SyncDuplicate
from survey.store import SyncContext


class DuplicateCase(TestCase):
    def setUp(self):
        self.city = make_city("Pune")
        self.slum = make_slum(self.city)
        self.api = FakeApi()
        self.context = SyncContext(AvniProvider(api=self.api))

    def sync(self, record):
        self.api.routes["api/subject/" + record["ID"]] = record
        return connector.sync_record("subject", record, self.context)

    def first_and_twin(self):
        self.sync(household_record(uuid="hh-1", number="0042", observations={"Type of structure occupancy_1": "Shop"}))
        self.sync(household_record(uuid="hh-2", number="0042", observations={"Type of structure occupancy_1": "Occupied house"}))


class HouseholdDuplicateTests(DuplicateCase):
    def test_twin_is_not_merged_into_the_first_household(self):
        self.first_and_twin()
        row = HouseholdData.objects.get()
        self.assertEqual(row.rhs_data["rhs_uuid"], "hh-1")
        self.assertEqual(row.rhs_data.get("Type_of_structure_occupancy"), "Shop")

    def test_both_households_are_marked(self):
        self.first_and_twin()
        group = SyncDuplicate.objects.get()
        self.assertEqual((group.kind, group.status, group.household_number), ("household", "open", "42"))
        self.assertEqual(group.external_ids, ["hh-1", "hh-2"])
        self.assertEqual((group.slum_id, group.city_id), (self.slum.id, self.city.id))

    def test_seen_again_keeps_one_group(self):
        self.first_and_twin()
        self.sync(dict(household_record(uuid="hh-2", number="0042"), audit={
            "Created at": "2026-01-01T00:00:00.000Z", "Last modified at": "2026-10-01T00:00:00.000Z"}))
        self.assertEqual(SyncDuplicate.objects.count(), 1)


class RecheckTests(DuplicateCase):
    def test_voided_twin_closes_the_group_and_the_survivor_gets_the_row(self):
        self.first_and_twin()
        self.api.routes["api/subject/hh-1"] = household_record(uuid="hh-1", number="0042", voided=True,
                                                              modified="2026-10-01T00:00:00.000Z")
        counts = job.recheck(context=self.context)
        group = SyncDuplicate.objects.get()
        self.assertEqual((group.status, counts["resolved"]), ("resolved", 1))
        self.assertIn("1 voided", group.resolution)
        self.assertEqual(HouseholdData.objects.get().rhs_data["rhs_uuid"], "hh-2")

    def test_renumbered_twin_closes_the_group(self):
        self.first_and_twin()
        self.api.routes["api/subject/hh-2"] = household_record(uuid="hh-2", number="0043", modified="2026-10-01T00:00:00.000Z")
        job.recheck(context=self.context)
        self.assertEqual(SyncDuplicate.objects.get().status, "resolved")
        self.assertEqual(sorted(HouseholdData.objects.values_list("household_number", flat=True)), ["42", "43"])

    def test_still_two_live_households_stays_open(self):
        self.first_and_twin()
        counts = job.recheck(context=self.context)
        self.assertEqual((SyncDuplicate.objects.get().status, counts["open"]), ("open", 1))

    def test_resolved_group_reopens_when_it_comes_back(self):
        self.first_and_twin()
        duplicates.resolve(SyncDuplicate.objects.get(), "test")
        duplicates.remember_household("avni", self.slum.id, self.city.id, "42", ["hh-1", "hh-3"])
        group = SyncDuplicate.objects.get()
        self.assertEqual((group.status, group.external_ids), ("open", ["hh-1", "hh-2", "hh-3"]))


class EncounterDuplicateTests(DuplicateCase):
    def visit(self, uuid, day="2026-09-03T10:00:00.000Z"):
        record = program_encounter_record(uuid=uuid, encounter_type="Menstrual hygiene Follow-up", subject_uuid="mem-1",
                                          observations={"Q": "A"}, modified="2026-09-04T00:00:00.000Z")
        record.update({"Subject type": "Family Member", "Program": "Menstrual hygiene", "Enrolment ID": "enr-1",
                       "Encounter date time": day})
        return record

    def store(self, record, answer="2026-08-20"):
        from survey.models import Answer, Concept

        stored = Record.objects.create(provider="avni", kind="program_encounter", external_id=record["ID"],
                                       subject_external_id="mem-1", encounter_type="Menstrual hygiene Follow-up",
                                       record_datetime=record["Encounter date time"], slum=self.slum, city=self.city)
        question, _ = Concept.objects.get_or_create(key="last-period-date", defaults={"name": "Last period date", "data_type": "date"})
        Answer.objects.create(record=stored, question=question, value_text=answer)
        return stored

    def test_same_day_with_other_answers_is_not_a_duplicate(self):
        self.store(self.visit("v-1"), answer="2026-07-20")
        self.store(self.visit("v-2"), answer="2026-08-20")
        self.assertIsNone(duplicates.flag_encounter("avni", "v-2"))

    def test_same_subject_type_and_day_is_flagged(self):
        self.store(self.visit("v-1"))
        self.store(self.visit("v-2", day="2026-09-03T15:00:00.000Z"))
        group = duplicates.flag_encounter("avni", "v-2")
        self.assertEqual((group.kind, group.external_ids), ("encounter", ["v-1", "v-2"]))

    def test_another_day_is_not_a_duplicate(self):
        self.store(self.visit("v-1"))
        self.store(self.visit("v-2", day="2026-09-10T10:00:00.000Z"))
        self.assertIsNone(duplicates.flag_encounter("avni", "v-2"))

    def test_group_closes_after_a_void(self):
        self.store(self.visit("v-1"))
        self.store(self.visit("v-2"))
        duplicates.flag_encounter("avni", "v-2")
        Record.objects.filter(external_id="v-1").update(is_voided=True)
        self.assertEqual(duplicates.recheck_encounters("avni"), 1)
        self.assertEqual(SyncDuplicate.objects.get().status, "resolved")

    def test_whole_store_scan_flags_existing_twins(self):
        self.store(self.visit("v-1"))
        self.store(self.visit("v-2"))
        self.store(self.visit("v-3", day="2026-09-20T10:00:00.000Z"))
        self.assertEqual(duplicates.flag_stored_encounters("avni"), 1)


class DigestTests(DuplicateCase):
    def recipients(self, city_name, to="team@example.org", cc="lead@example.org"):
        purpose = EmailPurpose.objects.create(key=job.purpose_key(city_name), display_name="Duplicates " + city_name)
        for address, kind in ((to, "to"), (cc, "cc")):
            contact = EmailContact.objects.create(name=address, email=address)
            EmailRecipient.objects.create(purpose=purpose, contact=contact, kind=kind)

    def test_each_city_team_gets_its_open_duplicates(self):
        self.first_and_twin()
        self.recipients("Pune")
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            sent = job.send_digest()
        self.assertEqual(sent, {"Pune": 1})
        args, kwargs = send.call_args
        self.assertEqual(args[0], ["team@example.org"])
        self.assertEqual(kwargs["cc"], ["lead@example.org"])
        self.assertEqual([kind["count"] for kind in kwargs["context"]["kinds"]], [1])
        name, content, mimetype = kwargs["attachments"][0]
        self.assertTrue(name.startswith("duplicates_pune_") and name.endswith(".xlsx"))
        self.assertIsNotNone(SyncDuplicate.objects.get().notified_on)

    def test_sheet_lists_each_group_and_what_to_do(self):
        import io
        from openpyxl import load_workbook

        self.first_and_twin()
        name, content, mimetype = job.workbook(list(SyncDuplicate.objects.all()), "Pune")
        book = load_workbook(io.BytesIO(content))
        self.assertEqual(book.sheetnames, ["Read me", "Same number"])
        readme = list(book["Read me"].iter_rows(values_only=True))
        self.assertIn("एकच घर क्रमांक", readme[1][2])
        rows = list(book["Same number"].iter_rows(values_only=True))
        self.assertEqual((rows[1][0], rows[1][3]), ("Pune", "42"))
        self.assertIn("Void the wrong household", rows[1][11])

    def test_city_without_recipients_is_not_mailed(self):
        self.first_and_twin()
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            self.assertEqual(job.send_digest(), {})
        send.assert_not_called()

    def test_resolved_groups_are_not_mailed(self):
        self.first_and_twin()
        duplicates.resolve(SyncDuplicate.objects.get(), "test")
        self.recipients("Pune")
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            self.assertEqual(job.send_digest(), {})

    def test_mail_renders(self):
        self.first_and_twin()
        self.recipients("Pune")
        with mock.patch("helpers.services.send_email.EmailMultiAlternatives") as message:
            job.send_digest(today=timezone.now())
        self.assertTrue(message.called)


class FirstMailTests(DuplicateCase):
    recipients = DigestTests.recipients

    def test_first_mail_explains_the_list_once(self):
        self.first_and_twin()
        self.recipients("Pune")
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            job.send_digest()
        self.assertTrue(send.call_args[1]["context"]["first"])
        duplicates.remember_household("avni", self.slum.id, self.city.id, "43", ["hh-8", "hh-9"])
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            job.send_digest()
        self.assertFalse(send.call_args[1]["context"]["first"])

    def test_first_mail_names_the_financial_year(self):
        self.first_and_twin()
        self.recipients("Pune")
        with mock.patch("helpers.services.send_email.EmailMultiAlternatives") as message:
            job.send_digest(today=timezone.make_aware(timezone.datetime(2026, 11, 30, 9)))
        html = message.return_value.attach_alternative.call_args[0][0]
        self.assertIn("FY 2026-27", html)
        self.assertIn("Working slum this year", html)
        self.assertIn("पहिली यादी", html)


class NightlyDigestTests(DuplicateCase):
    def test_digest_counts_duplicates_apart_from_failures(self):
        from notification.services import email

        self.first_and_twin()
        since = timezone.now() - timezone.timedelta(days=1)
        counts = email.duplicate_counts(since, timezone.now())
        self.assertEqual(counts, {"households": 1, "visits": 0, "new": 1, "resolved": 0})
        payload = email.digest_payload("28 Nov 2026", "OK", [], [], [], since, timezone.now())
        self.assertEqual(payload["duplicates"]["households"], 1)
        self.assertIn("Duplicates: 1 household", email.nightly_text("28 Nov 2026", "OK", [], [], [], since, timezone.now()))


class TestMailTests(DuplicateCase):
    def test_test_mail_goes_only_to_the_test_address_and_marks_nothing(self):
        self.first_and_twin()
        DigestTests.recipients(self, "Pune")
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            sent = job.send_digest(test_to="dev@example.org")
        args, kwargs = send.call_args
        self.assertEqual((args[0], kwargs["cc"], kwargs["bcc"]), (["dev@example.org"], [], []))
        self.assertTrue(args[1].startswith("[TEST] "))
        self.assertEqual(sent, {"Pune": 1})
        self.assertIsNone(SyncDuplicate.objects.get().notified_on)
        self.assertTrue(kwargs["context"]["first"])

    def test_test_mail_covers_cities_without_recipients(self):
        self.first_and_twin()
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            self.assertEqual(job.send_digest(test_to="dev@example.org"), {"Pune": 1})
        self.assertIn("would go to: nobody yet", send.call_args[1]["context"]["test_note"])


class InMailTests(DuplicateCase):
    def test_groups_kept_out_of_the_mail_are_not_mailed(self):
        self.first_and_twin()
        SyncDuplicate.objects.update(in_mail=False)
        DigestTests.recipients(self, "Pune")
        with mock.patch("avni.jobs.duplicates.send_email") as send:
            self.assertEqual(job.send_digest(), {})
        send.assert_not_called()

    def test_seen_again_keeps_the_choice(self):
        self.first_and_twin()
        SyncDuplicate.objects.update(in_mail=False)
        duplicates.remember_household("avni", self.slum.id, self.city.id, "42", ["hh-1", "hh-2"])
        self.assertFalse(SyncDuplicate.objects.get().in_mail)
