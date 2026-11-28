"""The member summary (MemberDataETL): rebuilt from MemberData, nightly and on demand."""

import datetime
from unittest import mock

from django.test import TestCase

from avni.tests.support import make_city, make_slum
from graphs import member_data_analysis
from graphs.member_data_analysis import MemberDataProcess
from graphs.models import ETLLog, MemberData, MemberDataETL, MemberEncounterData
from notification.services import registry, reporting


class MemberSummaryTests(TestCase):
    def setUp(self):
        city = make_city("Pune")
        self.first = make_slum(city, name="Antule Nagar, Pisoli", code="AN1")
        self.second = make_slum(city, name="Indira Vasahat", code="IV1")

    def member(self, slum, uuid, number="42", data=None):
        return MemberData.objects.create(
            slum=slum, member_uuid=uuid, household_number=number, member_first_name="Asha", gender="2",
            date_of_birth=datetime.date(1960, 1, 1), created_date=datetime.date(2026, 1, 1),
            submission_date=datetime.date(2026, 1, 1),
            member_data={"Marital Status": "Widow"} if data is None else data)

    def test_refresh_copies_the_household_number(self):
        member = self.member(self.first, "m1", number="42")
        member_data_analysis.main()
        row = MemberDataETL.objects.get(member=member)
        self.assertEqual(row.household_number, "42")
        self.assertEqual(row.marital_status, "Widow")

    def test_refresh_picks_up_a_number_filled_later(self):
        member = self.member(self.first, "m1", number=None)
        member_data_analysis.main()
        MemberData.objects.filter(id=member.id).update(household_number="70")
        member_data_analysis.main()
        self.assertEqual(MemberDataETL.objects.get(member=member).household_number, "70")

    def test_member_without_answers_is_summarised(self):
        member = self.member(self.first, "m1")
        MemberData.objects.filter(id=member.id).update(member_data=None)
        member_data_analysis.main()
        self.assertTrue(MemberDataETL.objects.filter(member=member).exists())

    def test_follow_up_without_a_cup_answer_is_summarised(self):
        member = self.member(self.first, "m1")
        MemberEncounterData.objects.create(slum=self.first, member=member, encounter_data={},
                                           submission_date=datetime.date(2026, 2, 1))
        member_data_analysis.main()
        row = MemberDataETL.objects.get(member=member)
        self.assertEqual(row.cup_used_in_last_followup, "")
        self.assertEqual(row.available_followup_cnt, 1)

    def test_rebuild_keeps_one_row_per_member(self):
        member = self.member(self.first, "m1")
        member_data_analysis.main()
        member_data_analysis.main()
        self.assertEqual(MemberDataETL.objects.filter(member=member).count(), 1)

    def test_member_moved_to_another_slum_is_summarised_there_only(self):
        member = self.member(self.first, "m1")
        self.member(self.first, "m2")
        member_data_analysis.main()
        MemberData.objects.filter(id=member.id).update(slum=self.second)
        member_data_analysis.main()
        self.assertEqual(list(MemberDataETL.objects.filter(member=member).values_list("slum_id", flat=True)),
                         [self.second.id])

    def test_one_failing_slum_does_not_stop_the_others(self):
        self.member(self.first, "m1")
        kept = self.member(self.second, "m2")
        original = MemberDataProcess.save_member_data_metrics

        def fails_in_first_slum(process):
            if process.data.filter(slum=self.first).exists():
                raise RuntimeError("boom")
            return original(process)

        with mock.patch.object(MemberDataProcess, "save_member_data_metrics", fails_in_first_slum):
            totals = member_data_analysis.main()
        self.assertTrue(MemberDataETL.objects.filter(member=kept).exists())
        self.assertEqual(totals["failed_slums"], 1)
        self.assertIn(str(self.first.id), str(ETLLog.objects.latest("id").error_details))


class MemberSummaryJobTests(TestCase):
    def test_job_rebuilds_the_summary(self):
        member = MemberData.objects.create(
            slum=make_slum(make_city("Pune")), member_uuid="m1", household_number="42", member_first_name="Asha",
            gender="2", date_of_birth=datetime.date(1990, 1, 1), member_data={})
        recorder = reporting.start("member_summary", trigger="manual")
        registry.resolve("member_summary")(recorder, None)
        run = recorder.finish()
        self.assertEqual(run.steps.get(name="member_summary").status, "success")
        self.assertTrue(MemberDataETL.objects.filter(member=member).exists())
