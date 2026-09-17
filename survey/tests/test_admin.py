"""The survey admin: registered, read-only where it must be, switches editable."""

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from survey.admin import ConceptAdmin, RecordAdmin, SlumDataVersionAdmin, SyncSwitchAdmin
from survey.models import Concept, Record, SlumDataVersion, SyncSwitch
from survey.tests.support import make_city, make_slum


class AdminRegistryTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser("root", "root@example.com", "x")
        self.client.force_login(self.admin_user)
        self.slum = make_slum(make_city())

    def test_every_survey_model_is_registered(self):
        for model in (Concept, Record, SlumDataVersion, SyncSwitch):
            self.assertIn(model, admin.site._registry)

    def test_concepts_only_expose_sa_text_and_active(self):
        concept = Concept.objects.create(key="k", name="K", sa_text="K")
        readonly = ConceptAdmin(Concept, admin.site).get_readonly_fields(None, concept)
        self.assertIn("key", readonly)
        self.assertIn("name", readonly)
        self.assertNotIn("sa_text", readonly)
        self.assertNotIn("is_active", readonly)
        self.assertFalse(ConceptAdmin(Concept, admin.site).has_add_permission(None))

    def test_records_are_read_only(self):
        row = Record.objects.create(provider="avni", kind="subject", external_id="s", slum=self.slum)
        model_admin = RecordAdmin(Record, admin.site)
        self.assertIn("external_id", model_admin.get_readonly_fields(None, row))
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None, row))
        response = self.client.get(reverse("admin:survey_record_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:survey_record_change", args=[row.pk])).status_code, 200)

    def test_a_version_cannot_be_deleted_once_records_use_it(self):
        version = SlumDataVersion.objects.create(slum=self.slum, version=2, started_on=timezone.now())
        model_admin = SlumDataVersionAdmin(SlumDataVersion, admin.site)
        self.assertTrue(model_admin.has_delete_permission(None, version))
        Record.objects.create(provider="avni", kind="subject", external_id="s", slum=self.slum, version=2)
        self.assertFalse(model_admin.has_delete_permission(None, version))

    def test_adding_a_version_records_who_did_it(self):
        response = self.client.post(reverse("admin:survey_slumdataversion_add"), {
            "slum": self.slum.pk, "version": 2, "started_on_0": "2026-09-10", "started_on_1": "00:00:00", "note": "resurvey",
        })
        self.assertEqual(response.status_code, 302, response.content[:500])
        self.assertEqual(SlumDataVersion.objects.get().created_by, self.admin_user)

    def test_switch_list_shows_effective_state_and_actions_toggle(self):
        parent = SyncSwitch.objects.create(provider="avni", subject_type="Household", kind="subject", is_enabled=False)
        child = SyncSwitch.objects.create(provider="avni", subject_type="Household", kind="encounter", encounter_type="Water")
        model_admin = SyncSwitchAdmin(SyncSwitch, admin.site)
        self.assertIn("parent", str(model_admin.effective(child)))
        self.assertIn("off", str(model_admin.effective(parent)))
        response = self.client.post(reverse("admin:survey_syncswitch_changelist"), {
            "action": "enable_selected", "_selected_action": [parent.pk],
        })
        self.assertEqual(response.status_code, 302)
        parent.refresh_from_db()
        self.assertTrue(parent.is_enabled)
        self.assertIn("on", str(model_admin.effective(child)))
        response = self.client.get(reverse("admin:survey_syncswitch_changelist"))
        self.assertContains(response, "Water")


class SwitchDisableActionTests(TestCase):
    def test_disable_action_and_alias_inline_is_read_only(self):
        from survey.admin import ConceptAliasInline

        admin_user = User.objects.create_superuser("root2", "root2@example.com", "x")
        self.client.force_login(admin_user)
        row = SyncSwitch.objects.create(provider="avni", subject_type="Household", kind="subject")
        response = self.client.post(reverse("admin:survey_syncswitch_changelist"), {
            "action": "disable_selected", "_selected_action": [row.pk],
        })
        self.assertEqual(response.status_code, 302)
        row.refresh_from_db()
        self.assertFalse(row.is_enabled)
        self.assertFalse(ConceptAliasInline(Concept, admin.site).has_add_permission(None))
