var report_short_datatable = null;
var columns_defs;
var table = null;
var divider = 1000 * 60 * 60 * 24;
var window = 8 * 1000 * 60 * 60 * 24;
var current_slum;
var city_code;
var btn_default = [];
var boxes = [];

var today = Date.now();
var daily_reporting_columns = [];

$(document).ready(function () {

    $("#add_table_btn").hide();

    var csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;

    $.ajax({
        url: "/mastersheet/columns/",
        type: "GET",
        dataType: "json",
        data: "",
        contentType: "application/json",
        success: function (data, type, row, meta) {
            columns_defs = data;

            // Adding hyperlinks to RHS data
            var tmp_RHS = columns_defs['buttons']['RHS'];
            for (i = 0; i < tmp_RHS.length; i++) {
                columns_defs['data'][tmp_RHS[i]]['render'] = function (data, type, row, meta) {
                    if (typeof data != 'undefined') {
                        url_RHS = row['rhs_url']
                        if (type === 'display') {
                            data = '<a href = "#" onclick="window.open(\'' + url_RHS + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                        }
                        return data;
                    }
                }
            }
            var tmp_FF = columns_defs['buttons']['Family factsheet'];
            for (i = 0; i < tmp_FF.length; i++) {
                columns_defs['data'][tmp_FF[i]]['render'] = function (data, type, row, meta) {
                    if (typeof data != 'undefined') {
                        if (typeof row['ff_url'] != 'undefined') {
                            url_FF = row['ff_url']
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_FF + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                        }
                        return data;
                    }
                }
            }

            // Adding family factsheet photo download URLs
            var tmp_download_TF = columns_defs['buttons']['Family factsheet'];
            var start_of_FF = columns_defs['buttons']['Family factsheet'][0];
            for (i = 0; i < tmp_download_TF.length; i++) {
                //Toilet photo
                columns_defs['data'][start_of_FF + 6]['render'] = function (data, type, row, meta) {
                    if (typeof data != 'undefined') {
                        url_download_TF = row['toilet_photo_url'];
                        if (type === 'display') {
                            data = '<a target="_blank" href = " ' + url_download_TF + '" >Download Photo</a>';
                        }
                        return data;
                    }
                }

                //Family photo
                columns_defs['data'][start_of_FF + 5]['render'] = function (data, type, row, meta) {
                    if (typeof data != 'undefined') {
                        url_download_FF = row['family_photo_url'];
                        if (type === 'display') {
                            data = '<a target="_blank" href = "' + url_download_FF + '" >Download Photo</a>';
                        }
                        return data;
                    }
                }
            }


            // Adding hyperlinks to community mobilization data
            var tmp_DR = columns_defs['buttons']['Community Mobilization'];
            for (i = 0; i < tmp_DR.length; i++) {
                columns_defs['data'][tmp_DR[i]]['render'] = function (data, type, row, meta) {
                    if (typeof data != 'undefined') {
                        url_daily_reporting = String("/accounts/mastersheet/communitymobilization/") + row[columns_defs['data'][meta.col]['title'] + "_id"] + String("/");
                        if (data.length > 11) {
                            url_daily_reporting = String("/accounts/mastersheet/communitymobilizationactivityattendance/") + row[columns_defs['data'][meta.col]['title'] + "_id"] + String("/");
                        }
                        if (type === 'display') {
                            data = '<a href = "#" onclick="window.open(\'' + url_daily_reporting + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                        }
                        return data;
                    }
                }
            }

            // Adding hyperlinks to accounts data
            var tmp_ACC = columns_defs['buttons']['Accounts'];
            for (i = 0; i < tmp_ACC.length; i++) {
                columns_defs['data'][tmp_ACC[i]]['render'] = function (data, type, row, meta) {
                    if (typeof data != 'undefined') {
                        url_accounts = String("/accounts/mastersheet/invoice/") + row[columns_defs['data'][meta.col]['title'] + "_id"] + String("/");
                        if (type === 'display') {
                            data = '<a href = "#" onclick="window.open(\'' + url_accounts + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";

                        }
                        return data;
                    }
                }
            }

            // Adding hyperlinks to SBM data
            var tmp_SBM = columns_defs['buttons']['SBM'];
            for (i = 0; i < tmp_SBM.length; i++) {
                columns_defs['data'][tmp_SBM[i]]['render'] = function (data, type, row, meta) {
                    if (typeof data != 'undefined') {
                        url_SBM = String("/accounts/mastersheet/sbmupload/") + row['sbm_id_' + String(row.Household_number)] + String("/");
                        if (type === 'display') {
                            data = '<a href = "#" onclick="window.open(\'' + url_SBM + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                        }
                        return data;
                    }
                }
                // Adding hyperlinks to open Household data
                columns_defs['data'][columns_defs['buttons']['RHS'][0] - 1]['render'] = function (data, type, row, meta) {
                    if (typeof data != 'undefined') {
                        if (typeof row['Household_id'] != 'undefined') {
                            url_SBM = String("/accounts/graphs/householddata/") + row['Household_id'] + String("/");
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_SBM + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                        }
                        if (row['no_rhs_flag'] != '') {
                            data = "<p class = 'highlight_p' style = 'background-color : " + row['no_rhs_flag'] + ";'>" + data + "</p>";
                        }
                        return data;
                    }
                }
            }


            // Adding hyperlinks to Toilet Construction data
            var tmp_TC = columns_defs['buttons']['Construction status'];
            for (i = 0; i < tmp_TC.length; i++) {
                if (columns_defs['data'][tmp_TC[i]]['data'] != "Funder") {
                    columns_defs['data'][tmp_TC[i]]['render'] = function (data, type, row, meta) {
                        if (typeof data != 'undefined') {
                            url_TC = String("/accounts/mastersheet/toiletconstruction/") + row['tc_id_' + String(row.Household_number)] + String("/");
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_TC + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            return data;
                        }
                    }
                }
                if (columns_defs['data'][tmp_TC[i]]['data'] == "status") {
                    columns_defs['data'][tmp_TC[i]]['render'] = function (data, type, row, meta) {
                        if (typeof data != 'undefined') {
                            url_TC = String("/accounts/mastersheet/toiletconstruction/") + row['tc_id_' + String(row.Household_number)] + String("/");
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_TC + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            if (row['delay_flag'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['delay_flag'] + ";'>" + data + "</p>";
                            }
                            return data;
                        }
                    }
                }
                if (columns_defs['data'][tmp_TC[i]]['data'] == "agreement_date_str") {
                    columns_defs['data'][tmp_TC[i]]['render'] = function (data, type, row, meta) {
                        if (typeof data != 'undefined') {
                            url_TC = String("/accounts/mastersheet/toiletconstruction/") + row['tc_id_' + String(row.Household_number)] + String("/");
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_TC + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            if (row['a_missing'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['a_missing'] + ";'>" + data + "</p>";
                            }
                            if (row['a_amb'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['a_amb'] + ";'>" + data + "</p>";
                            }
                            return data;
                        }
                    }
                }
                if (columns_defs['data'][tmp_TC[i]]['data'] == "phase_one_material_date_str") {
                    columns_defs['data'][tmp_TC[i]]['render'] = function (data, type, row, meta) {
                        if (typeof data != 'undefined') {
                            url_TC = String("/accounts/mastersheet/toiletconstruction/") + row['tc_id_' + String(row.Household_number)] + String("/");
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_TC + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            if (row['p1_missing'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['p1_missing'] + ";'>" + data + "</p>";
                            }
                            if (row['p1_amb'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['p1_amb'] + ";'>" + data + "</p>";
                            }
                            return data;
                        }
                    }
                }
                if (columns_defs['data'][tmp_TC[i]]['data'] == "phase_two_material_date_str") {
                    columns_defs['data'][tmp_TC[i]]['render'] = function (data, type, row, meta) {
                        if (typeof data != 'undefined') {
                            url_TC = String("/accounts/mastersheet/toiletconstruction/") + row['tc_id_' + String(row.Household_number)] + String("/");
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_TC + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            if (row['p2_missing'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['p2_missing'] + ";'>" + data + "</p>";
                            }
                            if (row['p2_amb'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['p2_amb'] + ";'>" + data + "</p>";
                            }
                            return data;
                        }
                    }
                }
                if (columns_defs['data'][tmp_TC[i]]['data'] == "phase_three_material_date_str") {
                    columns_defs['data'][tmp_TC[i]]['render'] = function (data, type, row, meta) {
                        if (typeof data != 'undefined') {
                            url_TC = String("/accounts/mastersheet/toiletconstruction/") + row['tc_id_' + String(row.Household_number)] + String("/");
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_TC + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            if (row['p3_missing'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['p3_missing'] + ";'>" + data + "</p>";
                            }
                            if (row['p3_amb'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['p3_amb'] + ";'>" + data + "</p>";
                            }
                            return data;
                        }
                    }
                }
                if (columns_defs['data'][tmp_TC[i]]['data'] == "completion_date_str") {
                    columns_defs['data'][tmp_TC[i]]['render'] = function (data, type, row, meta) {
                        if (typeof data != 'undefined') {
                            url_TC = String("/accounts/mastersheet/toiletconstruction/") + row['tc_id_' + String(row.Household_number)] + String("/");
                            if (type === 'display') {
                                data = '<a href = "#" onclick="window.open(\'' + url_TC + '\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            if (row['c_amb'] != '') {
                                data = "<p class = 'highlight_p' style = 'background-color : " + row['c_amb'] + ";'>" + data + "</p>";
                            }
                            return data;
                        }
                    }
                }
                var length_table = columns_defs['buttons']['Accounts'][columns_defs['buttons']['Accounts'].length - 1] + 1;
                btn_default = [
                    {
                        extend: 'excel',
                        text: 'Excel(Flagged records)',
                        exportOptions: {
                            rows: '.highlight_p',
                            columns: [...Array(length_table).keys()].slice(columns_defs['buttons']['RHS'][0] - 2, length_table)
                        }
                    },
                    {
                        extend: 'excel',
                        text: 'Excel(ALL)',
                        exportOptions: {
                            columns: [...Array(length_table).keys()].slice(columns_defs['buttons']['RHS'][0] - 2, length_table)
                        }
                    }
                ];
                if ($("#export_mastersheet").val() == "False") {
                    btn_default = [];
                }
            }
        }
    });
    $("#buttons").on("click", "button", function () {

        $(this).toggleClass("active");
        flag = false;
        if ($(this).hasClass("active")) {
            flag = true;
        }
        section = $(this).attr('value');
        col = columns_defs['buttons'][section];
        table.columns(col).visible(flag);
        add_search_box();
    });
    $("#upload_file_1").on("click", function () {

        $(".overlay").show();
        var input = $("#upload_file")[0];
        var formData = new FormData(input);
        formData.append('slum_code', $("#slum_form")[0][1].value);
        if (typeof input[1].files[0] == 'undefined') {
            alert("No file selected. Please select a file.");
        }
        else {
            var fname = input[1].files[0].name;
            var re = /(\.xls|\.xlsx)$/i;
            if (!re.exec(fname)) {
                alert("File extension not supported!");
            }
            else {
                $.ajax({
                    type: "post",
                    url: "/mastersheet/files/",
                    data: formData,
                    dataType: 'json',
                    contentType: false,
                    processData: false,
                    success: function (response) {
                        var total_updates = 0;
                        var total_new = 0;
                        jQuery.each(response, function (index, value) {
                            try {
                                if (index.indexOf("updated") != -1) {
                                    total_updates = total_updates + value.length;
                                }
                            }
                            catch (error) {
                                total_updates = 0;
                            }
                            try {
                                if (index.indexOf("newly") != -1) {
                                    total_new = total_new + value.length;
                                }
                            }
                            catch (error) {
                                total_new = 0;
                            }
                            try {
                                if (index.indexOf("error") != -1) {
                                    var error_log = document.createElement('div');
                                    error_log.innerHTML = "<p>" + index + ": " + String(value) + "[ total:" + value.length + " ]</p>";
                                    $("#error_log").append(error_log);
                                    $('#error_log').addClass('error_display');
                                    $('#error_log').addClass('alert alert-danger');
                                }
                            }
                            catch (error) {
                            }

                        });
                        var success_log = document.createElement('div');
                        success_log.innerHTML = "<p>Number of records in the uploaded sheet: " + response.total_records + "<br>Total records updated: " + total_updates + "<br>Number of new records added: " + total_new + "</p>";
                        $("#success_log").append(success_log);
                        $('#success_log').addClass('alert alert-success');
                        $(".overlay").hide();
                    },
                    // complete:function(){
                    //     console.log("We are in complete");
                    //     $(".overlay").hide();
                    // },
                    error: function (response) {
                        $(".overlay").hide();
                        if (response.responseText != "") {
                            alert(response.responseText);
                        }
                    }
                });
            }
        }
    });

    // Clearing modal after it is closed
    $("#btnUpload").on("click", function () {
        var slum_code = $("#slum_form")[0][1].value;
        if (slum_code.length == 0) {
            alert("Please select a slum");
        }
        else {
            $("#myModal").modal('show');
        }
        $('#myModal').on('hidden.bs.modal', function () {
            $(this).find("#error_log").html("");
            $(this).find("#error_log").remove();
            $(this).find("#success_log").html("");
            $(this).find("#success_log").remove();
            $("#upload_file")[0].reset();

        });
    });

    // Handling Download Accounts Data button click event.
    $("#btnAccount").on("click", function () {
        var slum_code = $("#slum_form")[0][1].value;
        $("#accountModal").modal('show');
        $('#accountModal').on('hidden.bs.modal', function () {
            $(this).find("#error_log").html("");
            $(this).find("#error_log").remove();
            $(this).find("#success_log").html("");
            $(this).find("#success_log").remove();
            $("#accountModal_selection")[0].reset();

        });
    });
    // Handling Download GIS Data button click event.
    $("#btnFetchGisTab").on("click", function () {
        var slum_code = $("#slum_form")[0][1].value;
        $("#GISModal").modal('show');
        $('#GISModal').on('hidden.bs.modal', function () {
            $(this).find("#error_log").html("");
            $(this).find("#error_log").remove();
            $(this).find("#success_log").html("");
            $(this).find("#success_log").remove();
            $("#GISModal_selection")[0].reset();
        });
    });


    // when we submit  Account data download  tab we check if slum is selected or not.
    $("#downloadExcel").on("click", function () {
        if ($("#id_account_slumname").val() == "" && ($("#account_cityname").val() == "")) {
            alert('Either Slum or City is required')
        }
        else {
            $("#accountModal_selection").submit();
        }
    });

    // when we submit  GIS data download tab we check if slum is selected or not.
    $("#downloadGIS").on("click", function () {
        if ($("#gisdata_slumname").val() == "" && ($("#gisdata_cityname").val() == "")) {
            alert('Please select any option for slum/city !!')
        }
        else {
            $("#GISModal_selection").submit();
        }
    });

    function load_data_datatable() {
        if (table != null) {
            $("#slum_form p").find("#slum_info").html("");
            $("#slum_form p").find("#slum_info").remove();
            $(".overlay").show();
            table.ajax.reload();
        }
        else {
            $(".overlay").show();
            $("#legend1").show();
            $("#legend2").show();
            buttons = '<div class="btn-group">';
            $.each(columns_defs['buttons'], function (index, button) {
                buttons += '<button type="button" class="active btn btn-default" value="' + index + '" id="' + index.replace(/ /g, '') + '">' + index + '</button>';
            });
            buttons += '</div>';
            $("#buttons").append(buttons);
            table = $("#example").DataTable({
                //dom: 'Bfrtip',
                "processing": true,
                "sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
                "ajax": {
                    url: "/mastersheet/list/show/",
                    dataSrc: "",
                    data: function () {
                        return $("#slum_form").serialize();// , 'csrfmiddlewaretoken':csrf_token}
                        // NOTE : We could have assigned the variable itself to the 'data' attribute, instead
                        // of writing  function. That method promotes the errorneous behaviour. The code would have been
                        // unable to update the 'data' attribute on the call of 'table.ajax.reload()'. 
                    },
                    contentType: "application/json",
                    dataSrc: function (data) {
                        for (i = 0; i < data.length; i++) {
                            if (data[i] != null) {
                                data[i]['a_missing'] = '';
                                data[i]['p1_missing'] = '';
                                data[i]['p2_missing'] = '';
                                data[i]['p3_missing'] = '';
                                if (!data[i]['agreement_date_str'] && (data[i]['phase_one_material_date_str'] || data[i]['phase_two_material_date_str'] || data[i]['phase_three_material_date_str'] || data[i]['completion_date_str'])) {
                                    data[i]['a_missing'] = '#a9d2fc';
                                }
                                if (!data[i]['phase_one_material_date_str'] && (data[i]['phase_two_material_date_str'] || data[i]['phase_three_material_date_str'] || data[i]['completion_date_str'])) {
                                    data[i]['p1_missing'] = '#a9d2fc';
                                }
                                if (data[i]['phase_one_material_date_str'] != data[i]['phase_three_material_date_str']) {
                                    if (!data[i]['phase_two_material_date_str'] && (data[i]['phase_three_material_date_str'] || data[i]['completion_date_str'])) {
                                        data[i]['p2_missing'] = '#a9d2fc';
                                    }
                                    if (!data[i]['phase_three_material_date_str'] && (data[i]['completion_date_str'])) {
                                        data[i]['p3_missing'] = '#a9d2fc';
                                    }
                                    else {
                                        if (!data[i]['phase_two_material_date_str'] && (data[i]['completion_date_str'])) {
                                            data[i]['p2_missing'] = '#a9d2fc';
                                        }
                                    }
                                }
                                data[i]['a_amb'] = '';
                                data[i]['p1_amb'] = '';
                                data[i]['p2_amb'] = '';
                                data[i]['p3_amb'] = '';
                                data[i]['c_amb'] = '';
                                if (checkCorrect(data[i]['phase_one_material_date_str'], data[i]['agreement_date_str']) == false) {
                                    data[i]['a_amb'] = '#fc0707';
                                    data[i]['p1_amb'] = '#fc0707';
                                }
                                if (checkCorrect(data[i]['phase_two_material_date_str'], data[i]['phase_one_material_date_str']) == false) {
                                    data[i]['p1_amb'] = '#fc0707';
                                    data[i]['p2_amb'] = '#fc0707';
                                }
                                if (data[i]['phase_one_material_date_str'] != data[i]['phase_three_material_date_str']) {
                                    if (checkCorrect(data[i]['phase_three_material_date_str'], data[i]['phase_two_material_date_str']) == false) {
                                        data[i]['p2_amb'] = '#fc0707';
                                        data[i]['p3_amb'] = '#fc0707';
                                    }
                                    if (checkCorrect(data[i]['completion_date_str'], data[i]['phase_three_material_date_str']) == false) {
                                        data[i]['p3_amb'] = '#fc0707';
                                        data[i]['c_amb'] = '#fc0707';
                                    }
                                }
                                else {
                                    if (checkCorrect(data[i]['completion_date_str'], data[i]['phase_two_material_date_str']) == false) {
                                        data[i]['p2_amb'] = '#fc0707';
                                        data[i]['c_amb'] = '#fc0707';
                                    }
                                }
                            }
                        }
                        return data;
                    },
                    complete: function () {
                        $(".overlay").hide();
                    },
                    error: function (response) {
                        $(".overlay").hide();
                        if (response.responseText != "") {
                            alert(response.responseText);
                        }
                    }


                },

                "columnDefs": [
                    {
                        "defaultContent": "-",
                        "targets": "_all",

                    },

                    { "footer": true },

                ],

                "buttons": btn_default,

                "columns": columns_defs['data'],
                "fixedColumns": {
                    leftColumns: 1,

                },
                "scrollCollapse": true,
            });



            $(table.table().container()).on('keyup ', 'tfoot tr th input', function (index, element) {
                table.column($(this).attr('dt_index')).search(String(this.value)).draw();

            });


            $('#p1, #p2, #p3, #cd, #ad, #md, #wo, #no_rhs, #material_shift, #incorrect_COD').click(function () {
                var selected = [];
                boxes = [];
                $.each($("input[name='checkbox_filter']:checked"), function (k, v) { boxes.push($(v).attr('value')) });
                table.draw();
            });
            $.fn.dataTable.ext.search.push(
                function (settings, data, dataIndex) {
                    if (boxes.indexOf(data[9]) > -1 || ($('#incorrect_COD:checked').length == 1 && data[13] == 'incorrect_cpod') || ($('#material_shift:checked').length == 1 && data[12] == '#f9cb9f') || ($("#no_rhs:checked").length == 1 && data[11].length > 1) || ($("#wo:checked").length == 1 && data[10] == "Written-off") || ($("#md:checked").length == 1 && (data[0] != '' || data[1] != '' || data[2] != '' || data[3] != '')) || ($("#ad:checked").length == 1 && (data[4] != '' || data[5] != '' || data[6] != '' || data[7] != '' || data[8] != ''))) {
                        return true; //( $('#material_shift').length ==1 &&  )||
                    }
                    if ($(".checkmark").parent().find("input:checked").length == 0) {
                        return true;
                    }

                    return false;

                }
            );
            $('#example').on("draw.dt", function () {
                flag_dates();
            });

            //prints the data in the cell when we click it. USED FOR DEBUGGING!!
            /*$('#example').on( 'click', 'tbody td', function () {
                var data = table.cell( this ).render( 'sort' );
            } );*/


            $('#example tbody').on('click', 'tr', function () {
                $(this).toggleClass('selected');
            });
            $('#delete_selected').click(function () {


                var count = table.rows('.selected').data().length;
                if (count == 0) {
                    alert("You have not selected any record. Please select a record to delete.");
                }
                else {
                    var records = [];
                    for (i = 0; i < count; i++) {
                        records[i] = (table.rows('.selected').data()[i]['_id']);
                    }

                    if (records.length == 1) {
                        var result = confirm("Are you sure? You have selected " + records.length + " record to delete.");
                    }
                    else {
                        var result = confirm("Are you sure? You have selected " + records.length + " records to delete.");
                    }
                    if (result) {
                        $(".overlay").show();
                        $.ajax({
                            type: "post",
                            url: "/mastersheet/delete_selected/",

                            data: JSON.stringify({ "records": records, "slum": document.forms[0].slumname.value }),
                            contentType: "json",
                            success: function (data, textStatus, xhr) {
                                $(".overlay").hide();
                                if (response.response != "") {
                                    alert(response.response);
                                    $("#btnFetch").click();
                                }
                            },
                            error: function (resp) {
                                $(".overlay").hide();
                                if (resp.responseText != "") {
                                    alert(resp.responseText);
                                }
                            }

                        });
                    }
                }
            });
            var number_of_invisible_columns = columns_defs['buttons']['RHS'][0] - 1;

            $.each(columns_defs['buttons'], function (key, val) {
                html_table = $("#example");
                //html_table.find("thead>tr>th:eq(0)").addClass("trFirst");
                html_table.find("thead>tr>th:eq(" + (val[0] - number_of_invisible_columns) + ")").addClass("trFirst");
                $.each(val.slice(1, val.length - 1), function (k, v) {
                    html_table.find("thead>tr>th:eq(" + (v - number_of_invisible_columns) + ")").addClass("trMiddle");

                });
                $.each(val, function (k, v) {
                    var va = v - number_of_invisible_columns;
                    if (String(key) === "RHS") {
                        html_table.find("thead>tr>th:eq(" + va + ")").css('background-color', '#d6d0dd');//
                        //background-color: lightblue;
                        //$("#" + key).css('background-color', '#ccc0d9');

                    }
                    if (String(key) === "Follow-up") {
                        html_table.find("thead>tr>th:eq(" + va + ")").css('background-color', '#ffe0f5');//
                        //$("#" + key).css('background-color', '#ccc0d9');
                    }
                    if (String(key) === "Family factsheet") {
                        html_table.find("thead>tr>th:eq(" + va + ")").css('background-color', '#e0f6ff');//
                        //$("#" + key.replace(/ /g,'')).css('background-color', '#c4bd97');

                    }
                    if (String(key) === "SBM") {
                        html_table.find("thead>tr>th:eq(" + va + ")").css('background-color', '#fed9a6');//
                        //$("#" + key).css('background-color', '#fbd4b4');
                    }
                    if (String(key) === "Construction status") {
                        html_table.find("thead>tr>th:eq(" + va + ")").css('background-color', '#d2e2ce');//
                        //$("#" + key.replace(/ /g,'')).css('background-color', '#c4bd97');
                    }
                    if (String(key) === "Community Mobilization") {
                        html_table.find("thead>tr>th:eq(" + va + ")").css('background-color', '#e5d8bd');//
                        //$("#" + key.replace(/ /g,'')).css('background-color', '#b8cce4');
                    }
                    if (String(key) === "Accounts") {
                        html_table.find("thead>tr>th:eq(" + va + ")").css('background-color', '#ffffb3');//
                        //$("#" + key).css('background-color', '#d8d8d8');
                    }

                });
                html_table.find("thead>tr>th:eq(" + (val[val.length - 1] - number_of_invisible_columns) + ")").addClass("trLast");
            });

            $("#buttons button")[0].click();
            $("#buttons button")[1].click();
            $("#buttons button")[2].click();
            $("#add_table_btn").show();
            //For excel button alignment.
            $("div.dt-buttons>button").addClass("pull-left");
        }


    }


    // For Summery View Datatable master method.......
    function load_short_datatable() {

        btn_default = [
            {
                extend: 'excel',
                text: 'Excel',
            }
        ];

        if (report_short_datatable != null) {
            $("#slum_form p").find("#slum_info").html("");
            $("#slum_form p").find("#slum_info").remove();
            $(".overlay").show();
            report_short_datatable.ajax.reload();
        }
        else {

            $(".overlay").show();
            $("#legend1").show();
            $("#legend2").show();
            buttons = '<div class="btn-group">';
            $.each(columns_defs['buttons'], function (index, button) {
                buttons += '<button type="button" class="active btn btn-default" value="' + index + '" id="' + index.replace(/ /g, '') + '">' + index + '</button>';
            });
            buttons += '</div>';
            $("#buttons").append(buttons);
            report_short_datatable = $("#example").DataTable({
                // "sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
                dom: 'QBlfrtip',
                "searchBuilder": {
                    depthLimit: 2
                },
                "paging": true,
                "order": [[9, "desc"]],
                "ajax": {
                    url: "/mastersheet/show/showSummery/",
                    dataSrc: "",
                    data: function () {
                        return $("#slum_form").serialize();// , 'csrfmiddlewaretoken':csrf_token}
                        // NOTE : We could have assigned the variable itself to the 'data' attribute, instead
                        // of writing  function. That method promotes the errorneous behaviour. The code would have been
                        // unable to update the 'data' attribute on the call of 'table.ajax.reload()'. 
                    },
                    contentType: "application/json",
                    dataSrc: function (data) {
                        return data;
                    },
                    complete: function () {
                        $(".overlay").hide();
                    },
                    error: function (response) {
                        $(".overlay").hide();
                        if (response.responseText != "") {
                            alert(response.responseText);
                        }
                    }
                },
                "buttons": btn_default,
                "columnDefs": [{ "defaultContent": "-", "targets": "_all" }, { "footer": true }, { "targets": 0, "visible": false, "searchable": false }],
                "columns": [
                    { 'data': 'slum', 'title': 'Slum' },
                    { 'data': 'household_number', 'title': 'Household Number' },
                    { 'data': 'pluscodes', 'title': 'Plus Code' },
                    { 'data': 'occupancy_status', 'title': 'Occupancy Status' },
                    { 'data': 'name_head_of_he_household', 'title': 'Name of the head of the household' },
                    { 'data': 'current_place_of_defication', 'title': 'Current place of defecation' },
                    { 'data': 'phase_one_material_date', 'title': 'Date of Phase One Material' },
                    { 'data': 'Completion delayed', 'title': 'Completion delayed:' },
                    { 'data': 'agreement_cancelled', 'title': 'Agreement Cancelled?' },
                    { 'data': 'material_shifted', 'title': 'Material shifted (Yes/No)' },
                    { 'data': 'toilet_status', 'title': 'Final Status of toilet' },
                    { 'data': 'sponsor_project', 'title': 'Funder (Project Name)' },
                    { 'data': 'factsheet_done', 'title': 'Factsheet onfield' },
                    { 'data': 'toilet_connected_to', 'title': 'Toilet Connected Status' },
                    { 'data': 'total_moilization_acticity', 'title': 'No. of mobilisation activities attended by family' },
                    { 'data': 'invoice_entry', 'title': 'Invoice entry (Yes/No)' }
                ],

            });
            $("div.dt-buttons>button").addClass("pull-left");
            add_search_box();
            $(report_short_datatable.table().container()).on('keyup ', 'tfoot tr th input', function (index, element) {
                report_short_datatable.column($(this).attr('dt_index')).search(String(this.value)).draw();

        new $.fn.dataTable.SearchBuilder(report_short_datatable);

            });

            select_rows()
        }
    }

    function select_rows() {
        $('#example tbody').on('click', 'tr', function () {
            $(this).toggleClass('selected');
        });
    }

    // For Mastersheet View 
    $("#btnFetch").click(function () {

        if (document.forms[0].slumname.value == "") {
            alert("Please select a slum");
        }
        else {
            $.ajax({
                url: "/mastersheet/details/",
                //dataSrc:"",
                type: "GET",
                data: { 'form': $("#slum_form").serialize(), 'csrfmiddlewaretoken': csrf_token }
                // NOTE : We could have assigned the variable itself to the 'data' attribute, instead
                // of writing  function. That method promotes the errorneous behaviour. The code would have been
                // unable to update the 'data' attribute on the call of 'table.ajax.reload()'. 
                ,
                contentType: "application/json",
                success: function (data) {
                    // Displaying the electoral ward and name of the slum besides the look-up box
                    if (data != 'undefined') {
                        city_code = data["City Code"];
                        var slum_info = document.createElement('div');
                        slum_info.classList.add("display_line");
                        slum_info.setAttribute("id", "slum_info");
                        slum_info.innerHTML = "<p>" + data["Name of the slum"] + ", " + data["Electoral Ward"] + "</p>";
                        //console.log(data.responseJSON[data.responseJSON.length-1]);
                        $("#slum_form p").append(slum_info);

                    }

                },
            });
            load_data_datatable();
        }

    });

    // for Short View of mastersheet...
    $("#btnFetchShort").click(function () {
        if (document.forms[0].slumname.value == "") {
            alert("Please select a slum");
        }
        else {
            $.ajax({
                url: "/mastersheet/details/",
                //dataSrc:"",
                type: "GET",
                data: { 'form': $("#slum_form").serialize(), 'csrfmiddlewaretoken': csrf_token }
                // NOTE : We could have assigned the variable itself to the 'data' attribute, instead
                // of writing  function. That method promotes the errorneous behaviour. The code would have been
                // unable to update the 'data' attribute on the call of 'table.ajax.reload()'. 
                ,
                contentType: "application/json",
                success: function (data) {
                    // Displaying the electoral ward and name of the slum besides the look-up box
                    if (data != 'undefined') {
                        city_code = data["City Code"];
                        var slum_info = document.createElement('div');
                        slum_info.classList.add("display_line");
                        slum_info.setAttribute("id", "slum_info");
                        slum_info.innerHTML = "<p>" + data["Name of the slum"] + ", " + data["Electoral Ward"] + "</p>";
                        //console.log(data.responseJSON[data.responseJSON.length-1]);
                        $("#slum_form p").append(slum_info);

                    }

                },
            });
            load_short_datatable();
        }

    });


    function trim_space(str) {
        if (str != null) {
            return str.trim();
        }
        else {
            return str;

        }
    }
    function get_date(str) {
        if (str != null) {
            return Date.parse(trim_space(str));
        }
        else {
            return str;
        }
    }
    function checkCorrect(str1, str2) {
        if (str1 != null && str2 != null) {
            if (get_date(str1) - get_date(str2) >= 0) {
                return true;
            }
            else {
                return false;
            }

        }
        else {
            return true;
        }

    }


    function flag_dates() {
        if (table != null) {
            $("td:contains('Written-off')").parents('tr').css('background-color', '#c6c6c6');
            $.each($('.highlight_p'), function (k, v) {
                $(v).parent().attr('style', $(v).attr('style'));
            });

        }
        else {
            console.log("table is null");
        }


    }

    $("#btnSync").click(function () {
        let slum = $("#slum_form").find('input[type=text]').val();
        if (slum != "") {
            $(".overlay").show();
            $.ajax({
                type: "get",
                url: "/mastersheet/sync/slum/",
                data: { 'slumname': slum },
                contentType: "json",
                success: function (response) {
                    $(".overlay").hide();
                    if (response.msg != "") {
                        alert(response.msg);
                    }
                },
                error: function (response) {
                    $(".overlay").hide();
                    if (response.responseText != "") {
                        alert(response.responseText);
                    }
                }

            });
        }
        else {
            alert("Please select slum to sync.")
        }
    });


    function add_search_box() {
        $('#example tfoot tr').empty();

        var visible_indices = $('#example').DataTable().columns(':visible')[0];//indices of visible columns
        var numCols = $('#example').DataTable().columns(':visible').nodes().length;
        var append_this = '<tfoot><tr>';
        for (i = 0; i < numCols; i++) {
            append_this = append_this + '<th></th>';
        }
        append_this = append_this + '</tr></tfoot>';
        $('#example').each(function () {
            $(this).append(append_this);
        });
        $('#example tfoot th').each(function (index, element) {
            var title = $(this).text();
            something = $(this).parent().parent().parent();
            title = (something.find('thead tr th:eq(' + index + ')')[0].innerText);
            $(this).html('<input id = "search_box" dt_index = ' + visible_indices[index] + '  type="text" placeholder="Search ' + title + '" />');
        });


    }

});

