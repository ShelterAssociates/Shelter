-- Metabase view: one row per subject registration in the survey core store
-- (Household, Structure, Detailed Socio Economic Survey, members, ...).
-- Apply with: psql -f DBScripts/vw_survey_households.sql  (order: households,
-- encounters, answers). Uses CREATE OR REPLACE so it can be re-applied.
-- Filter NOT is_voided for live data; `version` separates re-survey rounds.

CREATE OR REPLACE VIEW vw_survey_households AS
SELECT
    r.id                                   AS record_id,
    r.provider,
    r.external_id                          AS subject_uuid,
    r.subject_type,
    r.version,
    r.household_number,
    r.household_id,
    r.slum_id,
    COALESCE(s.name, r.slum_name)          AS slum_name,
    r.city_id,
    cr.city_name,
    r.form_name,
    r.is_voided,
    (r.record_datetime AT TIME ZONE 'Asia/Kolkata')::date   AS registration_date,
    r.record_datetime                      AS registration_datetime,
    r.created_at,
    r.last_modified_at,
    r.synced_on
FROM survey_record r
LEFT JOIN master_slum s            ON s.id = r.slum_id
LEFT JOIN master_city c            ON c.id = r.city_id
LEFT JOIN master_cityreference cr  ON cr.id = c.name_id
WHERE r.kind = 'subject';
