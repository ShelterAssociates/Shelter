"""Permissions, the 01:00 schedule and the RHS dry-run count."""

from datetime import datetime

from django.contrib.auth.models import Group, User
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from avni import paths
from avni.tests.support import FakeApi, page
from avni_console import permissions
from avni_console.services import dry_run, schedule


class PermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="u")
        self.group = Group.objects.create(name="Data Team")

    def test_superuser_can_do_everything(self):
        self.user.is_superuser = True
        self.assertTrue(permissions.can_use_console(self.user))
        self.assertTrue(permissions.can_write_avni(self.user))

    def test_plain_user_cannot(self):
        self.assertFalse(permissions.can_use_console(self.user))
        self.assertFalse(permissions.can_write_avni(self.user))

    @override_settings(AVNI_SYNC_GROUPS=["Data Team"], AVNI_WRITE_GROUPS=[])
    def test_sync_group_can_use_but_not_write(self):
        self.user.groups.add(self.group)
        self.assertTrue(permissions.can_use_console(self.user))
        self.assertFalse(permissions.can_write_avni(self.user))

    @override_settings(AVNI_SYNC_GROUPS=[], AVNI_WRITE_GROUPS=["Data Team"])
    def test_write_group_implies_console_access(self):
        self.user.groups.add(self.group)
        self.assertTrue(permissions.can_write_avni(self.user))
        self.assertTrue(permissions.can_use_console(self.user))

    def test_anonymous_and_inactive(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(permissions.can_use_console(AnonymousUser()))
        self.user.is_superuser = True
        self.user.is_active = False
        self.assertFalse(permissions.can_use_console(self.user))


class ScheduleTests(SimpleTestCase):
    def local(self, *args):
        return timezone.make_aware(datetime(*args))

    def test_before_the_hour_today(self):
        when = schedule.next_run_at(1, now=self.local(2026, 9, 11, 0, 30))
        self.assertEqual(timezone.localtime(when), self.local(2026, 9, 11, 1, 0))

    def test_after_the_hour_tomorrow(self):
        when = schedule.next_run_at(1, now=self.local(2026, 9, 11, 14, 0))
        self.assertEqual(timezone.localtime(when), self.local(2026, 9, 12, 1, 0))

    def test_exactly_on_the_hour_is_tomorrow(self):
        when = schedule.next_run_at(1, now=self.local(2026, 9, 11, 1, 0))
        self.assertEqual(timezone.localtime(when), self.local(2026, 9, 12, 1, 0))

    def test_month_rollover(self):
        when = schedule.next_run_at(1, now=self.local(2026, 9, 30, 23, 59))
        self.assertEqual(timezone.localtime(when), self.local(2026, 10, 1, 1, 0))

    def test_dedupe_key_names_the_slot(self):
        when = schedule.next_run_at(1, now=self.local(2026, 9, 11, 14, 0))
        self.assertEqual(schedule.slot_key("dashboard_update", when), "dashboard_update:2026-09-12T01:00")


class DryRunTests(TestCase):
    def test_counts_per_subject_type(self):
        since = "2026-01-01T00:00:00.000Z"
        api = FakeApi({
            paths.subjects("Household", since): [page(["x"] * 20, 2, 20), page(["x"] * 3 + [{"Voided": True}], 2, 20)],
            paths.subjects("Structure", since): page([]),
        })
        result = dry_run.count_households(["Household", "Structure"], "2026-01-01", api=api)
        self.assertEqual(result["window_start"], since)
        self.assertEqual(result["counts"]["Household"], {"total": 24, "pages": 2, "page_size": 20})
        self.assertEqual(result["counts"]["Structure"]["total"], 0)
        self.assertEqual(result["errors"], {})

    def test_list_error_is_reported_per_type(self):
        api = FakeApi({paths.subjects("Household", "2026-01-01T00:00:00.000Z"): page([])})
        result = dry_run.count_households(["Household", "Structure"], "2026-01-01", api=api)
        self.assertIn("Structure", result["errors"])
        self.assertEqual(result["counts"]["Household"]["total"], 0)

    def test_wide_window_warns(self):
        api = FakeApi({paths.subjects("Household", "2020-01-01T00:00:00.000Z"): page([])})
        result = dry_run.count_households(["Household"], "2020-01-01", api=api)
        self.assertTrue(result["warning"])

    def test_bad_subject_type_rejected(self):
        with self.assertRaises(ValueError):
            dry_run.count_households(["Toilet"], "2026-01-01", api=FakeApi())
