CREATE VIEW vw_rhsfollowup

AS

SELECT
r.household_number,
r.followup_data::json->>'group_oi8ts04/Have_you_applied_for_individua' as toilet_applied_under_sbm,
r.followup_data::json->>'group_oi8ts04/Type_of_SBM_toilets' as sbm_toilets_type,
r.followup_data::json->>'group_oi8ts04/How_many_installments_have_you' as no_of_installments_received,
r.followup_data::json->>'group_oi8ts04/When_did_you_receive_ur_first_installment' as first_installment_date,
r.followup_data::json->>'group_oi8ts04/When_did_you_receive_r_second_installment' as second_installment_date,
r.followup_data::json->>'group_oi8ts04/When_did_you_receive_ur_third_installment' as third_installment_date,
#r.followup_data::json->>'group_oi8ts04/Status_of_toilet_under_SBM' as sbm_toilet_status,
#r.followup_data::json->>'group_oi8ts04/How_many_installments_have_you' as no_of_i,

#r.followup_data::json->>'group_oi8ts04/If_built_by_contract_ow_satisfied_are_you' as contractor_construction_satisfaction_level,
r.followup_data::json->>'group_oi8ts04/What_was_the_cost_in_to_build_the_toilet' as toilet_cost,
#r.followup_data::json->>'group_oi8ts04/C1' as current_place_of_defecation1,
#r.followup_data::json->>'group_oi8ts04/C2' as current_place_of_defecation2,
#r.followup_data::json->>'group_oi8ts04/C3' as current_place_of_defecation_no_sbm,
#r.followup_data::json->>'group_oi8ts04/C4' as current_place_of_defecation_status_of_sbm,
#r.followup_data::json->>'group_oi8ts04/C5' as current_place_of_defecation_yet_to_start_sbm,
CASE r.followup_data::json->>'group_oi8ts04/Current_place_of_defecation'
WHEN '01' THEN 'SBM (Installment)'
WHEN '02' THEN 'SBM (Contractor)'
WHEN '03' THEN 'Toilet by SA (SBM)'
WHEN '04' THEN 'Toilet by other NGO (SBM)'
WHEN '05' THEN 'Own toilet'
WHEN '06' THEN 'Toilet by other NGO'
WHEN '07' THEN 'Toilet by SA'
WHEN '08' THEN 'None of the above'
WHEN '09' THEN 'Use CTB'
WHEN '10' THEN 'Shared toilet'
WHEN '11' THEN 'Public toilet outside slum'
WHEN '12' THEN 'None of the above'
WHEN '13' THEN 'Non-functional, hence CTB'
ELSE NULL END AS current_place_of_defecation,
r.followup_data::json->>'group_oi8ts04/Is_there_availabilit_onnect_to_the_toilet' as drainage_connection_available,
r.followup_data::json->>'group_oi8ts04/Are_you_interested_in_an_indiv' as interested_in_toilet,
#r.followup_data::json->>'group_oi8ts04/What_kind_of_toilet_would_you_like' as toilet_preference,
#r.followup_data::json->>'group_oi8ts04/Under_what_scheme_wo_r_toilet_to_be_built' as scheme_preference,
r.followup_data::json->>'group_oi8ts04/If_yes_why' as toilet_yes_reason,
r.followup_data::json->>'group_oi8ts04/If_no_why' as toilet_no_reason,
r.followup_data::json->>'group_oi8ts04/What_is_the_toilet_connected_to' as toilet_connected_to,
r.followup_data::json->>'group_oi8ts04/Who_all_use_toilets_in_the_hou' as toilet_used_by,
r.followup_data::json->>'group_oi8ts04/Reason_for_not_using_toilet' as toilet_not_used_reason,
r.followup_data::json->>'group_oi8ts04/OD1' as open_defecation_practiced,
r.flag_followup_in_rhs,
vw.status,
r.city_id,
r.slum_id,
s.name as Slum_Name,
c.city_name,
r.created_date,
r.submission_date

FROM graphs_followupdata as r,  master_slum as s, master_city as mcc, master_cityreference as c, master_electoralward as me,
master_administrativeward as ma, vw_toiletconstruction as vw

WHERE r.slum_id = s.id AND s.electoral_ward_id= me.id AND me.administrative_ward_id=ma.id AND mcc.id = ma.city_id AND c.id = mcc.name_id and vw.household_number = r.household_number and vw.slum_id = r.slum_id
