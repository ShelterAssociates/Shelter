/* 

Sponsor Details View 

*/
DROP VIEW IF EXISTS vw_rhs_toilet;
DROP VIEW IF EXISTS vw_rhsfollowup_toilet;
DROP VIEW IF EXISTS vw_toiletconstruction;
DROP VIEW IF EXISTS vw_sponsor_details;

CREATE VIEW vw_sponsor_details as
WITH households AS (
    SELECT 
        TRIM(BOTH FROM REPLACE(
            regexp_split_to_table(
                regexp_replace(regexp_replace(sd.household_code, '\[', ''), '\]', ''), 
                '[," ]+'
            ), E'\n', ''
        )) AS household_number,
        sd.slum_id,
        sd.sponsor_id,
        sd.sponsor_project_id
    FROM sponsor_sponsorprojectdetails sd
)
SELECT 
    TRIM(BOTH FROM households.household_number) AS household_number,
    households.slum_id,
    households.sponsor_id,
    households.sponsor_project_id,
    sp.name,
    s.organization_name
FROM households
JOIN sponsor_sponsorproject sp ON sp.id = households.sponsor_project_id
JOIN sponsor_sponsor s ON s.id = households.sponsor_id
WHERE 
    households.household_number IS NOT NULL 
    AND households.household_number <> '' 
    AND NOT households.household_number LIKE 'Invalid household_code%' 
    AND s.organization_name <> 'SBM Toilets';
