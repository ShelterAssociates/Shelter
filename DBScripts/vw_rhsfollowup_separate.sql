CREATE VIEW vw_rhsfollowup_separate
as
SELECT * FROM vw_rhsfollowup WHERE flag_followup_in_rhs = 'false'
