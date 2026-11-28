"""Family members against a fake AVNI: the household a member belongs to, the order
members, enrolments and follow-ups are saved in, and gaps that close on the next run.

AVNI gives a member's household as a list of household-subject uuids under
"Groups"; the household's number is that subject's "First name".
"""

from django.test import TestCase

from avni import paths
from avni.client import reset_client, use_client
from avni.jobs import daily_sync
from avni.provider import AvniProvider
from avni.tests.support import FakeApi, make_city, make_slum, page, program_encounter_record, subject_record
from graphs.models import HouseholdData, MemberData, MemberEncounterData, MemberProgramData
from survey import connector
from survey.models import Record, SyncSwitch
from survey.store import SyncContext

SINCE = "2026-01-01T00:00:00.000Z"
PROGRAM = "Menstrual hygiene"
FOLLOW_UP = "Menstrual hygiene Follow-up"


def member_record(uuid="mem-1", groups=("hh-1",), modified="2026-09-01T06:47:34.548Z", **observations):
    answers = {"First name": "Asha", "Last name": "Patil", "Date of birth": "1990-05-01", "Gender": "Female"}
    answers.update(observations)
    record = subject_record(uuid=uuid, subject_type="Family Member", observations=answers, modified=modified)
    record["Groups"] = list(groups)
    return record


def household_record(uuid="hh-1", number="0042", **overrides):
    return subject_record(uuid=uuid, number=number, **overrides)


def enrolment_record(uuid="enr-1", member="mem-1", modified="2026-09-02T00:00:00.000Z", voided=False):
    return {
        "ID": uuid, "Subject ID": member, "Subject type": "Family Member", "Program": PROGRAM, "Voided": voided,
        "Enrolment datetime": "2026-09-01T00:00:00.000Z", "Exit datetime": None,
        "observations": {"Have you received a Cup from SA ?": "Yes"}, "exitObservations": {}, "encounters": [],
        "audit": {"Created at": "2026-09-01T00:00:00.000Z", "Last modified at": modified},
    }


def follow_up_record(uuid="fol-1", member="mem-1", enrolment="enr-1", modified="2026-09-03T00:00:00.000Z"):
    record = program_encounter_record(uuid=uuid, encounter_type=FOLLOW_UP, subject_uuid=member,
                                      observations={"Did you use cup in the previous menstruation?": "Yes"},
                                      modified=modified)
    record.update({"Subject type": "Family Member", "Program": PROGRAM, "Enrolment ID": enrolment})
    return record


