
/*Toilet Construction*/
DROP VIEW IF EXISTS vw_rhs_toilet;
DROP VIEW IF EXISTS vw_rhsfollowup_toilet;
DROP VIEW IF EXISTS vw_toiletconstruction;

CREATE VIEW vw_toiletconstruction as 
 SELECT mc.household_number,
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
    mc.use_of_toilet,
    mc.toilet_connected_to,
    mc.factsheet_done,
        CASE
            WHEN mc.status::text = '1'::text THEN 'Agreement Done'::text
            WHEN mc.status::text = '2'::text THEN 'Agreement Cancelled'::text
            WHEN mc.status::text = '3'::text THEN 'Material Not Given'::text
            WHEN mc.status::text = '4'::text THEN 'Construction Not Started'::text
            WHEN mc.status::text = '5'::text THEN 'Under Construction'::text
            WHEN mc.status::text = '6'::text THEN 'Completed'::text
            WHEN mc.status::text = '7'::text THEN 'Written Off'::text
            ELSE NULL::text
        END AS status,
    mc.comment,
    mc.slum_id,
    s.name AS slum_name,
    c.city_name,
    sp.name,
    sp.organization_name,
    household.id,
    COALESCE((household.ff_data::json ->> 'group_im2th52/Total_family_members'::text)::integer, 0) AS family_members_count,
    COALESCE((household.ff_data::json ->> 'group_im2th52/Number_of_Male_members'::text)::integer, 0) AS male_members_count,
    COALESCE((household.ff_data::json ->> 'group_im2th52/Number_of_Female_members'::text)::integer, 0) AS female_members_count,
    COALESCE((household.ff_data::json ->> 'group_im2th52/Number_of_Children_under_5_years_of_age'::text)::integer, 0) AS count_of_children_under_5,
    COALESCE((household.ff_data::json ->> 'group_im2th52/Number_of_members_over_60_years_of_age'::text)::integer, 0) AS count_of_members_over_60,
    COALESCE((household.ff_data::json ->> 'group_im2th52/Number_of_Girl_children_between_0_18_yrs'::text)::integer, 0) AS count_of_girls_under_18,
    household.ff_data::json ->> 'group_ne3ao98/Where_the_individual_ilet_is_connected_to'::text AS ff_individual_toilet_connected_to,
    household.ff_data::json ->> 'group_ne3ao98/Who_has_built_your_toilet'::text AS toilet_built_by,
    household.ff_data::json ->> 'group_ne3ao98/Have_you_upgraded_yo_ng_individual_toilet'::text AS individual_toilet_upgraded,
    household.ff_data::json ->> 'group_ne3ao98/Cost_of_upgradation_in_Rs'::text AS cost_of_upgradation,
    household.ff_data::json ->> 'group_ne3ao98/Use_of_toilet'::text AS use_of_toilet_status,
        CASE
            WHEN date_part('month'::text, mc.phase_one_material_date) >= 4::double precision THEN ("right"(date_part('year'::text, mc.phase_one_material_date)::text, 2) || '-'::text) || "right"((date_part('year'::text, mc.phase_one_material_date) + 1::double precision)::text, 2)
            ELSE ("right"((date_part('year'::text, mc.phase_one_material_date) - 1::double precision)::text, 2) || '-'::text) || "right"(date_part('year'::text, mc.phase_one_material_date)::text, 2)
        END AS financial_year
   FROM mastersheet_toiletconstruction mc
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
            mastersheet_toiletconstruction.phase_one_material_date - mastersheet_toiletconstruction.agreement_date AS days_between_agreement_phase1
           FROM mastersheet_toiletconstruction
          WHERE mastersheet_toiletconstruction.status::text = '6'::text AND mastersheet_toiletconstruction.agreement_date IS NOT NULL AND mastersheet_toiletconstruction.phase_one_material_date IS NOT NULL) mc1 ON mc1.household_number::text = mc.household_number::text AND mc1.slum_id = mc.slum_id
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
            mastersheet_toiletconstruction.phase_two_material_date - mastersheet_toiletconstruction.phase_one_material_date AS days_between_phase1_phase2
           FROM mastersheet_toiletconstruction
          WHERE mastersheet_toiletconstruction.status::text = '6'::text AND mastersheet_toiletconstruction.phase_one_material_date IS NOT NULL AND mastersheet_toiletconstruction.phase_two_material_date IS NOT NULL) mc2 ON mc2.household_number::text = mc.household_number::text AND mc2.slum_id = mc.slum_id
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
            mastersheet_toiletconstruction.phase_three_material_date - mastersheet_toiletconstruction.phase_two_material_date AS days_between_phase2_phase3
           FROM mastersheet_toiletconstruction
          WHERE mastersheet_toiletconstruction.status::text = '6'::text AND mastersheet_toiletconstruction.phase_two_material_date IS NOT NULL AND mastersheet_toiletconstruction.phase_three_material_date IS NOT NULL) mc3 ON mc3.household_number::text = mc.household_number::text AND mc3.slum_id = mc.slum_id
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
            mastersheet_toiletconstruction.completion_date - mastersheet_toiletconstruction.agreement_date AS days_between_agreement_completed
           FROM mastersheet_toiletconstruction
          WHERE mastersheet_toiletconstruction.status::text = '6'::text AND mastersheet_toiletconstruction.agreement_date IS NOT NULL AND mastersheet_toiletconstruction.completion_date IS NOT NULL) mc4 ON mc4.household_number::text = mc.household_number::text AND mc4.slum_id = mc.slum_id
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
            mastersheet_toiletconstruction.completion_date - mastersheet_toiletconstruction.phase_one_material_date AS days_between_phase1_completed
           FROM mastersheet_toiletconstruction
          WHERE mastersheet_toiletconstruction.status::text = '6'::text AND mastersheet_toiletconstruction.agreement_date IS NOT NULL AND mastersheet_toiletconstruction.completion_date IS NOT NULL) mc10 ON mc10.household_number::text = mc.household_number::text AND mc10.slum_id = mc.slum_id
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
                CASE
                    WHEN mastersheet_toiletconstruction.agreement_date IS NOT NULL AND (mastersheet_toiletconstruction.phase_one_material_date IS NULL OR (mastersheet_toiletconstruction.phase_one_material_date - mastersheet_toiletconstruction.agreement_date) > 8) THEN 1
                    ELSE 0
                END AS phase1_delayed
           FROM mastersheet_toiletconstruction) mc5 ON mc5.household_number::text = mc.household_number::text AND mc5.slum_id = mc.slum_id
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
                CASE
                    WHEN mastersheet_toiletconstruction.phase_one_material_date IS NOT NULL AND (mastersheet_toiletconstruction.phase_two_material_date IS NULL OR (mastersheet_toiletconstruction.phase_two_material_date - mastersheet_toiletconstruction.phase_one_material_date) > 8) THEN 1
                    ELSE 0
                END AS phase2_delayed
           FROM mastersheet_toiletconstruction) mc6 ON mc6.household_number::text = mc.household_number::text AND mc6.slum_id = mc.slum_id
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
                CASE
                    WHEN mastersheet_toiletconstruction.phase_two_material_date IS NOT NULL AND (mastersheet_toiletconstruction.phase_three_material_date IS NULL OR (mastersheet_toiletconstruction.phase_three_material_date - mastersheet_toiletconstruction.phase_two_material_date) > 8) THEN 1
                    ELSE 0
                END AS phase3_delayed
           FROM mastersheet_toiletconstruction) mc7 ON mc7.household_number::text = mc.household_number::text AND mc7.slum_id = mc.slum_id
     LEFT JOIN ( SELECT mastersheet_toiletconstruction.household_number,
            mastersheet_toiletconstruction.slum_id,
                CASE
                    WHEN mastersheet_toiletconstruction.phase_three_material_date IS NOT NULL AND (mastersheet_toiletconstruction.completion_date IS NULL OR (mastersheet_toiletconstruction.completion_date - mastersheet_toiletconstruction.phase_three_material_date) > 8) THEN 1
                    ELSE 0
                END AS completion_delayed
           FROM mastersheet_toiletconstruction) mc8 ON mc8.household_number::text = mc.household_number::text AND mc8.slum_id = mc.slum_id
     LEFT JOIN ( SELECT master_slum.id,
            master_slum.electoral_ward_id,
            master_slum.name
           FROM master_slum) s ON s.id = mc.slum_id
     LEFT JOIN ( SELECT master_electoralward.id,
            master_electoralward.administrative_ward_id
           FROM master_electoralward) me ON me.id = s.electoral_ward_id
     LEFT JOIN ( SELECT master_administrativeward.id,
            master_administrativeward.city_id
           FROM master_administrativeward) ma ON ma.id = me.administrative_ward_id
     LEFT JOIN ( SELECT master_city.id,
            master_city.name_id
           FROM master_city) mcc ON mcc.id = ma.city_id
     LEFT JOIN ( SELECT master_cityreference.id,
            master_cityreference.city_name
           FROM master_cityreference) c ON c.id = mcc.name_id
     LEFT JOIN vw_sponsor_details sp ON sp.household_number = mc.household_number::text AND sp.slum_id = mc.slum_id
     LEFT JOIN graphs_householddata household ON household.household_number::text = mc.household_number::text AND household.slum_id = mc.slum_id;