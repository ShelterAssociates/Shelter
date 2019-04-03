/* 

Community Mobilization View 

*/
DROP VIEW vw_communitymobilization;

CREATE VIEW vw_communitymobilization as
SELECT 
/* Converting array of households into one row per household */
    CAST(regexp_split_to_table(regexp_replace(regexp_replace(mc.household_number,'\["',''), '"\]',''),E'["," ]+') AS INTEGER) AS household_number, 
	mc.activity_date::timestamp,
	att.name as Activity_Name,
	mc.slum_id,
/* Grouping male, female and both gender based activities */
	CASE mc.activity_type_id 
		WHEN 2 THEN 'Activities with Females'
		WHEN 4 THEN 'Activities with Females'
		WHEN 9 THEN 'Activities with Females'
		WHEN 11 THEN 'Activities with Females'
		WHEN 3 THEN 'Activities with Males'
		WHEN 5 THEN 'Activities with Males'
		WHEN 8 THEN 'Activities with Males'
		WHEN 10 THEN 'Activities with Males'
		WHEN 1 THEN 'Activities with Both'
		WHEN 7 THEN 'Activities with Both'
		WHEN 12 THEN 'Activities with Both'
		WHEN 13 THEN 'Activities with Both'
		WHEN 14 THEN 'Activities with Both'
		WHEN 15 THEN 'Activities with Both'
		WHEN 16 THEN 'Activities with Both'
		WHEN 17 THEN 'Activities with Both'
		WHEN 18 THEN 'Activities with Both'
		WHEN 19 THEN 'Activities with Both'
		WHEN 20 THEN 'Activities with Both'
		WHEN 21 THEN 'Activities with Both'
		WHEN 22 THEN 'Activities with Both'
		ELSE NULL END AS activity_gender_type,
    s.name as Slum_Name,
    c.city_name

FROM mastersheet_communitymobilization as mc, mastersheet_activitytype as att, master_slum as s, master_city as mcc, master_cityreference as c, master_electoralward as me,
master_administrativeward as ma

WHERE mc.activity_type_id = att.id AND mc.slum_id = s.id AND s.electoral_ward_id= me.id AND me.administrative_ward_id=ma.id AND mcc.id = ma.city_id AND c.id = mcc.name_id