class MemberHouseholdNumberTests(TestCase):
    """The legacy writer alone: which household number a member is saved with."""

    def setUp(self):
        self.slum = make_slum(make_city())
        self.api = FakeApi({paths.subject("hh-1"): household_record()})
        self.provider = AvniProvider(api=self.api)
        self.context = SyncContext(self.provider)

    def save(self, record):
        return self.provider.legacy_save("subject", record, self.context)

    def number_of(self, uuid="mem-1"):
        return MemberData.objects.get(member_uuid=uuid).household_number

    def test_a_member_takes_the_number_of_the_household_she_belongs_to(self):
        self.assertTrue(self.save(member_record()))
        self.assertEqual(self.number_of(), "42")

    def test_the_household_is_read_once_for_all_its_members(self):
        self.save(member_record("mem-1"))
        self.save(member_record("mem-2"))
        self.assertEqual(self.api.calls.count(paths.subject("hh-1")), 1)
        self.assertEqual((self.number_of("mem-1"), self.number_of("mem-2")), ("42", "42"))

    def test_a_number_among_the_members_own_answers_wins_without_a_fetch(self):
        self.save(member_record(**{"Household number": "7"}))
        self.assertEqual(self.number_of(), "7")
        self.assertEqual(self.api.calls, [])

    def test_a_group_that_is_not_a_household_is_passed_over(self):
        self.api.routes[paths.subject("grp-1")] = subject_record(uuid="grp-1", number="Mahila Mandal", subject_type="Grp head")
        self.save(member_record(groups=("grp-1", "hh-1")))
        self.assertEqual(self.number_of(), "42")

    def test_a_voided_household_is_passed_over(self):
        self.api.routes[paths.subject("hh-old")] = household_record("hh-old", number="9", voided=True)
        self.save(member_record(groups=("hh-old", "hh-1")))
        self.assertEqual(self.number_of(), "42")

    def test_a_household_that_cannot_be_read_still_saves_the_member(self):
        self.assertTrue(self.save(member_record(groups=("ghost",))))
        self.assertIsNone(self.number_of())

    def test_a_member_in_no_household_is_saved_without_a_number(self):
        self.assertTrue(self.save(member_record(groups=())))
        self.assertIsNone(self.number_of())

    def test_a_member_record_without_the_groups_key_is_saved_without_a_number(self):
        record = member_record()
        del record["Groups"]
        self.assertTrue(self.save(record))
        self.assertIsNone(self.number_of())

    def test_a_number_already_held_is_never_blanked(self):
        self.save(member_record())
        self.save(member_record(groups=(), modified="2026-09-05T00:00:00.000Z"))
        self.assertEqual(self.number_of(), "42")

    def test_a_number_already_held_survives_an_unreadable_household(self):
        self.save(member_record())
        self.provider = AvniProvider(api=FakeApi())
        self.context = SyncContext(self.provider)
        self.save(member_record(modified="2026-09-05T00:00:00.000Z"))
        self.assertEqual(self.number_of(), "42")

    def test_a_member_who_moves_household_takes_the_new_number(self):
        self.save(member_record())
        self.api.routes[paths.subject("hh-2")] = household_record("hh-2", number="43")
        self.save(member_record(groups=("hh-2",), modified="2026-09-05T00:00:00.000Z"))
        self.assertEqual(self.number_of(), "43")

    def test_what_is_read_without_a_fetch_never_takes_her_name_for_a_household_number(self):
        self.assertEqual(self.provider.facts("subject", member_record()).household_number, "")
        self.assertEqual(self.provider.facts("subject", household_record()).household_number, "42")

    def test_the_other_answers_are_still_saved_as_before(self):
        self.save(member_record())
        member = MemberData.objects.get()
        self.assertEqual((member.member_first_name, member.member_last_name, member.gender), ("Asha", "Patil", "2"))
        self.assertEqual(str(member.date_of_birth), "1990-05-01")
        self.assertEqual(member.slum, self.slum)


class MemberSyncCase(TestCase):
    def setUp(self):
        self.city = make_city()
        self.slum = make_slum(self.city)
        self.api = FakeApi({
            paths.subjects("Family Member", SINCE): page([]),
            paths.enrolments(PROGRAM, SINCE): page([]),
            paths.program_encounters(FOLLOW_UP, SINCE): page([]),
            paths.subject("hh-1"): household_record(),
            paths.subject("mem-1"): member_record(),
            paths.program_enrolment("enr-1"): enrolment_record(),
        })
        use_client(self.api)
        connector.reset_provider()
        self.addCleanup(reset_client)
        self.addCleanup(connector.reset_provider)
        for kind, program, encounter_type in (
                ("subject", "", ""), ("enrolment", PROGRAM, ""), ("program_encounter", PROGRAM, FOLLOW_UP)):
            SyncSwitch.objects.create(provider="avni", subject_type="Family Member", kind=kind, program=program,
                                      encounter_type=encounter_type, is_enabled=True)

    def listed(self, members=(), enrolments=(), follow_ups=()):
        self.api.routes[paths.subjects("Family Member", SINCE)] = page(list(members))
        self.api.routes[paths.enrolments(PROGRAM, SINCE)] = page(list(enrolments))
        self.api.routes[paths.program_encounters(FOLLOW_UP, SINCE)] = page(list(follow_ups))

    def sync(self):
        return daily_sync.sync_members(from_date=SINCE)


