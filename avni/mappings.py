"""Concept-name to rhs_data-key maps.

The mastersheet and dashboards still read the KoboToolbox-era keys, so every
AVNI observation is renamed on the way in. Values are copied from the legacy
graphs/sync_avni_data.py and graphs/structure_registration_sync.py unchanged.
"""

import logging
import re

logger = logging.getLogger(__name__)

# rhs_data key -> AVNI concept name (household registration)
RHS_KEYS = {
    "Enter_household_number_again": "Househhold number",
    "_notes": "Comment if any ?",
    "Name_s_of_the_surveyor_s": "Name of the surveyor",
    "Household_number": "First name",
    "group_el9cl08/Aadhar_number": "Aadhaar number",
    "group_el9cl08/Enter_the_10_digit_mobile_number": "Enter the 10 digit mobile number",
    "group_el9cl08/Ownership_status_of_the_house": "Ownership status of the house_1",
    "Date_of_survey": "Date of Survey",
    "group_el9cl08/House_area_in_sq_ft": "House area in square feets.",
    "group_og5bx85/Full_name_of_the_head_of_the_household": "Full name of the head of the household",
    "group_el9cl08/Number_of_household_members": "Number of household members",
    "Type_of_unoccupied_house": "Type of unoccupied house_1",
    "group_el9cl08/Type_of_structure_of_the_house": "Type of structure of the house_1",
    "Parent_household_number": "Parent household number",
    "Type_of_structure_occupancy": "Type of structure occupancy_1",
    "group_el9cl08/Do_you_have_any_girl_child_chi": "Do you have any girl child/children under the age of 18?_",
    "group_oi8ts04/Current_place_of_defecation": "Current place of defecation",
    "group_el9cl08/Type_of_water_connection": "Water Sub Category",
    "group_el9cl08/Facility_of_solid_waste_collection": "How do you dispose your solid waste ?",
}

# rhs_data key -> AVNI concept name (family factsheet)
FACTSHEET_KEYS = {
    "Note": "Note",
    "group_im2th52/Number_of_Children_under_5_years_of_age": "Number of Children under 5 years of age",
    "group_ne3ao98/Cost_of_upgradation_in_Rs": "Cost of upgradation",
    "group_oh4zf84/Duration_of_stay_in_settlement_in_Years": "Duration of stay in this current settlement (in Years)",
    "group_oh4zf84/Ownership_status": "Ownership status of the house_1",
    "group_im2th52/Number_of_earning_members": "Number of earning members",
    "group_im2th52/Occupation_s_of_earning_membe": "Occupation(s) of earning members",
    "Family_Photo": "Family Photo",
    "group_ne3ao98/Who_has_built_your_toilet": "Who has built your toilet ?",
    "group_im2th52/Approximate_monthly_family_income_in_Rs": "Approximate monthly family income (in Rs.)",
    "group_vq77l17/Household_number": "Househhold number",
    "group_im2th52/Total_family_members": "Total family members",
    "group_oh4zf84/Type_of_house": "Type of house*",
    "group_im2th52Number_of_members_over_60_years_of_age": "Number of members over 60 years of age",
    "group_ne3ao98/Where_the_individual_ilet_is_connected_to": "Where the individual toilet is connected ?",
    "group_vq77l17/Settlement_address": "Settlement address",
    "group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet": "Have you upgraded your toilet/bathroom/house while constructing individual toilet?",
    "group_im2th52/Number_of_disabled_members": "Number of Disabled members",
    "group_oh4zf84/Duration_of_stay_in_the_city_in_Years": "Duration of stay in the city (in Years)",
    "group_im2th52/Number_of_Male_members": "Number of Male members",
    "group_oh4zf84/Name_of_the_family_head": "Name of the family head",
    "Toilet_Photo": "Toilet Photo",
    "group_ne3ao98/Use_of_toilet": "Use of toilet",
    "group_im2th52/Number_of_Girl_children_between_0_18_yrs": "Number of Girl children between 0-18 yrs",
    "group_im2th52/Number_of_Female_members": "Number of Female members",
    "group_oh4zf84/Name_of_Native_villa_district_and_state": "What is your native place (village, town, city) ?",
}
FACTSHEET_MULTISELECT = ["Occupation(s) of earning members", "Use of toilet"]

