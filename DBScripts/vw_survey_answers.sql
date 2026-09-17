-- Metabase view: one row per answer in the survey core store, joined to its
-- record and to the concept dictionary (standard key + editable SA text).
-- question_key / answer_key are the stable text keys shared by every survey
-- tool; question_text / answer_text are the SA texts edited in Django admin
-- (Survey > Concepts). Filter NOT is_voided for live data.

CREATE OR REPLACE VIEW vw_survey_answers AS
SELECT
    a.id                                   AS answer_id,
    r.id                                   AS record_id,
    r.provider,
    r.external_id                          AS record_uuid,
    r.kind,
    r.subject_external_id                  AS subject_uuid,
    r.subject_type,
    r.program,
    r.encounter_type,
    r.version,
    r.household_number,
    r.household_id,
    r.slum_id,
    COALESCE(s.name, r.slum_name)          AS slum_name,
    r.is_voided,
    (r.cancel_datetime IS NULL AND r.record_datetime IS NOT NULL) AS is_filled,
    (r.record_datetime AT TIME ZONE 'Asia/Kolkata')::date   AS record_date,
    q.key                                  AS question_key,
    q.name                                 AS question_name,
    q.sa_text                              AS question_text,
    q.data_type                            AS question_type,
    g.key                                  AS group_key,
    g.sa_text                              AS group_text,
    a.repeat_index,
    a.position,
    ans.key                                AS answer_key,
    ans.sa_text                            AS answer_text,
    a.value_text,
    a.value_number,
    a.value_date,
    (a.value_date AT TIME ZONE 'Asia/Kolkata')::date AS value_day
FROM survey_answer a
JOIN survey_record r          ON r.id = a.record_id
JOIN survey_concept q         ON q.id = a.question_id
LEFT JOIN survey_concept g    ON g.id = a.group_id
LEFT JOIN survey_concept ans  ON ans.id = a.answer_id
LEFT JOIN master_slum s       ON s.id = r.slum_id;
