"""The Metabase views in DBScripts apply cleanly and read the core tables."""

import os

from django.conf import settings
from django.db import connection
from django.test import TestCase

from survey import store
from survey.tests.fakes import FakeProvider
from survey.tests.support import make_city, make_slum, normalized, observation

SCRIPTS = os.path.join(settings.BASE_DIR, "DBScripts")
VIEWS = ("vw_survey_households.sql", "vw_survey_encounters.sql", "vw_survey_answers.sql")


def apply(name):
    with open(os.path.join(SCRIPTS, name)) as handle:
        sql = handle.read()
    with connection.cursor() as cursor:
        cursor.execute(sql)


def rows(sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


class MetabaseViewTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        context = store.SyncContext(FakeProvider())
        store.upsert(normalized(observations=[observation("Members", "4", "numeric")]), context)
        store.upsert(normalized(kind="encounter", external_id="enc-1", subject_external_id="sub-1",
                                encounter_type="Sanitation", household_number="",
                                observations=[observation("Toilet users", "Men", "coded", answer_name="Men")]), context)
        store.upsert(normalized(kind="encounter", external_id="enc-2", subject_external_id="sub-1",
                                encounter_type="Water", household_number="", record_datetime=None,
                                cancel_datetime="2026-09-02T00:00:00.000Z"), context)
        for name in VIEWS:
            apply(name)

    def test_views_can_be_applied_twice(self):
        for name in VIEWS:
            apply(name)

    def test_households_view(self):
        found = rows("SELECT * FROM vw_survey_households")
        self.assertEqual(len(found), 1)
        row = found[0]
        self.assertEqual((row["subject_uuid"], row["slum_name"], row["city_name"], row["household_number"], row["version"]),
                         ("sub-1", "Lokmanya Nagar", "Thane", "42", 1))
        self.assertEqual(str(row["registration_date"]), "2026-09-01")

    def test_encounters_view_marks_filled_visits(self):
        found = {row["record_uuid"]: row for row in rows("SELECT * FROM vw_survey_encounters")}
        self.assertEqual(sorted(found), ["enc-1", "enc-2"])
        self.assertTrue(found["enc-1"]["is_filled"])
        self.assertFalse(found["enc-2"]["is_filled"])
        self.assertEqual(found["enc-1"]["slum_name"], "Lokmanya Nagar")
        counts = rows("SELECT encounter_type, count(*) AS n FROM vw_survey_encounters WHERE is_filled AND NOT is_voided GROUP BY 1")
        self.assertEqual(counts, [{"encounter_type": "Sanitation", "n": 1}])

    def test_answers_view_joins_the_dictionary(self):
        found = {row["question_key"]: row for row in rows("SELECT * FROM vw_survey_answers")}
        self.assertEqual(found["members"]["value_number"], 4.0)
        self.assertEqual(found["members"]["question_text"], "Members")
        self.assertEqual((found["toilet_users"]["answer_key"], found["toilet_users"]["answer_text"]), ("men", "Men"))
        self.assertEqual(found["toilet_users"]["encounter_type"], "Sanitation")