class MemberSyncOrderTests(MemberSyncCase):
    def test_members_are_listed_before_enrolments_and_enrolments_before_follow_ups(self):
        self.sync()
        listings = [call for call in self.api.calls if call.startswith("api/") and "lastModifiedDateTime" in call]
        self.assertEqual(listings, [
            paths.subjects("Family Member", SINCE), paths.enrolments(PROGRAM, SINCE),
            paths.program_encounters(FOLLOW_UP, SINCE),
        ])

    def test_a_member_registered_enrolled_and_followed_up_in_one_night_keeps_all_three(self):
        self.listed([member_record()], [enrolment_record()], [follow_up_record()])
        self.sync()
        member = MemberData.objects.get(member_uuid="mem-1")
        programme = MemberProgramData.objects.get(member=member)
        self.assertEqual((programme.program_uuid, programme.program_name), ("enr-1", PROGRAM))
        visit = MemberEncounterData.objects.get(member=member)
        self.assertEqual((visit.encounter_uuid, visit.program), ("fol-1", programme))

    def test_an_enrolment_with_no_follow_up_yet_is_saved(self):
        self.listed([member_record()], [enrolment_record()])
        self.sync()
        self.assertEqual(MemberProgramData.objects.get().program_data, {"Have you received a Cup from SA ?": "Yes"})

    def test_a_voided_enrolment_is_not_saved(self):
        self.listed([member_record()], [enrolment_record(voided=True)])
        self.sync()
        self.assertEqual(MemberProgramData.objects.count(), 0)
        self.assertTrue(Record.objects.get(external_id="enr-1").is_voided)

    def test_only_family_member_enrolments_with_a_program_are_listed(self):
        provider = AvniProvider(api=self.api)
        self.assertTrue(provider.lists_enrolments("Family Member", PROGRAM))
        self.assertFalse(provider.lists_enrolments("Family Member", ""))
        self.assertFalse(provider.lists_enrolments("Household", "Sanitation program"))
        self.assertFalse(provider.lists("enrolment"))


class ParentsOnDemandTests(MemberSyncCase):
    """Whatever arrives first, what it hangs off is synced before it."""

    def test_an_enrolment_whose_member_was_never_synced_brings_her_and_her_household(self):
        self.listed(enrolments=[enrolment_record()])
        self.sync()
        member = MemberData.objects.get(member_uuid="mem-1")
        self.assertEqual(member.household_number, "42")
        self.assertTrue(HouseholdData.objects.filter(slum=self.slum, household_number="42").exists())
        self.assertEqual(MemberProgramData.objects.get(member=member).program_uuid, "enr-1")

    def test_a_follow_up_whose_member_was_never_synced_brings_her_and_her_enrolment(self):
        self.listed(follow_ups=[follow_up_record()])
        self.sync()
        member = MemberData.objects.get(member_uuid="mem-1")
        programme = MemberProgramData.objects.get(member=member)
        self.assertEqual(MemberEncounterData.objects.get(member=member).program, programme)

    def test_a_member_whose_household_was_never_synced_brings_the_household(self):
        self.listed([member_record()])
        self.sync()
        household = HouseholdData.objects.get(slum=self.slum, household_number="42")
        self.assertEqual(Record.objects.get(external_id="hh-1").household, household)
        self.assertEqual(MemberData.objects.get().household_number, "42")

    def test_a_household_the_tables_already_hold_is_read_but_not_saved_again(self):
        HouseholdData.objects.create(household_number="42", slum=self.slum, city=self.city,
                                     submission_date="2020-01-01T00:00:00Z", rhs_data={"kept": "yes"})
        self.listed([member_record()])
        self.sync()
        self.assertEqual(HouseholdData.objects.get().rhs_data, {"kept": "yes"})
        self.assertFalse(Record.objects.filter(external_id="hh-1").exists())
        self.assertEqual(MemberData.objects.get().household_number, "42")

    def test_a_household_type_that_is_switched_off_is_not_synced_through_its_member(self):
        SyncSwitch.objects.create(provider="avni", subject_type="Household", kind="subject", is_enabled=False)
        self.listed([member_record()])
        self.sync()
        self.assertEqual(HouseholdData.objects.count(), 0)
        self.assertEqual(MemberData.objects.get().household_number, "42", "the number is still read")

    def test_a_member_that_cannot_be_read_fails_only_her_own_enrolment(self):
        del self.api.routes[paths.subject("mem-1")]
        self.api.routes[paths.subject("mem-2")] = member_record("mem-2")
        self.listed(enrolments=[enrolment_record("enr-1", "mem-1"), enrolment_record("enr-2", "mem-2")])
        self.sync()
        self.assertEqual(list(MemberProgramData.objects.values_list("program_uuid", flat=True)), ["enr-2"])

    def test_two_members_of_one_household_fetch_and_save_it_once(self):
        self.api.routes[paths.subject("mem-2")] = member_record("mem-2")
        self.listed([member_record("mem-1"), member_record("mem-2")])
        self.sync()
        self.assertEqual(self.api.calls.count(paths.subject("hh-1")), 1)
        self.assertEqual(HouseholdData.objects.count(), 1)


