"""AvniProvider: catalog from the form cache, AVNI shapes -> Observations, legacy dispatch."""

from django.test import TestCase

from avni import metadata, paths, provider as avni_provider
from avni.provider import AvniProvider, CachingApi
from avni.tests.support import FakeApi, encounter_record, make_city, make_slum, program_encounter_record, subject_record
from avni.tests.test_metadata import element, export, modules, routes
from graphs.models import FollowupData, HouseholdData, MemberData
from mastersheet.models import ToiletConstruction
from survey import contracts
from survey.store import SyncContext


def by_name(observations):
    return {(o.question.name or o.question.external_id, o.repeat_index): o for o in observations}


class CatalogTests(TestCase):
    def setUp(self):
        metadata.refresh_form_cache(api=FakeApi(routes()))
        self.provider = AvniProvider(api=FakeApi())

    def test_one_entry_per_active_mapping_with_the_core_kind(self):
        entries = {(e.subject_type, e.kind, e.program, e.encounter_type): e for e in self.provider.catalog()}
        self.assertIn(("Household", "subject", "", ""), entries)
        self.assertIn(("Household", "enrolment", "Sanitation program", ""), entries)
        self.assertIn(("Household", "program_encounter", "Sanitation program", "Daily Reporting"), entries)
        self.assertIn(("Household", "encounter", "", "Water"), entries)
        self.assertIn(("Toilet", "subject", "", ""), entries)
        self.assertEqual(entries[("Household", "encounter", "", "Water")].label, "Water form")
        self.assertEqual(entries[("Household", "encounter", "", "Water")].form_external_id, "f-water")

    def test_avni_types_map_onto_the_core_vocabulary(self):
        registration = [e for e in self.provider.catalog() if e.kind == "subject" and e.subject_type == "Household"][0]
        types = {question.name: question.data_type for question, answers in registration.concepts}
        self.assertEqual(types["First name"], "text")
        self.assertEqual(types["Aadhaar number"], "numeric")
        self.assertEqual(types["Do you have a toilet at home?"], "coded")
        self.assertEqual(types["Total Number of Members"], "group")
        self.assertEqual(types["Number of Male members"], "numeric", "group children are listed too")
        self.assertNotIn("Old question", types, "voided elements are left out")

    def test_coded_answers_carry_their_uuids(self):
        registration = [e for e in self.provider.catalog() if e.kind == "subject" and e.subject_type == "Household"][0]
        answers = {q.name: a for q, a in registration.concepts}["Use of toilet"]
        self.assertEqual([(a.external_id, a.name, a.data_type) for a in answers],
                         [("a-Men", "Men", "answer"), ("a-Women", "Women", "answer")])

    def test_unknown_avni_types_are_unknown(self):
        self.assertEqual(avni_provider.core_data_type("Weird"), "unknown")
        self.assertEqual(avni_provider.core_data_type("Image"), "media")
        self.assertEqual(avni_provider.core_data_type("Location"), "location")


