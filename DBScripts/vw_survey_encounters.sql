-- Metabase view: one row per enrolment / encounter / program encounter in the
-- survey core store, with the household it belongs to.
-- is_filled = a done visit (not cancelled, has its own date). Scheduled-only
-- visits are never stored. Filter NOT is_voided for live data.

CREATE OR REPLACE VIEW vw_survey_encounters AS
SELECT
    r.id                                   AS record_id,
    r.provider,
    r.external_id                          AS record_uuid,
    r.kind,
    r.subject_external_id                  AS subject_uuid,
    r.subject_type,
    r.program,
    r.encounter_type,
    r.form_name,
    r.version,
    r.household_number,
    r.household_id,
    r.slum_id,
    COALESCE(s.name, r.slum_name)          AS slum_name,
    r.city_id,
    cr.city_name,
    (r.cancel_datetime IS NULL AND r.record_datetime IS NOT NULL) AS is_filled,
    r.is_voided,
    (r.record_datetime AT TIME ZONE 'Asia/Kolkata')::date   AS record_date,
    r.record_datetime,
    r.earliest_scheduled,
    r.max_scheduled,
    r.cancel_datetime,
    r.exit_datetime,
    r.created_at,
    r.last_modified_at,
    r.synced_on
FROM survey_record r
LEFT JOIN master_slum s            ON s.id = r.slum_id
LEFT JOIN master_city c            ON c.id = r.city_id
LEFT JOIN master_cityreference cr  ON cr.id = c.name_id
WHERE r.kind <> 'subject';
