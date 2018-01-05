
        $(document).ready(function() {
            $('#example').DataTable( {
            "columnDefs": [ { "defaultContent": "-", "targets": "_all" } , {"footer":true}],
            "ajax" :  {url:"http://127.0.0.1:8000/mastersheet/list/show/", dataSrc:"", contentType : "application/json" },
            "columns": [
                            {"data": "group_ce0hf58/date_of_rhs", "title": "Date of RHS"},
                            {"data": "group_ce0hf58/house_no" , "title": "House Number"},
                            {"data": "group_ye18c77/group_ud4em45/what_is_the_full_name_of_the_family_head_", "title":"Full name of the family head"},
                            {"data": "group_ye18c77/group_yw8pj39/number_of_family_members", "title": "Number of family members"},
                            {"data": "group_ye18c77/group_ud4em45/mobile_number", "title":"Mobile Number"},
                            {"data": "group_ye18c77/group_ud4em45/adhar_card_number", "title": "Aadhar card number"},
                            {"data": "group_ye18c77/group_yw8pj39/what_is_the_ownership_status_of_the_house", "title":"Ownership status of the house"},
                            {"data": "group_ye18c77/group_yw8pj39/house_area_in_sq_ft", "title": "House area in sq ft"},
                            {"data": "group_ce0hf58/Type_of_structure_occupancy", "title": "Type of structure occupancy"},
                            {"data": "group_ye18c77/group_yw8pj39/what_is_the_structure_of_the_house", "title":"Structure of the house"},
                            {"data": "group_ye18c77/group_yw8pj39/when_did_you_receive_the_first_installment_date","title":"Date of first installment"},
                            {"data": "group_ye18c77/group_yw8pj39/when_did_you_receive_the_second_installment_date", "title":"Date of second installment"},
                            {"data": "group_ce0hf58/name_of_surveyor_who_collected_rhs_data","title":"Name of the surveyor"},
                            {"data": "group_ye18c77/group_yw8pj39/Do_you_have_a_girl_child_under", "title":"Do you have a girl children under 18 yearsof age"},
                            {"data": "group_ye18c77/group_yw8pj39/facility_of_waste_collection", "title": "Facility of waste collection"},
                            {"data": "group_ye18c77/group_yw8pj39/does_any_member_of_your_family_go_for_open_defecation_", "title": "Does any member of the family goes for open defecation?"},
                            {"data": "group_ye18c77/group_yw8pj39/Current_place_of_defecation_toilet", "title": "Current place of defecation"},
                            {"data": "group_ye18c77/group_yw8pj39/type_of_water_connection", "title": "Type of water connection"},
                            {"data": "group_ye18c77/group_yw8pj39/Does_any_family_members_has_co", "title": "Does any family member has construction skills?"}
                       ]


 });
        } );