# rhs_data key -> AVNI concept name (sanitation encounter)
SANITATION_KEYS = {
    "group_oi8ts04/Have_you_applied_for_individua": "Have you applied for an individual toilet under SBM?_1",
    "group_oi8ts04/Status_of_toilet_under_SBM": "Status of toilet under SBM ?",
    "group_oi8ts04/What_is_the_toilet_connected_to": "Where the individual toilet is connected to ?",
    "group_oi8ts04/Who_all_use_toilets_in_the_hou": "Who all use toilets in the household ?",
    "group_oi8ts04/What_was_the_cost_in_to_build_the_toilet": "What was the cost incurred to build the toilet?",
    "group_oi8ts04/Type_of_SBM_toilets": "Type of SBM toilets ?",
    "group_oi8ts04/Reason_for_not_using_toilet": "Reason for not using toilet ?",
    "group_oi8ts04/How_many_installments_have_you": "How many installments have you received ?",
    "group_oi8ts04/When_did_you_receive_ur_first_installment": "When did you receive your first SBM installment?",
    "group_oi8ts04/When_did_you_receive_r_second_installment": "When did you receive your second SBM installment?",
    "group_oi8ts04/When_did_you_receive_ur_third_installment": "When did you receive your third SBM installment?",
    "group_oi8ts04/If_built_by_contract_ow_satisfied_are_you": "If built by contractor, how satisfied are you?",
    "group_oi8ts04/OD1": "Does any member of the household go for open defecation ?",
    "group_oi8ts04/Current_place_of_defecation": "Final current place of defecation",
    "group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets": "Is there availability of drainage to connect it to the toilet?",
    "group_oi8ts04/Are_you_interested_in_an_indiv": "Are you interested in an individual toilet ?",
    "group_oi8ts04/What_kind_of_toilet_would_you_like": "What kind of toilet would you like ?",
    "group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built": "Under what scheme would you like your toilet to be built ?",
    "group_oi8ts04/If_yes_why": "If yes for individual toilet , why?",
    "group_oi8ts04/If_no_why": "If no for individual toilet , why?",
    "group_oi8ts04/Which_Community_Toil_r_family_members_use": "Which CTB do your family members use ?",
    "group_el9cl08/Does_any_household_m_n_skills_given_below": "Does any household member have any of the construction skills given below ?",
}

# Single renames applied to direct encounters before merging into rhs_data.
ENCOUNTER_RENAMES = {
    "Water": {"Type of water connection ?": "group_el9cl08/Type_of_water_connection"},
    "Waste": {"How do you dispose your solid waste ?": "group_el9cl08/Facility_of_solid_waste_collection"},
}

