/* 

Sponsor Details View 

*/
DROP VIEW vw_rhs_toilet;
DROP VIEW vw_rhsfollowup_toilet;
DROP VIEW vw_rhsdata;
DROP VIEW vw_toiletconstruction;
DROP VIEW vw_sponsor_details;

CREATE VIEW vw_sponsor_details as
SELECT 
/* Converting array of households into one row per household */
    CAST(regexp_split_to_table(regexp_replace(regexp_replace(sd.household_code,'\[',''), '\]',''),E'["," ]+') AS INTEGER) AS household_number, 
	sd.slum_id,
	sd.sponsor_id,
	sd.sponsor_project_id,
	sd1.organization_name as sponsor_name,
	sd2.name as sponsor_project_name,
	s.name as Slum_Name,
	c.city_name

FROM sponsor_sponsorprojectdetails as sd, sponsor_sponsorproject as sd2, sponsor_sponsor as sd1, master_slum as s, master_city as mcc, master_cityreference as c, master_electoralward as me,
master_administrativeward as ma

WHERE sd1.id = sd.sponsor_id AND sd2.id = sd.sponsor_project_id AND sd.slum_id = s.id AND s.electoral_ward_id= me.id AND me.administrative_ward_id=ma.id AND mcc.id = ma.city_id AND c.id = mcc.name_id

