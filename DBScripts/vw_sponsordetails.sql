/* 

Sponsor Details View 

*/
DROP VIEW IF EXISTS vw_rhs_toilet;
DROP VIEW IF EXISTS vw_rhsfollowup_toilet;
DROP VIEW IF EXISTS vw_toiletconstruction;
DROP VIEW IF EXISTS vw_sponsor_details;

CREATE VIEW vw_sponsor_details as
 WITH households AS (
         SELECT regexp_split_to_table(regexp_replace(regexp_replace(sd.household_code, '\['::text, ''::text), '\]'::text, ''::text), '[," ]+'::text) AS household_number,
            sd.slum_id,
            sd.sponsor_id,
            sd.sponsor_project_id
           FROM sponsor_sponsorprojectdetails sd
        )
 SELECT households.household_number,
    households.slum_id,
    households.sponsor_id,
    households.sponsor_project_id,
    sp.name,
    s.organization_name
   FROM households
     JOIN sponsor_sponsorproject sp ON sp.id = households.sponsor_project_id
     JOIN sponsor_sponsor s ON s.id = households.sponsor_id
  WHERE NOT households.household_number ~~ 'Invalid household_code%'::text AND NULLIF(households.household_number, ''::text) IS NOT NULL AND s.organization_name::text <> 'SBM Toilets'::text;