# AVNI concept name -> rhs_data key, used by the Structure / DSES sync.
# Anything not listed is written through unchanged.
KNOWN_QUESTION_MAP = {
    "uuid": "rhs_uuid",
    "first_name": "Household_number",
    "First name": "Household_number",
    "Househhold number": "Enter_household_number_again",
    "Ward No": "Select Ward",
    "Date of Survey": "Date_of_survey",
    "Additional Comment": "Comment ?",
    "Comment": "Comment ?",
    "Surveyor (normal/coded)": "Name_s_of_the_surveyor_s",
    "Name of the surveyor": "Name_s_of_the_surveyor_s",
    "Updated by (normal/coded)": "Name of surveyor who updated the data",
    "Type of structure occupancy_1": "Type_of_structure_occupancy",
    "Type of structure occupancy": "Type_of_structure_occupancy",
    "Type of structure of the house_1": "group_el9cl08/Type_of_structure_of_the_house",
    "Type of structure of the house": "group_el9cl08/Type_of_structure_of_the_house",
    "Ownership status of the house_1": "group_el9cl08/Ownership_status_of_the_house",
    "Ownership status of the house": "group_el9cl08/Ownership_status_of_the_house",
    "Type of unoccupied house_1": "Type_of_unoccupied_house",
    "Type of unoccupied house": "Type_of_unoccupied_house",
    "Number of flats in the building ?": "Number of units in the building ?",
    "Parent household number": "Parent_household_number",
    "House area in square feets.": "group_el9cl08/House_area_in_sq_ft",
    "Full name of the head of the household": "group_og5bx85/Full_name_of_the_head_of_the_household",
    "Enter the 10 digit mobile number": "group_el9cl08/Enter_the_10_digit_mobile_number",
    "Contact number of respondent": "group_el9cl08/Enter_the_10_digit_mobile_number",
    "Number of household members": "group_el9cl08/Number_of_household_members",
    "total_members": "group_el9cl08/Number_of_household_members",
    "total_male_members": "Total number of male members (including children)",
    "total_female_members": "Total number of female members (including children)",
    "total_third_gender_members": "Total number of third gender members (including children)?",
    "Aadhaar number": "group_el9cl08/Aadhar_number",
    "Aadhaar Number of the beneficiary": "group_el9cl08/Aadhar_number",
    "Do you have any girl child/children under the age of 18?_": "group_el9cl08/Do_you_have_any_girl_child_chi",
    "Type of water connection ?": "group_el9cl08/Type_of_water_connection",
    "Water Sub Category": "group_el9cl08/Type_of_water_connection",
    "How do you dispose your solid waste ?": "group_el9cl08/Facility_of_solid_waste_collection",
    "How do you dispose your solid waste": "group_el9cl08/Facility_of_solid_waste_collection",
    "Current place of defecation": "group_oi8ts04/Current_place_of_defecation",
    "Final current place of defecation": "group_oi8ts04/Current_place_of_defecation",
    "Have you applied for an individual toilet under SBM?_1": "group_oi8ts04/Have_you_applied_for_individua",
    "Status of toilet under SBM ?": "group_oi8ts04/Status_of_toilet_under_SBM",
    "Where the individual toilet is connected to ?": "group_oi8ts04/What_is_the_toilet_connected_to",
    "Who all use toilets in the household ?": "group_oi8ts04/Who_all_use_toilets_in_the_hou",
    "What was the cost incurred to build the toilet?": "group_oi8ts04/What_was_the_cost_in_to_build_the_toilet",
    "Type of SBM toilets ?": "group_oi8ts04/Type_of_SBM_toilets",
    "Reason for not using toilet ?": "group_oi8ts04/Reason_for_not_using_toilet",
    "How many installments have you received ?": "group_oi8ts04/How_many_installments_have_you",
    "When did you receive your first SBM installment?": "group_oi8ts04/When_did_you_receive_ur_first_installment",
    "When did you receive your second SBM installment?": "group_oi8ts04/When_did_you_receive_r_second_installment",
    "When did you receive your third SBM installment?": "group_oi8ts04/When_did_you_receive_ur_third_installment",
    "If built by contractor, how satisfied are you?": "group_oi8ts04/If_built_by_contract_ow_satisfied_are_you",
    "Does any member of the household go for open defecation ?": "group_oi8ts04/OD1",
    "Is there availability of drainage to connect it to the toilet?": "group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets",
    "Is drainage line available ?": "group_oi8ts04/Is_there_availabilit_onnect_to_the_toilets",
    "Are you interested in an individual toilet ?": "group_oi8ts04/Are_you_interested_in_an_indiv",
    "What kind of toilet would you like ?": "group_oi8ts04/What_kind_of_toilet_would_you_like",
    "Under what scheme would you like your toilet to be built ?": "group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built",
    "If yes for individual toilet , why?": "group_oi8ts04/If_yes_why",
    "If no for individual toilet , why?": "group_oi8ts04/If_no_why",
    "Which CTB do your family members use ?": "group_oi8ts04/Which_Community_Toil_r_family_members_use",
    "Does any household member have any of the construction skills given below ?": "group_el9cl08/Does_any_household_m_n_skills_given_below",
    "Does any household member have any of the construction skills ?": "group_el9cl08/Does_any_household_m_n_skills_given_below",
}

