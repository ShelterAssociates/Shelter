"""Exporting AVNI records to a JSON-lines bundle, and loading a bundle with no AVNI calls."""

import csv
import json
import os
import tempfile
from unittest import mock

from django.test import TestCase

from avni import bundle, paths
from avni.client import AvniError, client, reset_client
from avni.tests.support import FakeApi, make_city, make_slum
from avni.tests.test_member_sync import enrolment_record, follow_up_record, household_record, member_record
from graphs.models import HouseholdData, MemberData, MemberEncounterData, MemberProgramData


class BundleCase(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city())
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "bundle.jsonl")

    def tearDown(self):
        reset_client()

    def write_bundle(self, *items):
        with open(self.path, "w", encoding="utf-8") as handle:
            for kind, record in items:
                handle.write(json.dumps({"kind": kind, "id": record["ID"], "record": record}) + "\n")
        return self.path

    def load(self, apply=True):
        return bundle.load(self.path, apply=apply, report=os.path.join(self.folder, "report.csv"), out=lambda line: None)


class ExportTests(BundleCase):
    def ids(self, *rows):
        path = os.path.join(self.folder, "ids.csv")
        with open(path, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["kind", "uuid"])
            writer.writerows(rows)
        return path

    def lines(self):
        with open(self.path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]

    def test_each_record_is_fetched_by_its_kind(self):
        api = FakeApi({paths.subject("hh-1"): household_record(), paths.program_enrolment("enr-1"): enrolment_record(),
                       paths.program_encounter("fol-1"): follow_up_record()})
        bundle.export(self.ids(("subject", "hh-1"), ("enrolment", "enr-1"), ("program_encounter", "fol-1")),
                      self.path, api=api, out=lambda line: None)
        self.assertEqual([(line["kind"], line["id"]) for line in self.lines()],
                         [("subject", "hh-1"), ("enrolment", "enr-1"), ("program_encounter", "fol-1")])

    def test_a_record_avni_does_not_have_is_noted(self):
        bundle.export(self.ids(("subject", "gone")), self.path, api=FakeApi(), out=lambda line: None)
        self.assertEqual(self.lines()[0]["missing"], 404)

    def test_export_resumes_where_it_stopped(self):
        api = FakeApi({paths.subject("hh-1"): household_record(), paths.subject("hh-2"): household_record(uuid="hh-2")})
        ids = self.ids(("subject", "hh-1"))
        bundle.export(ids, self.path, api=api, out=lambda line: None)
        bundle.export(self.ids(("subject", "hh-1"), ("subject", "hh-2")), self.path, api=api, out=lambda line: None)
        self.assertEqual([line["id"] for line in self.lines()], ["hh-1", "hh-2"])
        self.assertEqual(api.calls.count(paths.subject("hh-1")), 1)


class FileApiTests(BundleCase):
    def test_serves_bundle_records_and_nothing_else(self):
        api = bundle.FileApi({("subject", "hh-1"): household_record()})
        self.assertEqual(api.get_json(paths.subject("hh-1"))["ID"], "hh-1")
        with self.assertRaises(AvniError):
            api.get_json(paths.subject("other"))
        self.assertEqual(list(api.iter_pages(paths.subjects("Household", "2026-01-01"))), [[]])

    def test_load_never_reaches_avni(self):
        self.write_bundle(("subject", member_record(groups=("not-in-bundle",))), ("enrolment", enrolment_record()))
        with mock.patch("avni.client.requests.request", side_effect=AssertionError("network call")) as request:
            self.load()
        request.assert_not_called()
        self.assertNotIsInstance(client(), bundle.FileApi)


class LoadTests(BundleCase):
    def test_missing_household_is_created(self):
        self.write_bundle(("subject", household_record(number="0042")))
        self.load()
        self.assertTrue(HouseholdData.objects.filter(slum=self.slum, household_number="42").exists())

    def test_dry_run_writes_nothing(self):
        self.write_bundle(("subject", household_record(number="0042")))
        counts = self.load(apply=False)
        self.assertFalse(HouseholdData.objects.exists())
        self.assertEqual(counts["saved"], 1)

    def test_voided_household_is_removed(self):
        self.write_bundle(("subject", household_record(number="0042")))
        self.load()
        self.write_bundle(("subject", household_record(number="0042", voided=True)))
        self.load()
        self.assertFalse(HouseholdData.objects.exists())

    def test_member_household_and_enrolment_load_in_order(self):
        self.write_bundle(("enrolment", enrolment_record()), ("subject", member_record()),
                          ("subject", household_record(number="0042")), ("program_encounter", follow_up_record()))
        self.load()
        member = MemberData.objects.get(member_uuid="mem-1")
        self.assertEqual(member.household_number, "42")
        self.assertTrue(MemberProgramData.objects.filter(member=member, program_uuid="enr-1").exists())
        self.assertTrue(MemberEncounterData.objects.filter(member=member, encounter_uuid="fol-1").exists())

    def test_enrolment_older_than_the_stored_one_is_skipped(self):
        self.write_bundle(("subject", household_record(number="0042")), ("subject", member_record()),
                          ("enrolment", enrolment_record(uuid="enr-new")))
        self.load()
        older = enrolment_record(uuid="enr-old")
        older["Enrolment datetime"] = "2025-01-01T00:00:00.000Z"
        older["audit"]["Created at"] = "2025-01-01T00:00:00.000Z"
        self.write_bundle(("enrolment", older))
        counts = self.load()
        self.assertEqual(MemberProgramData.objects.get().program_uuid, "enr-new")
        self.assertEqual(counts["older than stored"], 1)

    def test_link_lines_give_old_rows_their_avni_id(self):
        old = HouseholdData.objects.create(household_number="42", slum=self.slum, city=self.slum.electoral_ward.administrative_ward.city,
                                           submission_date="2020-01-01T00:00:00Z", rhs_data={"Type_of_survey": "RHS"})
        held = HouseholdData.objects.create(household_number="43", slum=self.slum, city=old.city,
                                            submission_date="2020-01-01T00:00:00Z", rhs_data={"rhs_uuid": "kept"})
        with open(self.path, "w", encoding="utf-8") as handle:
            for number, uuid in (("42", "hh-42"), ("43", "hh-43")):
                handle.write(json.dumps({"kind": "link", "slum_id": self.slum.id, "number": number, "uuid": uuid}) + "\n")
        counts = self.load()
        old.refresh_from_db()
        held.refresh_from_db()
        self.assertEqual(old.rhs_data["rhs_uuid"], "hh-42")
        self.assertEqual(old.rhs_data["Type_of_survey"], "RHS")
        self.assertEqual(held.rhs_data["rhs_uuid"], "kept")
        self.assertEqual(counts["linked"], 1)

    def test_report_lists_every_record(self):
        self.write_bundle(("subject", household_record(number="0042")), ("enrolment", enrolment_record(member="ghost")))
        self.load()
        with open(os.path.join(self.folder, "report.csv"), encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([(row["kind"], row["id"], row["result"]) for row in rows],
                         [("subject", "hh-1", "saved"), ("enrolment", "enr-1", "not saved")])
