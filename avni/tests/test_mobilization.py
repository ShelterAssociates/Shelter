"""Community mobilization subjects and activity attendance."""

from datetime import date

from django.test import TestCase

from avni import paths, watermark
from avni.sync import mobilization
from avni.tests.support import FakeApi, make_city, make_slum, page, subject_record
from graphs.models import HouseholdData
from mastersheet.models import ActivityType, CommunityMobilization, CommunityMobilizationActivityAttendance
from notification.services import reporting


def make_activity(name):
    activity = ActivityType.objects.create(name=name, key="0", display_order=1)
    activity.key = str(activity.id)
    activity.save()
    return activity


def mobilization_record(uuid="mob-1", activity="Samitee meeting 1", date_text="2026-02-01", voided=False, **attendees):
    observations = {"Type of Activity": activity, "Date of Survey": date_text}
    observations.update(attendees)
    return subject_record(uuid, voided=voided, number="", observations=observations)


class MobilizationTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.activity = make_activity("Samitee meeting 1")
        for number in ("1", "2", "3"):
            HouseholdData.objects.create(household_number=number, slum=self.slum, city=self.city,
                                         submission_date="2020-01-01T00:00:00Z", rhs_data={"x": 1})

    def test_creates_with_known_households_only(self):
        record = mobilization_record(**{
            "Household numbers for which activity attended by girls": "1,2,",
            "Household numbers for which activity attended by male members": "3,99",
        })
        mobilization.save_mobilization(record)
        row = CommunityMobilization.objects.get(slum=self.slum, activity_type=self.activity)
        self.assertEqual(row.household_number, ["1", "2", "3"])
        self.assertEqual(row.activity_date, date(2026, 2, 1))

    def test_alias_spelling_resolves_to_activity(self):
        mobilization.save_mobilization(mobilization_record(activity="Samiti meeting1"))
        self.assertEqual(CommunityMobilization.objects.count(), 1)

    def test_second_record_same_day_merges_households(self):
        mobilization.save_mobilization(mobilization_record(**{"Household numbers for which activity attended by girls": "1"}))
        mobilization.save_mobilization(mobilization_record("mob-2", **{"Household numbers for which activity attended by boys": "2"}))
        self.assertEqual(CommunityMobilization.objects.get().household_number, ["1", "2"])

    def test_zero_string_means_nobody(self):
        mobilization.save_mobilization(mobilization_record(**{"Household numbers for which activity attended by girls": "0"}))
        self.assertEqual(CommunityMobilization.objects.get().household_number, [])

    def test_unknown_activity_raises(self):
        with self.assertRaises(LookupError):
            mobilization.save_mobilization(mobilization_record(activity="Dance"))

    def test_sync_all_dates_uses_epoch_and_records(self):
        path = paths.subjects(mobilization.SUBJECT_TYPE, watermark.EPOCH)
        api = FakeApi({path: page([mobilization_record(), mobilization_record("v", voided=True), mobilization_record("bad", activity="Dance")])})
        recorder = reporting.start("mobilization_sync", trigger="manual")
        with recorder.step("mobilization"):
            saved = mobilization.sync_mobilization(from_date=watermark.EPOCH, api=api)
        step = recorder.finish().steps.get()
        self.assertEqual(saved, 1)
        self.assertEqual((step.records_ok, step.records_failed, step.records_skipped), (1, 1, 1))
        self.assertEqual(api.calls, [path])


class ActivityAttendanceTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.activity = make_activity("Workshop for Women")

    def test_create_then_update(self):
        observations = {"Type of Activity": "Workshop for Women", "Date of the activity conducted": "2026-03-03",
                        "Number of Women present": 5}
        mobilization.save_activity_attendance(observations, "Lokmanya Nagar", "42")
        row = CommunityMobilizationActivityAttendance.objects.get(household_number="42")
        self.assertEqual((row.females_attended_activity, row.males_attended_activity), (5, 0))
        observations["Number of Men present"] = 2
        mobilization.save_activity_attendance(observations, "Lokmanya Nagar", "42")
        row.refresh_from_db()
        self.assertEqual(row.males_attended_activity, 2)
        self.assertEqual(CommunityMobilizationActivityAttendance.objects.count(), 1)