# Lookup columns that never belong inside the rhs_data blob.
METADATA_KEYS = {
    "Slum", "Slum id", "id", "created_by_user", "last_modified_by_user",
    "created_date_time", "last_modified_date_time", "registration_date",
    "registration_location", "Subject ID", "Voided",
}

SHOP_ONLY_KEYS = ["If shop, type of occupancy ?", "Type of shop"]
UNOCCUPIED_ONLY_KEYS = ["Type_of_unoccupied_house", "Parent_household_number"]

LEADING_ZEROS = re.compile(r"^0*(\d+)([A-Za-z].*)$")


def household_number_from(value):
    """'0042' -> '42', '0022A' -> '22A', 42.0 -> '42'. Blank stays blank."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if text.isdigit():
        return str(int(text))
    match = LEADING_ZEROS.match(text)
    return match.group(1) + match.group(2) if match else text


def merge_rhs_keys(existing, incoming):
    """Rename incoming AVNI concepts to rhs keys and merge them over existing data."""
    incoming = dict(incoming)
    for rhs_key, concept in RHS_KEYS.items():
        if concept in incoming:
            incoming[rhs_key] = incoming.pop(concept)
    occupancy = existing.get("Type_of_structure_occupancy")
    drop = SHOP_ONLY_KEYS if occupancy == "Shop" else UNOCCUPIED_ONLY_KEYS if occupancy == "Unoccupied house" else []
    for key in drop:
        existing.pop(key, None)
    existing.update(incoming)
    return existing


def map_factsheet_keys(observations):
    concept_to_key = {concept: key for key, concept in FACTSHEET_KEYS.items()}
    mapped = {}
    for concept, value in observations.items():
        key = concept_to_key.get(concept, concept)
        if concept in FACTSHEET_MULTISELECT and isinstance(value, list):
            value = ",".join(value)
        mapped[key] = value
    return mapped


def map_sanitation_keys(observations):
    mapped = dict(observations)
    for key, concept in SANITATION_KEYS.items():
        if concept in mapped:
            mapped[key] = mapped.pop(concept)
    return mapped


def rename_keys(data, renames):
    for old, new in renames.items():
        if old in data:
            data[new] = data.pop(old)
    return data


def map_known_questions(observations):
    return {
        KNOWN_QUESTION_MAP.get(key, key): value
        for key, value in observations.items()
        if key not in METADATA_KEYS
    }


def normalize_occupancy(data):
    """'Functioning of the structure' answers Shop / Individual home + shop become the occupancy key."""
    if data.get("Functioning of the structure") in ("Shop", "Individual home + shop"):
        data["Type_of_structure_occupancy"] = data.pop("Functioning of the structure")
    return data


def apply_household_overrides(data):
    """Business rules applied to household registration answers."""
    if data.get("Do you have a toilet at home?") == "Yes":
        data["Current place of defecation"] = "Own toilet"
    if data.get("Ownership status of the house_1") == "Own house/Shop":
        data["Ownership status of the house_1"] = "Own house"
    return data


def apply_structure_overrides(rhs_data):
    """Same rules, expressed on already-mapped Structure / DSES keys."""
    if rhs_data.get("Do you have a toilet at home?") == "Yes":
        rhs_data["group_oi8ts04/Current_place_of_defecation"] = "Own toilet"
    if rhs_data.get("group_el9cl08/Ownership_status_of_the_house") == "Own house/Shop":
        rhs_data["group_el9cl08/Ownership_status_of_the_house"] = "Own house"
    return rhs_data
