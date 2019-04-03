CREATE VIEW vw_rhs_toilet 

AS

select
vw1.household_number,
vw1.slum_id,
vw1.slum_name,
vw1.city_name,
vw1.sbm_toilets_type,
vw1.current_place_of_defecation,
vw2.status,
vw1.created_date

from vw_rhsfollowup vw1 
left join vw_toiletconstruction vw2 on vw1.household_number = vw2.household_number and vw1.slum_id = vw2.slum_id 
where flag_followup_in_rhs = 'true'