class FactsAndStatusTests(TestCase):
    def setUp(self):
        self.provider = AvniProvider(api=FakeApi())

    def test_subject_facts(self):
        facts = self.provider.facts("subject", subject_record())
        self.assertEqual(facts.external_id, "sub-1")
        self.assertEqual(facts.subject_external_id, "sub-1")
        self.assertEqual(facts.subject_type, "Household")
        self.assertEqual(facts.slum_name, "Lokmanya Nagar")
        self.assertEqual(facts.household_number, "42")
        self.assertEqual(facts.record_datetime, "2018-03-20")
        self.assertEqual(facts.last_modified, "2026-09-01T06:47:34.548Z")

    def test_encounter_facts_carry_no_identity(self):
        facts = self.provider.facts("encounter", encounter_record())
        self.assertEqual(facts.subject_external_id, "sub-1")
        self.assertEqual(facts.encounter_type, "Sanitation")
        self.assertEqual(facts.slum_name, "")

    def test_status_done_scheduled_cancelled_voided(self):
        done = encounter_record()
        scheduled = encounter_record(observations={})
        scheduled["Encounter date time"] = None
        scheduled["Earliest scheduled date"] = "2026-09-10T00:00:00.000Z"
        cancelled = encounter_record(observations={})
        cancelled["Cancel date time"] = "2026-09-05T00:00:00.000Z"
        self.assertEqual(self.provider.visit_status("encounter", done), "done")
        self.assertEqual(self.provider.visit_status("encounter", scheduled), "scheduled")
        self.assertEqual(self.provider.visit_status("encounter", cancelled), "cancelled")
        self.assertEqual(self.provider.visit_status("encounter", encounter_record(voided=True)), "voided")
        self.assertEqual(self.provider.visit_status("subject", subject_record()), "done")
        self.assertEqual(self.provider.visit_status("subject", subject_record(voided=True)), "voided")

    def test_legacy_skip_rules_are_todays(self):
        self.assertFalse(self.provider.is_skipped_by_legacy("subject", subject_record()))
        self.assertTrue(self.provider.is_skipped_by_legacy("subject", subject_record(voided=True)))
        self.assertTrue(self.provider.is_skipped_by_legacy("encounter", encounter_record(observations={})))
        self.assertTrue(self.provider.is_skipped_by_legacy("encounter", encounter_record(voided=True)))
        self.assertFalse(self.provider.is_skipped_by_legacy("encounter", encounter_record()))


