
/*Toilet Construction*/
DROP VIEW vw_rhs_toilet;
DROP VIEW vw_rhsfollowup_toilet;
DROP VIEW vw_toiletconstruction;

CREATE VIEW vw_toiletconstruction as 
SELECT

mc.household_number,
mc.agreement_date,
mc.agreement_cancelled,
mc.septic_tank_date,
mc.phase_one_material_date,
mc.phase_two_material_date,
mc.phase_three_material_date,
mc.completion_date,
mc1.days_between_agreement_phase1,
mc2.days_between_phase1_phase2,
mc3.days_between_phase2_phase3,
mc4.days_between_agreement_completed,
mc10.days_between_phase1_completed,
mc5.phase1_delayed,
mc6.phase2_delayed,
mc7.phase3_delayed,
mc8.completion_delayed,
mc9.days_between_agreement_use,
mc.use_of_toilet,
mc.toilet_connected_to,
mc.factsheet_done,
/*Status Description*/
CASE mc.status 
WHEN '1' THEN 'Agreement Done'
WHEN '2' THEN 'Agreement Cancelled'
WHEN '3' THEN 'Material Not Given'
WHEN '4' THEN 'Construction Not Started'
WHEN '5' THEN 'Under Construction'
WHEN '6' THEN 'Completed'
WHEN '7' THEN 'Written Off'
ELSE NULL END status,
mc.comment,
sp.sponsor_name,
mc.slum_id,
s.name as Slum_Name,
c.city_name, 
cc.coordinates,
cc.longitude,
cc.latitude

FROM mastersheet_toiletconstruction as mc 

/*Calculating days between agreement, phase1, phase 2, phase 3, completion dates */

LEFT JOIN (SELECT household_number, slum_id, phase_one_material_date-agreement_date as "days_between_agreement_phase1" FROM mastersheet_toiletconstruction WHERE status = '6' AND agreement_date IS NOT NULL AND phase_one_material_date IS NOT NULL) mc1 on mc1.household_number = mc.household_number AND mc1.slum_id = mc.slum_id

LEFT JOIN (SELECT household_number, slum_id, phase_two_material_date-phase_one_material_date as "days_between_phase1_phase2" FROM mastersheet_toiletconstruction WHERE status = '6' AND phase_one_material_date IS NOT NULL AND phase_two_material_date IS NOT NULL) mc2 on mc2.household_number = mc.household_number AND mc2.slum_id = mc.slum_id

LEFT JOIN (SELECT household_number, slum_id, phase_three_material_date-phase_two_material_date as "days_between_phase2_phase3" FROM mastersheet_toiletconstruction WHERE status = '6' AND phase_two_material_date IS NOT NULL AND phase_three_material_date IS NOT NULL) mc3 on mc3.household_number = mc.household_number AND mc3.slum_id = mc.slum_id

LEFT JOIN (SELECT household_number, slum_id, completion_date-agreement_date as "days_between_agreement_completed" FROM mastersheet_toiletconstruction WHERE status = '6' AND agreement_date IS NOT NULL AND completion_date IS NOT NULL) mc4 on mc4.household_number = mc.household_number AND mc4.slum_id = mc.slum_id

LEFT JOIN (SELECT household_number, slum_id, completion_date-phase_one_material_date as "days_between_phase1_completed" FROM mastersheet_toiletconstruction WHERE status = '6' AND agreement_date IS NOT NULL AND completion_date IS NOT NULL) mc10 on mc10.household_number = mc.household_number AND mc10.slum_id = mc.slum_id

LEFT JOIN (SELECT household_number, slum_id, use_of_toilet-agreement_date as "days_between_agreement_use" FROM mastersheet_toiletconstruction WHERE status = '6' AND agreement_date IS NOT NULL AND completion_date IS NOT NULL) mc9 on mc9.household_number = mc.household_number AND mc9.slum_id = mc.slum_id

/*Constructing logic for calculating delays after agreement is done*/

LEFT JOIN (SELECT household_number, slum_id, 

	CASE agreement_date IS NOT NULL 
	    WHEN phase_one_material_date IS NULL AND current_date - agreement_date > 8 THEN 1
		WHEN phase_one_material_date IS NOT NULL AND phase_one_material_date - agreement_date>8 THEN 1 
		
		ELSE 0 END AS "phase1_delayed" FROM mastersheet_toiletconstruction)

mc5 on mc5.household_number = mc.household_number AND mc5.slum_id = mc.slum_id


LEFT JOIN (SELECT household_number, slum_id, 

	CASE phase_one_material_date IS NOT NULL 
	    WHEN phase_two_material_date IS NULL AND current_date - phase_one_material_date>8 THEN 1
		WHEN phase_two_material_date IS NOT NULL AND phase_two_material_date - phase_one_material_date > 8 THEN 1 
		
		ELSE 0 END AS "phase2_delayed" FROM mastersheet_toiletconstruction)

mc6 on mc6.household_number = mc.household_number AND mc6.slum_id = mc.slum_id

LEFT JOIN (SELECT household_number, slum_id, 

	CASE phase_two_material_date IS NOT NULL 
	    WHEN phase_three_material_date IS NULL AND current_date - phase_two_material_date>8 THEN 1
		WHEN phase_three_material_date IS NOT NULL AND phase_three_material_date - phase_two_material_date > 8 THEN 1 
		
		ELSE 0 END AS "phase3_delayed" FROM mastersheet_toiletconstruction)

mc7 on mc7.household_number = mc.household_number AND mc7.slum_id = mc.slum_id

LEFT JOIN (SELECT household_number, slum_id, 

	CASE phase_three_material_date IS NOT NULL 
	    WHEN completion_date IS NULL AND current_date - phase_three_material_date > 8 THEN 1
		WHEN completion_date IS NOT NULL AND completion_date - phase_three_material_date > 8 THEN 1 
		
		ELSE 0 END AS "completion_delayed" FROM mastersheet_toiletconstruction) 

mc8 on mc8.household_number = mc.household_number AND mc8.slum_id = mc.slum_id

/*Extracting longitudes and latitudes from shape vectors*/

LEFT JOIN(SELECT housenumber, object_id as slum_id,
ST_X(ST_Transform(ST_SetSRID(ST_AsText(ST_Centroid(shape)), 4326), 4326)) as "longitude",
ST_Y(ST_Transform(ST_SetSRID(ST_AsText(ST_Centroid(shape)), 4326), 4326)) as "latitude",
ST_AsText(ST_Centroid(shape)) as "coordinates" 
FROM component_component WHERE metadata_id = 1 and content_type_id = 12) cc on cc.housenumber = mc.household_number::varchar AND cc.slum_id = mc.slum_id

LEFT JOIN(SELECT id, electoral_ward_id, name FROM master_slum) s on s.id = mc.slum_id

LEFT JOIN(SELECT id, administrative_ward_id FROM master_electoralward) me on me.id = s.electoral_ward_id

LEFT JOIN(SELECT id, city_id FROM master_administrativeward) ma on ma.id = me.administrative_ward_id

LEFT JOIN(SELECT id, name_id FROM master_city) mcc on mcc.id = ma.city_id

LEFT JOIN(SELECT id, city_name FROM master_cityreference) c on c.id = mcc.name_id

LEFT JOIN vw_sponsor_details sp ON sp.household_number::INT = mc.household_number::INT AND sp.slum_id::INT = mc.slum_id::INT		;

		  
