"""Map filter presets: which preset a slum resolves to, and the definitions sent to the app."""

import datetime

from django.test import TestCase

from avni import map_filters
from avni.models import (
    AvniFilterPreset,
    AvniFilterPresetItem,
    AvniFilterPresetScope,
    AvniForm,
    AvniFormMapping,
    AvniFormQuestion,
    AvniStageFilter,
)
from avni.tests.support import make_city, make_slum
from helpers.financial_year import current_financial_year


def make_form(name, form_type="Encounter", uuid=None):
    return AvniForm.objects.create(uuid=uuid or name, name=name, form_type=form_type)


def make_mapping(form, subject_type="Household", program="", encounter_type="", uuid=None):
    return AvniFormMapping.objects.create(
        uuid=uuid or "{}-{}-{}".format(form.uuid, program, encounter_type),
        form=form, subject_type=subject_type, program=program, encounter_type=encounter_type,
    )


def make_date_question(form, concept_name, concept_uuid):
    return AvniFormQuestion.objects.create(
        form=form, uuid=concept_uuid + "-el", question_name=concept_name, concept_name=concept_name,
        concept_uuid=concept_uuid, data_type="Date",
    )


class PresetResolutionTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.other_slum = make_slum(self.city, name="Elsewhere", code="EL1")

    def preset(self, name, version=1, is_active=True):
        return AvniFilterPreset.objects.create(name=name, version=version, is_active=is_active)

    def test_no_scope_means_no_preset(self):
        self.preset("Unassigned")
        self.assertIsNone(map_filters.resolve_preset(self.slum))

    def test_a_global_scope_covers_every_slum(self):
        preset = self.preset("Everywhere")
        AvniFilterPresetScope.objects.create(preset=preset)
        self.assertEqual(map_filters.resolve_preset(self.slum), preset)
        self.assertEqual(map_filters.resolve_preset(self.other_slum), preset)

    def test_a_city_scope_beats_the_global_one(self):
        globally = self.preset("Everywhere")
        AvniFilterPresetScope.objects.create(preset=globally)
        city_wide = self.preset("City")
        AvniFilterPresetScope.objects.create(preset=city_wide, city=self.city)
        self.assertEqual(map_filters.resolve_preset(self.slum), city_wide)

    def test_a_slum_scope_beats_the_city_one(self):
        city_wide = self.preset("City")
        AvniFilterPresetScope.objects.create(preset=city_wide, city=self.city)
        just_here = self.preset("This slum")
        AvniFilterPresetScope.objects.create(preset=just_here, slum=self.slum)
        self.assertEqual(map_filters.resolve_preset(self.slum), just_here)
        self.assertEqual(map_filters.resolve_preset(self.other_slum), city_wide)

    def test_a_slum_scope_records_the_city_so_it_is_found_in_one_query(self):
        preset = self.preset("This slum")
        scope = AvniFilterPresetScope.objects.create(preset=preset, slum=self.slum)
        scope.refresh_from_db()
        self.assertEqual(scope.city_id, self.city.id)

    def test_the_newest_version_wins_between_equal_scopes(self):
        old = self.preset("City", version=1)
        new = self.preset("City", version=2)
        AvniFilterPresetScope.objects.create(preset=old, city=self.city)
        AvniFilterPresetScope.objects.create(preset=new, city=self.city)
        self.assertEqual(map_filters.resolve_preset(self.slum), new)

    def test_a_switched_off_preset_is_ignored(self):
        off = self.preset("Draft", version=2, is_active=False)
        on = self.preset("Draft", version=1)
        AvniFilterPresetScope.objects.create(preset=off, city=self.city)
        AvniFilterPresetScope.objects.create(preset=on, city=self.city)
        self.assertEqual(map_filters.resolve_preset(self.slum), on)


class PayloadTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.preset = AvniFilterPreset.objects.create(name="Ichalkaranji", version=3)
        AvniFilterPresetScope.objects.create(preset=self.preset, city=self.city)
        water = make_mapping(make_form("Water Encounter form", uuid="f-water"), encounter_type="Water")
        self.water = AvniFilterPresetItem.objects.create(
            preset=self.preset, mapping=water, is_required=True, order=1)
        daily_form = make_form("Household Level Daily Reporting", form_type="ProgramEncounter", uuid="f-daily")
        daily = make_mapping(daily_form, program="Sanitation program", encounter_type="Daily Reporting")
        self.agreement = make_date_question(daily_form, "Date of agreement", "c-agreement")
        self.daily = AvniFilterPresetItem.objects.create(
            preset=self.preset, mapping=daily, anchor_question=self.agreement,
            default_window="current_fy", order=2)
        AvniStageFilter.objects.create(
            item=self.daily, label="Phase 1 material given", order=1,
            question=make_date_question(daily_form, "Date on which cement is given", "c-cement"))
        AvniStageFilter.objects.create(
            item=self.daily, label="Agreement cancelled", kind="cancelled", order=9,
            question=make_date_question(daily_form, "Date on which agreement is cancelled", "c-cancel"))

    def payload(self):
        return map_filters.payload(self.slum)

    def test_no_preset_for_the_slum_returns_nothing(self):
        AvniFilterPresetScope.objects.all().delete()
        self.assertIsNone(self.payload())

    def test_the_preset_is_named_and_versioned(self):
        self.assertEqual(self.payload()["preset"], {"name": "Ichalkaranji", "version": 3})

    def test_forms_carry_the_identity_the_app_matches_on(self):
        forms = {form["id"]: form for form in self.payload()["forms"]}
        self.assertEqual(sorted(forms), ["enc:Household:Water", "penc:Household:Sanitation program:Daily Reporting"])
        water = forms["enc:Household:Water"]
        self.assertEqual(water["label"], "Water")
        self.assertEqual(water["kind"], "enc")
        self.assertEqual(water["encounter_type"], "Water")
        self.assertTrue(water["required"])
        self.assertIsNone(water["anchor_concept_uuid"])
        self.assertEqual(water["default_window"], "overall")

    def test_an_anchor_question_travels_as_its_concept(self):
        daily = next(f for f in self.payload()["forms"] if f["kind"] == "penc")
        self.assertEqual(daily["anchor_concept_uuid"], "c-agreement")
        self.assertEqual(daily["anchor_concept_name"], "Date of agreement")
        self.assertEqual(daily["default_window"], "current_fy")

    def test_forms_keep_their_configured_order(self):
        self.assertEqual([f["kind"] for f in self.payload()["forms"]], ["enc", "penc"])

    def test_stages_are_ordered_and_name_the_form_they_belong_to(self):
        stages = self.payload()["stages"]
        self.assertEqual([stage["label"] for stage in stages], ["Phase 1 material given", "Agreement cancelled"])
        self.assertEqual([stage["kind"] for stage in stages], ["progress", "cancelled"])
        self.assertEqual(stages[0]["concept_uuid"], "c-cement")
        self.assertEqual(
            {stage["form_id"] for stage in stages}, {"penc:Household:Sanitation program:Daily Reporting"})

    def test_completeness_is_offered_only_when_a_form_is_required(self):
        self.assertIn("completeness", self.payload())
        AvniFilterPresetItem.objects.update(is_required=False)
        self.assertNotIn("completeness", self.payload())

    def test_a_pre_form_points_at_its_post_form(self):
        pre = make_mapping(make_form("OHOT Pre", form_type="ProgramEncounter", uuid="f-pre"),
                           program="Sanitation program", encounter_type="OHOT Pre Impact Assessment")
        post = make_mapping(make_form("OHOT Post", form_type="ProgramEncounter", uuid="f-post"),
                            program="Sanitation program", encounter_type="OHOT Post Impact Assessment")
        post_item = AvniFilterPresetItem.objects.create(preset=self.preset, mapping=post, order=4)
        AvniFilterPresetItem.objects.create(preset=self.preset, mapping=pre, pairs_with=post_item, order=3)
        pairs = self.payload()["pairs"]
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["pre_form_id"], "penc:Household:Sanitation program:OHOT Pre Impact Assessment")
        self.assertEqual(pairs[0]["post_form_id"], "penc:Household:Sanitation program:OHOT Post Impact Assessment")

    def test_date_presets_are_financial_years_newest_first(self):
        windows = self.payload()["date_presets"]
        current = current_financial_year()
        self.assertEqual(windows[0]["id"], "fy-{}".format(current))
        self.assertEqual(windows[0]["from"], datetime.date(current, 4, 1).isoformat())
        self.assertEqual(windows[0]["to"], datetime.date(current + 1, 3, 31).isoformat())
        self.assertEqual([w["id"] for w in windows], sorted((w["id"] for w in windows), reverse=True))

    def test_a_label_overrides_the_encounter_name(self):
        self.water.label = "Water survey"
        self.water.save()
        self.assertIn("Water survey", [form["label"] for form in self.payload()["forms"]])