class StoreIdentityTests(MemberSyncCase):
    """What the survey store holds for a member's records."""

    def test_a_members_own_row_is_linked_to_her_household_with_the_number_left_blank(self):
        self.listed([member_record()])
        self.sync()
        row = Record.objects.get(external_id="mem-1")
        self.assertEqual((row.household_number, row.household), ("", HouseholdData.objects.get()))

    def test_her_enrolment_and_follow_up_carry_the_households_number_and_link(self):
        self.listed([member_record()], [enrolment_record()], [follow_up_record()])
        self.sync()
        household = HouseholdData.objects.get()
        for external_id in ("enr-1", "fol-1"):
            row = Record.objects.get(external_id=external_id)
            self.assertEqual((row.household_number, row.household), ("42", household), external_id)

    def test_two_members_with_the_same_first_name_in_one_slum_are_both_stored(self):
        self.api.routes[paths.subject("hh-2")] = household_record("hh-2", number="43")
        self.listed([member_record("mem-1"), member_record("mem-2", groups=("hh-2",)), member_record("mem-3")])
        results = self.sync()
        self.assertEqual(Record.objects.filter(subject_type="Family Member", kind="subject").count(), 3)
        self.assertEqual(MemberData.objects.count(), 3)
        self.assertEqual(results["households:Family Member"], 3)

    def test_a_member_in_no_household_is_stored_with_no_number_not_her_name(self):
        self.listed([member_record(groups=())])
        self.sync()
        self.assertEqual(Record.objects.get(external_id="mem-1").household_number, "")

    def test_a_households_own_number_still_comes_from_its_first_name(self):
        self.listed([member_record()])
        self.sync()
        self.assertEqual(Record.objects.get(external_id="hh-1").household_number, "42")


class GapsCloseTests(MemberSyncCase):
    """A record the store has already seen is saved again when the member tables lack it."""

    def rerun(self):
        self.api.calls = []
        connector.reset_provider()
        return self.sync()

    def test_an_enrolment_the_member_tables_lost_is_saved_on_the_next_run(self):
        self.listed([member_record()], [enrolment_record()])
        self.sync()
        MemberProgramData.objects.all().delete()
        self.rerun()
        self.assertEqual(MemberProgramData.objects.get().program_uuid, "enr-1")

    def test_a_member_the_tables_lost_is_saved_on_the_next_run(self):
        self.listed([member_record()])
        self.sync()
        MemberData.objects.all().delete()
        self.rerun()
        self.assertEqual(MemberData.objects.get().household_number, "42")

    def test_a_member_whose_number_was_blanked_gets_it_back_on_the_next_run(self):
        self.listed([member_record()])
        self.sync()
        MemberData.objects.update(household_number=None)
        self.rerun()
        self.assertEqual(MemberData.objects.get().household_number, "42")

    def test_a_follow_up_the_member_tables_never_received_is_saved_on_the_next_run(self):
        self.listed([member_record()], [enrolment_record()], [follow_up_record()])
        self.sync()
        MemberEncounterData.objects.all().delete()
        self.rerun()
        self.assertEqual(MemberEncounterData.objects.get().encounter_uuid, "fol-1")

    def test_an_unchanged_member_who_is_complete_costs_no_fetch_and_no_write(self):
        self.listed([member_record()], [enrolment_record()], [follow_up_record()])
        self.sync()
        self.rerun()
        self.assertEqual(self.api.calls, [
            paths.subjects("Family Member", SINCE), paths.enrolments(PROGRAM, SINCE),
            paths.program_encounters(FOLLOW_UP, SINCE),
        ])

    def test_an_unchanged_member_in_no_household_is_not_saved_again_every_night(self):
        self.listed([member_record(groups=())])
        self.sync()
        saved = self.rerun()
        self.assertEqual(saved.get("households:Family Member"), 0)

    def test_an_older_follow_up_does_not_replace_the_one_held(self):
        self.listed([member_record()], [enrolment_record()],
                    [follow_up_record("fol-2", modified="2026-09-09T00:00:00.000Z")])
        self.sync()
        self.listed([member_record()], [enrolment_record()],
                    [follow_up_record("fol-1"), follow_up_record("fol-2", modified="2026-09-09T00:00:00.000Z")])
        self.rerun()
        self.assertEqual(MemberEncounterData.objects.get().encounter_uuid, "fol-2")