class NormalizeTests(TestCase):
    def setUp(self):
        metadata.refresh_form_cache(api=FakeApi(routes()))
        self.provider = AvniProvider(api=FakeApi())

    def test_identity_and_dates_of_a_subject(self):
        record = self.provider.normalize("subject", subject_record())
        self.assertEqual(record.kind, "subject")
        self.assertEqual(record.slum_name, "Lokmanya Nagar")
        self.assertEqual(record.city_name, "Thane")
        self.assertEqual(record.household_number, "42")
        self.assertEqual(record.form_external_id, "f-reg")
        self.assertEqual(record.form_name, "Household form")
        self.assertEqual(record.record_datetime, "2018-03-20")
        self.assertEqual(record.created_at, "2021-08-17T04:37:33.023Z")

    def test_an_encounter_takes_identity_from_its_subject(self):
        raw = encounter_record(encounter_type="Water")
        raw["Earliest scheduled date"] = "2026-08-30T00:00:00.000Z"
        record = self.provider.normalize("encounter", raw, subject_record())
        self.assertEqual(record.subject_external_id, "sub-1")
        self.assertEqual(record.subject_type, "Household")
        self.assertEqual(record.slum_name, "Lokmanya Nagar")
        self.assertEqual(record.household_number, "42")
        self.assertEqual(record.form_name, "Water form")
        self.assertEqual(record.earliest_scheduled, "2026-08-30T00:00:00.000Z")

    def test_top_level_names_and_group_children_by_uuid(self):
        raw = subject_record(observations={
            "Aadhaar number": 1234,
            "Total Number of Members": {"c-Number of Male members": 2, "c-Number of Female members": 3},
        })
        observations = by_name(self.provider.normalize("subject", raw).observations)
        self.assertEqual(observations[("Aadhaar number", 0)].question.data_type, "numeric")
        male = observations[("Number of Male members", 0)]
        self.assertEqual(male.value, 2)
        self.assertEqual(male.group.name, "Total Number of Members")
        self.assertEqual(male.question.external_id, "c-Number of Male members")

    def test_repeat_groups_keep_their_index(self):
        raw = subject_record(observations={
            "Total Number of Members": [{"c-Number of Male members": 1}, {"c-Number of Male members": 4}],
        })
        observations = by_name(self.provider.normalize("subject", raw).observations)
        self.assertEqual(observations[("Number of Male members", 0)].value, 1)
        self.assertEqual(observations[("Number of Male members", 1)].value, 4)

    def test_multi_select_becomes_one_observation_per_option(self):
        raw = subject_record(observations={"Use of toilet": ["Men", "Women"]})
        rows = [o for o in self.provider.normalize("subject", raw).observations if o.question.name == "Use of toilet"]
        self.assertEqual([(o.value, o.answer_name) for o in rows], [("Men", "Men"), ("Women", "Women")])
        self.assertEqual([o.position for o in rows], [1, 2])

    def test_single_coded_answer_names_the_option(self):
        raw = subject_record(observations={"Do you have a toilet at home?": "Yes"})
        row = by_name(self.provider.normalize("subject", raw).observations)[("Do you have a toilet at home?", 0)]
        self.assertEqual(row.answer_name, "Yes")

    def test_unknown_concepts_are_kept_by_name_or_uuid(self):
        raw = subject_record(observations={
            "Brand new question": "x",
            "Total Number of Members": {"3fa85f64-5717-4562-b3fc-2c963f66afa6": 9},
        })
        observations = by_name(self.provider.normalize("subject", raw).observations)
        self.assertEqual(observations[("Brand new question", 0)].question.data_type, "unknown")
        child = observations[("3fa85f64-5717-4562-b3fc-2c963f66afa6", 0)]
        self.assertEqual(child.question.name, "")
        self.assertEqual(child.question.external_id, "3fa85f64-5717-4562-b3fc-2c963f66afa6")

    def test_a_location_dict_is_one_observation(self):
        raw = subject_record(observations={"Where": {"x": 72.8, "y": 19.1}})
        row = by_name(self.provider.normalize("subject", raw).observations)[("Where", 0)]
        self.assertEqual(row.value, {"x": 72.8, "y": 19.1})

    def test_an_unknown_dict_is_walked_as_a_group(self):
        raw = subject_record(observations={"Mystery group": {"Child A": "a", "Child B": "b"}})
        observations = by_name(self.provider.normalize("subject", raw).observations)
        self.assertEqual(observations[("Child A", 0)].group.name, "Mystery group")

    def test_media_lists_become_one_observation_per_url(self):
        raw = subject_record(observations={"Photos": ["https://x/1.jpg", "https://x/2.jpg"]})
        rows = [o for o in self.provider.normalize("subject", raw).observations if o.question.name == "Photos"]
        self.assertEqual([o.value for o in rows], ["https://x/1.jpg", "https://x/2.jpg"])

    def test_empty_values_are_dropped(self):
        raw = subject_record(observations={"Blank": None, "Empty": "", "Nothing": []})
        names = [o.question.name for o in self.provider.normalize("subject", raw).observations]
        self.assertEqual(names, ["First name"])

    def test_a_record_with_no_cached_form_still_normalizes(self):
        raw = encounter_record(encounter_type="Never seen")
        record = self.provider.normalize("encounter", raw, subject_record())
        self.assertEqual(record.form_name, "")
        self.assertEqual(len(record.observations), 1)


class SubjectTreeTests(TestCase):
    def test_uuid_lists_are_fetched_into_a_tree(self):
        subject = subject_record()
        subject["enrolments"] = ["enr-1"]
        subject["encounters"] = ["enc-1"]
        enrolment = {"ID": "enr-1", "Subject ID": "sub-1", "Program": "Sanitation program",
                     "Enrolment datetime": "2026-01-01T00:00:00.000Z", "observations": {}, "encounters": ["penc-1"],
                     "audit": {"Created at": "x", "Last modified at": "y"}}
        api = FakeApi({
            paths.subject("sub-1"): subject,
            paths.program_enrolment("enr-1"): enrolment,
            paths.program_encounter("penc-1"): program_encounter_record(),
            paths.encounter("enc-1"): encounter_record(),
        })
        tree = AvniProvider(api=api).get_subject_tree("sub-1")
        self.assertEqual(tree.subject["ID"], "sub-1")
        self.assertEqual(tree.enrolments[0][0]["ID"], "enr-1")
        self.assertEqual(tree.enrolments[0][1][0]["ID"], "penc-1")
        self.assertEqual(tree.encounters[0]["ID"], "enc-1")

    def test_inlined_children_are_used_without_a_fetch(self):
        subject = subject_record()
        subject["encounters"] = [encounter_record()]
        api = FakeApi({paths.subject("sub-1"): subject})
        tree = AvniProvider(api=api).get_subject_tree("sub-1")
        self.assertEqual(tree.encounters[0]["ID"], "enc-1")
        self.assertEqual(api.calls, [paths.subject("sub-1")])

    def test_a_child_that_cannot_be_fetched_is_left_out(self):
        subject = subject_record()
        subject["encounters"] = ["gone"]
        tree = AvniProvider(api=FakeApi({paths.subject("sub-1"): subject})).get_subject_tree("sub-1")
        self.assertEqual(tree.encounters, [])

    def test_listing_goes_through_the_right_path(self):
        provider = AvniProvider(api=FakeApi())
        self.assertEqual(provider.list_path("subject", "Household", "", "", "s"), paths.subjects("Household", "s"))
        self.assertEqual(provider.list_path("encounter", "Household", "", "Water", "s"), paths.encounters("Water", "s"))
        self.assertEqual(provider.list_path("program_encounter", "Household", "P", "Daily Reporting", "s"),
                         paths.program_encounters("Daily Reporting", "s"))
        with self.assertRaises(ValueError):
            provider.list_path("enrolment", "Household", "Sanitation program", "", "s")
        self.assertFalse(provider.lists("enrolment"))
        self.assertTrue(provider.lists("program_encounter"))


