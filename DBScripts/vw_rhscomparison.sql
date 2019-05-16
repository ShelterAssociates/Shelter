DROP VIEW vw_rhscomparison;
CREATE VIEW vw_rhscomparison
AS
select
        s.household_number,
        f.current_place_of_defecation,
        s.slum_id,
        s.slum_name,
        f.city_name,
        --f.drainage_connection_available,
        --f.interested_in_toilet,
        --f.toilet_yes_reason,
        --f.toilet_no_reason,
        --f.toilet_connected_to,
        --f.toilet_used_by,
        --f.toilet_not_used_reason,
        f.open_defecation_practiced,
        f.flag_followup_in_rhs,
	vw.status,
		s.created_date
from vw_rhsfollowup_separate s left join  (select household_number, slum_id, max(created_date) as MaxDate from vw_rhsfollowup_separate group by household_number, slum_id) 
tm  on tm.household_number = s.household_number and tm.slum_id = s.slum_id and tm.MaxDate = s.created_date
left join vw_rhsfollowup f on f.slum_id = s.slum_id and f.household_number = s.household_number
left join vw_toiletconstruction vw on vw.household_number = s.household_number and vw.slum_id = s.slum_id
where f.flag_followup_in_rhs = true 
