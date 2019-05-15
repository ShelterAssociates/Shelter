DROP VIEW vw_rhsdata;

CREATE VIEW vw_rhsdata

AS

select
r.household_number,
r.rhs_data::json->>'admin_ward' as admin_ward,
r.rhs_data::json->>'slum_name' as shelter_slum_name,
#r.rhs_data::json->>'Date_of_survey' as survey_date,
#r.rhs_data::json->>'Name_s_of_the_surveyor_s' as surveyor_name,
r.rhs_data::json->>'Type_of_structure_occupancy' as structure_occupancy_type,
r.rhs_data::json->>'Type_of_unoccupied_house' as unoccupied_house_type,
#r.rhs_data::json->>'Parent_household_number' as parent_household_number,
#r.rhs_data::json->>'group_og5bx85/Type_of_survey' as survey_type,
r.rhs_data::json->>'group_el9cl08/Number_of_household_members' as no_of_household_member,
#r.rhs_data::json->>'group_el9cl08/Do_you_have_any_girl_child_chi' as girl_child_y_n,
r.rhs_data::json->>'group_el9cl08/How_many' as no_of_girl_child,
r.rhs_data::json->>'group_el9cl08/Type_of_structure_of_the_house' as house_structure_type,
r.rhs_data::json->>'group_el9cl08/Ownership_status_of_the_house' as house_ownership_status,
r.rhs_data::json->>'group_el9cl08/House_area_in_sq_ft' as house_area,
r.rhs_data::json->>'group_el9cl08/Type_of_water_connection' as water_connection_type,
r.rhs_data::json->>'group_el9cl08/Facility_of_solid_waste_collection' as solid_waste_collection_facility,
r.rhs_data::json->>'group_el9cl08/Does_any_household_m_n_skills_given_below' as construction_skills_any,
#r.ff_data::json->>'group_oh4zf84/Name_of_Native_villa_district_and_state' as household_native_of,
#r.ff_data::json->>'group_oh4zf84/Duration_of_stay_in_the_city_in_Years' as duration_of_stay_in_city_years,
#r.ff_data::json->>'group_oh4zf84/Duration_of_stay_in_settlement_in_Years' as duration_of_stay_in_settlement_years,
#r.ff_data::json->>'group_oh4zf84/Type_of_house' as type_of_house,
#r.ff_data::json->>'group_oh4zf84/Ownership_status' as ff_ownership_status,
r.ff_data::json->>'group_im2th52/Total_family_members' as family_members_count,
r.ff_data::json->>'group_im2th52/Number_of_Male_members' as male_members_count,
r.ff_data::json->>'group_im2th52/Number_of_Female_members' as female_members_count,
r.ff_data::json->>'group_im2th52/Number_of_Children_under_5_years_of_age' as count_of_children_under_5,
r.ff_data::json->>'group_im2th52/Number_of_members_over_60_years_of_age' as count_of_members_over_60,
r.ff_data::json->>'group_im2th52/Number_of_Girl_children_between_0_18_yrs' as count_of_girls_under_18,
r.ff_data::json->>'group_im2th52/Number_of_disabled_members' as count_of_disabled_members,
#r.ff_data::json->>'group_im2th52/If_yes_specify_type_of_disability' as type_of_disability,
#r.ff_data::json->>'group_im2th52/Number_of_earning_members' as count_of_earning_members,
#r.ff_data::json->>'group_im2th52/Occupation_s_of_earning_membe' as occupation_of_earning_members,
#r.ff_data::json->>'group_im2th52/Approximate_monthly_family_income_in_Rs' as monthly_income,
r.ff_data::json->>'group_ne3ao98/Where_the_individual_ilet_is_connected_to' as ff_individual_toilet_connected_to,
r.ff_data::json->>'group_ne3ao98/Who_has_built_your_toilet' as toilet_built_by,
r.ff_data::json->>'group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet' as individual_toilet_upgraded,
r.ff_data::json->>'group_ne3ao98/Cost_of_upgradation_in_Rs' as cost_of_upgradation,
r.ff_data::json->>'group_ne3ao98/Use_of_toilet' as use_of_toilet,
r.created_date,
r.submission_date,
r.slum_id,
r.city_id,
s.name as Slum_Name,
c.city_name, 
sd.sponsor_name
FROM graphs_householddata as r LEFT JOIN vw_sponsor_details as sd on r.slum_id= sd.slum_id AND r.household_number::varchar = sd.household_number::varchar,  master_slum as s, master_city as mcc, master_cityreference as c, master_electoralward as me,
master_administrativeward as ma

WHERE r.slum_id = s.id AND s.electoral_ward_id= me.id AND me.administrative_ward_id=ma.id AND mcc.id = ma.city_id AND c.id = mcc.name_id 