class CachingApiTests(TestCase):
    def test_subject_reads_come_from_the_memo(self):
        api = FakeApi({paths.subject("sub-1"): subject_record(), "api/other": {"x": 1}})
        subjects = {}
        cached = CachingApi(api, subjects)
        cached.get_json(paths.subject("sub-1"))
        cached.get_json(paths.subject("sub-1"))
        cached.get_json("api/other")
        cached.get_json("api/other")
        self.assertEqual(api.calls.count(paths.subject("sub-1")), 1)
        self.assertEqual(api.calls.count("api/other"), 2)
        self.assertIn("sub-1", subjects)


class LegacyDispatchTests(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.provider = AvniProvider(api=FakeApi())
        self.context = SyncContext(self.provider)

    def with_subject(self, record):
        self.context.subjects[record["ID"]] = record
        return record

    def test_household_registration_goes_through_save_household(self):
        raw = subject_record(observations={"Aadhaar number": "1234"})
        self.assertTrue(self.provider.legacy_save("subject", raw, self.context))
        row = HouseholdData.objects.get(slum=self.slum, household_number="42")
        self.assertEqual(row.rhs_data["group_el9cl08/Aadhar_number"], "1234")
        self.assertEqual(row.rhs_data["rhs_uuid"], "sub-1")

    def test_structure_registration_also_goes_through_save_household(self):
        raw = subject_record(subject_type="Structure", observations={"Aadhaar number": "9"})
        self.assertTrue(self.provider.legacy_save("subject", raw, self.context))
        self.assertEqual(HouseholdData.objects.get().rhs_data["group_el9cl08/Aadhar_number"], "9")

    def test_dses_registration_goes_through_the_structure_writer(self):
        raw = subject_record(subject_type="Detailed Socio Economic Survey",
                             observations={"Ownership status of the house": "Own house/Shop", "Odd question": "kept"})
        self.assertTrue(self.provider.legacy_save("subject", raw, self.context))
        rhs = HouseholdData.objects.get(slum=self.slum, household_number="42").rhs_data
        self.assertEqual(rhs["group_el9cl08/Ownership_status_of_the_house"], "Own house")
        self.assertEqual(rhs["Odd question"], "kept", "unmapped questions keep the AVNI name")
        self.assertEqual(rhs["rhs_uuid"], "sub-1")

    def test_a_subject_type_with_no_writer_is_stored_only(self):
        raw = subject_record(subject_type="Toilet")
        self.assertFalse(self.provider.legacy_save("subject", raw, self.context))
        self.assertEqual(HouseholdData.objects.count(), 0)

    def test_a_household_sanitation_encounter_merges_and_writes_followup(self):
        self.with_subject(subject_record())
        raw = encounter_record(encounter_type="Sanitation", observations={"Status of toilet under SBM ?": "Built"})
        self.assertTrue(self.provider.legacy_save("encounter", raw, self.context))
        rhs = HouseholdData.objects.get(household_number="42").rhs_data
        self.assertEqual(rhs["group_oi8ts04/Status_of_toilet_under_SBM"], "Built")
        self.assertEqual(FollowupData.objects.get(household_number="42").followup_data["group_oi8ts04/Status_of_toilet_under_SBM"], "Built")

    def test_a_dses_sanitation_inp_encounter_lands_on_the_same_keys(self):
        self.with_subject(subject_record(subject_type="Detailed Socio Economic Survey"))
        raw = encounter_record(encounter_type="Sanitation INP", observations={"Status of toilet under SBM ?": "Built"})
        raw["Subject type"] = "Detailed Socio Economic Survey"
        self.assertTrue(self.provider.legacy_save("encounter", raw, self.context))
        rhs = HouseholdData.objects.get(household_number="42").rhs_data
        self.assertEqual(rhs["group_oi8ts04/Status_of_toilet_under_SBM"], "Built")
        self.assertTrue(FollowupData.objects.filter(household_number="42").exists())
        self.assertEqual(raw["Encounter type"], "Sanitation INP", "the caller's record is not re-stamped")

    def test_a_dses_water_inp_encounter_uses_the_water_rename(self):
        self.with_subject(subject_record(subject_type="Detailed Socio Economic Survey"))
        raw = encounter_record(encounter_type="Water INP", observations={"Type of water connection ?": "Own"})
        self.assertTrue(self.provider.legacy_save("encounter", raw, self.context))
        rhs = HouseholdData.objects.get(household_number="42").rhs_data
        self.assertEqual(rhs["group_el9cl08/Type_of_water_connection"], "Own")
        self.assertIn("Last_modified_date", rhs)

    def test_an_encounter_type_with_no_map_merges_under_avni_names(self):
        self.with_subject(subject_record(subject_type="Detailed Socio Economic Survey"))
        raw = encounter_record(encounter_type="Housing INP", observations={"Roof type": "Tin"})
        self.assertTrue(self.provider.legacy_save("encounter", raw, self.context))
        self.assertEqual(HouseholdData.objects.get(household_number="42").rhs_data["Roof type"], "Tin")

    def test_an_encounter_of_a_non_household_subject_never_touches_rhs_data(self):
        self.with_subject(subject_record(subject_type="Toilet"))
        raw = encounter_record(encounter_type="Cleaning")
        raw["Subject type"] = "Toilet"
        self.assertFalse(self.provider.legacy_save("encounter", raw, self.context))
        self.assertEqual(HouseholdData.objects.count(), 0)

    def test_daily_reporting_program_encounter_writes_toilet_construction(self):
        self.with_subject(subject_record())
        raw = program_encounter_record(observations={"Date of agreement": "2026-09-01", "Comment if any ?": "ok"})
        self.assertTrue(self.provider.legacy_save("program_encounter", raw, self.context))
        self.assertEqual(ToiletConstruction.objects.get(household_number="42").comment, "ok")

    def test_an_unknown_program_encounter_type_is_stored_only(self):
        self.with_subject(subject_record())
        raw = program_encounter_record(encounter_type="Mystery")
        self.assertFalse(self.provider.legacy_save("program_encounter", raw, self.context))

    def test_a_household_enrolment_has_no_legacy_writer(self):
        self.with_subject(subject_record())
        raw = {"ID": "enr-1", "Subject ID": "sub-1", "Program": "Sanitation program", "observations": {"a": 1}}
        self.assertFalse(self.provider.legacy_save("enrolment", raw, self.context))

    def test_a_legacy_error_is_reported_not_raised(self):
        self.with_subject(subject_record(slum="Nowhere"))
        raw = encounter_record(encounter_type="Water")
        self.assertFalse(self.provider.legacy_save("encounter", raw, self.context))

    def test_the_subject_memo_feeds_the_legacy_api(self):
        self.with_subject(subject_record())
        raw = encounter_record(encounter_type="Water")
        self.provider.legacy_save("encounter", raw, self.context)
        self.assertIsInstance(self.context.api, CachingApi)
        self.assertEqual(self.context.api.get_json(paths.subject("sub-1"))["ID"], "sub-1")
        self.assertEqual(self.provider.api().calls, [], "no live call was needed")

    def test_legacy_handles(self):
        handles = self.provider.legacy_handles
        self.assertTrue(handles("subject", "Household"))
        self.assertTrue(handles("subject", "Detailed Socio Economic Survey"))
        self.assertFalse(handles("subject", "Toilet"))
        self.assertTrue(handles("encounter", "Detailed Socio Economic Survey", "Housing INP"))
        self.assertFalse(handles("encounter", "Toilet", "Cleaning"))
        self.assertTrue(handles("program_encounter", "Household", "Family factsheet"))
        self.assertFalse(handles("program_encounter", "Household", "Mystery"))
        self.assertFalse(handles("enrolment", "Household"))
        self.assertTrue(handles("enrolment", "Family Member"))


class MemberAdapterTests(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city())
        self.provider = AvniProvider(api=FakeApi())
        self.context = SyncContext(self.provider)

    def member(self):
        raw = subject_record(uuid="mem-1", subject_type="Family Member", observations={
            "First name": "Asha", "Last name": "Patil", "Household number": "42",
        })
        raw["Date of birth"] = "1990-05-01"
        raw["Gender"] = "Female"
        return raw

    def test_a_family_member_subject_becomes_member_data(self):
        self.assertTrue(self.provider.legacy_save("subject", self.member(), self.context))
        member = MemberData.objects.get(member_uuid="mem-1")
        self.assertEqual((member.member_first_name, member.member_last_name), ("Asha", "Patil"))
        self.assertEqual(str(member.date_of_birth), "1990-05-01")
        self.assertEqual(member.gender, "2")
        self.assertEqual(member.household_number, "42")
        self.assertEqual(member.slum, self.slum)
        self.assertEqual(member.member_data["First name"], "Asha")

    def test_enrolment_and_program_encounter_hang_off_the_member(self):
        self.provider.legacy_save("subject", self.member(), self.context)
        self.context.subjects["mem-1"] = self.member()
        enrolment = {"ID": "enr-1", "Subject ID": "mem-1", "Subject type": "Family Member",
                     "Program": "Menstrual hygiene", "Enrolment datetime": "2026-01-02T00:00:00.000Z",
                     "observations": {"Uses cup": "Yes"}, "audit": {"Created at": "2026-01-02T00:00:00.000Z", "Last modified at": "2026-01-03T00:00:00.000Z"}}
        self.assertTrue(self.provider.legacy_save("enrolment", enrolment, self.context))
        program = MemberData.objects.get().memberprogramdata_set.get()
        self.assertEqual(program.program_name, "Menstrual hygiene")
        self.assertEqual(program.program_uuid, "enr-1")
        encounter = program_encounter_record(uuid="penc-9", encounter_type="Follow up", subject_uuid="mem-1",
                                             observations={"Cup used": "Yes"})
        encounter["Subject type"] = "Family Member"
        encounter["Enrolment ID"] = "enr-1"
        self.assertTrue(self.provider.legacy_save("program_encounter", encounter, self.context))
        row = MemberData.objects.get().memberencounterdata_set.get()
        self.assertEqual((row.encounter_uuid, row.encounter_name, row.program), ("penc-9", "Follow up", program))


class ProviderEdgeTests(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city())

    def test_caching_api_delegates_other_attributes(self):
        api = FakeApi()
        self.assertIs(CachingApi(api, {}).calls, api.calls)

    def test_the_form_index_is_rebuilt_after_a_cache_refresh(self):
        provider = AvniProvider(api=FakeApi())
        self.assertEqual(provider.form_for("subject", "Household").name, "")
        metadata.refresh_form_cache(api=FakeApi(routes()))
        provider.refresh_forms_if_stale()
        self.assertEqual(provider.form_for("subject", "Household").name, "Household form")

    def test_catalog_falls_back_to_cached_questions_without_an_export(self):
        from avni.models import AvniForm, AvniFormMapping, AvniFormQuestion

        form = AvniForm.objects.create(uuid="f-x", name="Loose form", form_type="Encounter", definition=None)
        AvniFormMapping.objects.create(uuid="m-x", form=form, subject_type="Household", encounter_type="Loose")
        AvniFormQuestion.objects.create(form=form, uuid="e1", question_name="Q", concept_name="Loose question",
                                        concept_uuid="c-loose", data_type="Coded", answers=["A", "B"])
        AvniFormQuestion.objects.create(form=form, uuid="e2", question_name="Gone", concept_name="Gone", is_active=False, data_type="Text")
        entry = [e for e in AvniProvider(api=FakeApi()).catalog() if e.encounter_type == "Loose"][0]
        (question, answers), = entry.concepts
        self.assertEqual((question.name, question.data_type), ("Loose question", "coded"))
        self.assertEqual([a.name for a in answers], ["A", "B"])

    def test_cancellation_forms_and_voided_definition_parts_are_skipped(self):
        from avni.models import AvniForm, AvniFormMapping

        form = AvniForm.objects.create(uuid="f-c", name="Cancel", form_type="ProgramEncounterCancellation",
                                       definition={"formElementGroups": [{"voided": True, "formElements": [element("x")]},
                                                                         {"voided": False, "formElements": [element("y", voided=True), {"uuid": "z"}]}]})
        AvniFormMapping.objects.create(uuid="m-c", form=form, subject_type="Household", encounter_type="Cancel")
        self.assertEqual(AvniProvider(api=FakeApi()).catalog(), [])
        self.assertEqual(avni_provider.form_concepts(form), [])

    def test_two_mappings_sharing_a_type_name_lose_the_type_only_fallback(self):
        from avni.models import AvniForm, AvniFormMapping

        for uuid, subject_type in (("f-1", "Household"), ("f-2", "Toilet")):
            form = AvniForm.objects.create(uuid=uuid, name=uuid, form_type="Encounter")
            AvniFormMapping.objects.create(uuid="m-" + uuid, form=form, subject_type=subject_type, encounter_type="Shared")
        provider = AvniProvider(api=FakeApi())
        self.assertEqual(provider.form_for("encounter", "Household", "", "Shared").name, "f-1")
        self.assertEqual(provider.form_for("encounter", "", "", "Shared").name, "", "ambiguous by type alone")

    def test_listed_subjects_get_the_listed_subject_type(self):
        record = subject_record()
        del record["Subject type"]
        api = FakeApi({paths.subjects("Structure", "s"): {"content": [record], "totalPages": 1}})
        listed = list(AvniProvider(api=api).iter_records("subject", "Structure", since="s"))
        self.assertEqual(listed[0]["Subject type"], "Structure")

    def test_walk_group_ignores_non_group_values(self):
        self.assertEqual(avni_provider.walk_group(contracts.ConceptRef(name="g"), "scalar", avni_provider.EMPTY_FORM, [0]), [])

    def test_mobilization_attendance_encounter_is_dispatched(self):
        from mastersheet.models import CommunityMobilizationActivityAttendance

        from avni.tests.test_mobilization import make_activity

        make_activity("Workshop")
        provider = AvniProvider(api=FakeApi())
        context = SyncContext(provider)
        context.subjects["sub-1"] = subject_record()
        raw = encounter_record(encounter_type=avni_provider.MOBILIZATION_ENCOUNTER, observations={
            "Type of Activity": "Workshop", "Date of the activity conducted": "2026-02-01", "Number of Men present": 3,
        })
        self.assertTrue(provider.legacy_save("encounter", raw, context))
        self.assertEqual(CommunityMobilizationActivityAttendance.objects.get().males_attended_activity, 3)

    def test_records_without_a_subject_id_have_no_legacy_writer(self):
        provider = AvniProvider(api=FakeApi())
        self.assertFalse(provider.legacy_save("encounter", {"ID": "e", "Encounter type": "Water", "observations": {"a": 1}}, SyncContext(provider)))

    def test_program_encounter_of_a_non_household_subject_is_stored_only(self):
        provider = AvniProvider(api=FakeApi())
        context = SyncContext(provider)
        context.subjects["sub-1"] = subject_record(subject_type="Toilet")
        raw = program_encounter_record(observations={"a": 1})
        raw["Subject type"] = "Toilet"
        self.assertFalse(provider.legacy_save("program_encounter", raw, context))

    def test_member_child_of_an_unknown_kind_is_stored_only(self):
        provider = AvniProvider(api=FakeApi())
        self.assertFalse(provider.save_member_child("encounter", {}))


class MemberAdapterEdgeTests(TestCase):
    def setUp(self):
        self.slum = make_slum(make_city())

    def test_unknown_slum_and_bad_dates(self):
        from avni.sync import members

        self.assertFalse(members.save_member_from_record({"ID": "m", "location": {"Slum": "Nowhere"}, "observations": {}}))
        self.assertIsNone(members.record_day("yesterday"))
        self.assertIsNone(members.record_day(None))

    def test_household_number_from_groups_or_nothing(self):
        from avni.sync import members

        self.assertEqual(members.member_household_number({"observations": {}, "Groups": [{"Household number": "0042"}]}), "0042")
        self.assertIsNone(members.member_household_number({"observations": {}, "Groups": ["hh-uuid"]}))

    def test_program_without_audit_uses_the_enrolment_date_and_exit_date(self):
        from avni.sync import members

        members.save_member_from_record(subject_record(uuid="mem-1", subject_type="Family Member",
                                                       observations={"First name": "A", "Last name": "B"}))
        members.save_member_program_from_record({"ID": "enr-1", "Subject ID": "mem-1", "Program": "MHM",
                                                 "Enrolment datetime": "2026-01-02T00:00:00.000Z",
                                                 "Exit datetime": "2026-03-02T00:00:00.000Z", "observations": {}})
        program = MemberData.objects.get().memberprogramdata_set.get()
        self.assertEqual(str(program.created_date), "2026-01-02")
        self.assertEqual(str(program.program_exit_date), "2026-03-02")

    def test_encounter_without_a_matching_enrolment_id_uses_any_program(self):
        from avni.sync import members

        members.save_member_from_record(subject_record(uuid="mem-1", subject_type="Family Member", observations={"First name": "A"}))
        members.save_member_program_from_record({"ID": "enr-1", "Subject ID": "mem-1", "Program": "MHM", "observations": {}})
        members.save_member_encounter_from_record({"ID": "p1", "Subject ID": "mem-1", "Enrolment ID": "other", "Encounter type": "F", "observations": {}})
        self.assertEqual(MemberData.objects.get().memberencounterdata_set.get().program.program_uuid, "enr-1")

    def test_file_import_program_row_with_exit_date(self):
        from avni.sync import members

        members.save_member({"slum": self.slum.name, "member_uuid": "m", "member_first_name": "A", "member_last_name": "B",
                             "date_of_birth": "May 01, 1990", "gender": "Female", "household_number": "4",
                             "created_date": "2026-01-01", "submission_date": "2026-01-02", "member_data": {}})
        self.assertTrue(members.save_member_program({"member_id": "m", "family_member_menstrual_hygiene__uuid": "p", "program_name": "MHM",
                                                     "created_date": "2026-01-01", "submission_date": "2026-01-02",
                                                     "program_exit_date": "2026-02-01", "program_data": {}}))
        self.assertEqual(str(MemberData.objects.get().memberprogramdata_set.get().program_exit_date), "2026-02-01")


class SubjectTreeEdgeTests(TestCase):
    def test_an_enrolment_that_cannot_be_fetched_is_left_out(self):
        subject = subject_record()
        subject["enrolments"] = ["gone"]
        tree = AvniProvider(api=FakeApi({paths.subject("sub-1"): subject})).get_subject_tree("sub-1")
        self.assertEqual(tree.enrolments, [])
