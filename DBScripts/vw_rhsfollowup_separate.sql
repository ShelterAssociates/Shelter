DROP VIEW vw_rhsfollowup_separate;
CREATE VIEW vw_rhsfollowup_separate
as
SELECT 
v.slum_id,
v.created_date,
v.household_number,
v.slum_name,
v.city_name,
v.current_place_of_defecation,
v.open_defecation_practiced

 FROM vw_rhsfollowup v WHERE v.flag_followup_in_rhs = 'false'
