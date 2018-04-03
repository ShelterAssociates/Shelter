
var columns_defs;
var table = null;
var divider = 1000 * 60 * 60 * 24;
var window = 8 * 1000 * 60 * 60 * 24;

var today = Date.now();




$(document).ready(function() {



   console.log("loading table...");
    var csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;

    $.ajax({
            url:"/mastersheet/columns",
            type : "GET",
            dataType : "json",
            data : "",
            contentType : "application/json",
            success : function (data) {
                            columns_defs = data;
                     }
    });

    function load_data_datatable(){

        if (table != null){
        table.ajax.reload();
        flag_dates();

        }
        else{


            table = $("#example").DataTable( {


            "dom":"Bfrtip",
            "ajax" :  {

                            url : "/mastersheet/list/show/",
                            dataSrc:"",
                            data:{'form':$("#slum_form").serialize() , 'csrfmiddlewaretoken':csrf_token},
                            contentType : "application/json",
                            complete: function(){
                                if(table.page.info().recordsDisplay != 0){
                                    flag_dates();
                                }
                            }

                      },
            "columnDefs": [
                            {   "defaultContent": "-",
                                "targets": "_all",

                            } ,
                            {"footer":true},
                            {
                                "targets": [ 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36 ],
                                "visible": false,
                            },

                          ],

            "buttons":

                      [

                             {
                                extend: 'excelHtml5',
                                className : 'btn',

                                text: 'Save current page',
                                exportOptions: {
                                     columns: ':visible'
                                }
                            },
                            {

                                text: 'RHS',
                                className : 'btn',

                                action:function(){

                                        var table = $('#example').DataTable();
                                        table.columns().visible(true);
                                        var show_them = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]
                                        table.columns().visible(false);
                                        table.columns(show_them).visible(true);
                                        table.columns(0).visible(true);

                                        add_search_box();
                                }
                            },
                            {
                                text: 'Follow-up Survey',
                                className : 'btn',
                                action:function(){

                                        var table = $('#example').DataTable();
                                        table.columns().visible(true);
                                        var show_them = [19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36];
                                        table.columns().visible(false);
                                        table.columns(show_them).visible(true);
                                        table.columns(0).visible(true);

                                        add_search_box();
                                }
                            },
                            {
                                text: 'Family Factsheet',
                                className : 'btn',
                                action:function(){

                                        var table = $('#example').DataTable();
                                        table.columns().visible(true);
                                        var show_them = [37,38,39,40,41];
                                        table.columns().visible(false);
                                        table.columns(show_them).visible(true);
                                        table.columns(0).visible(true);
                                        add_search_box();
                                }
                            },
                            {
                                text: 'Daily Reporting',
                                className : 'btn',
                                action:function(){
                                                    $.ajax({
                                                            url: "/mastersheet/buttons",
                                                            type: "GET",
                                                            dataType : "json",
                                                            data : "",
                                                            contentType : "application/json",
                                                            success : function(data){
                                                                            var show_them = [];
                                                                            //console.log(data['accounts']);
                                                                            for ( i = 53; i < (53 + data['daily_reporting']); i++){
                                                                                show_them.push(i);
                                                                            }
                                                                            var table = $('#example').DataTable();
                                                                            table.columns().visible(false);
                                                                            table.columns(show_them).visible(true);
                                                                            table.columns(0).visible(true);
                                                                            add_search_box();
                                                                 }
                                                          });
                                                    }
                            },
                            {
                                text: 'Accounts',
                                className : 'btn',
                                action:function(){
                                                    $.ajax({
                                                            url: "/mastersheet/buttons",
                                                            type: "GET",
                                                            dataType : "json",
                                                            data : "",
                                                            contentType : "application/json",
                                                            success : function(data){
                                                                            var show_them = [];
                                                                            //console.log(data['accounts']);
                                                                            for ( i = (53 + data['daily_reporting']); i < (53 + data['daily_reporting'] + data['accounts']); i++){
                                                                                show_them.push(i);
                                                                            }
                                                                            var table = $('#example').DataTable();
                                                                            table.columns().visible(false);
                                                                            table.columns(show_them).visible(true);
                                                                            table.columns(0).visible(true);
                                                                            add_search_box();
                                                                 }
                                                          });
                                                    }
                            },
                            {
                                text: 'SBM',
                                className : 'btn',
                                action:function(){

                                        var table = $('#example').DataTable();
                                        table.columns().visible(true);
                                        var show_them = [42,43,44];
                                        table.columns().visible(false);
                                        table.columns(show_them).visible(true);
                                        table.columns(0).visible(true);
                                        add_search_box();
                                }
                            },
                            {
                                text: 'Show all',
                                className : 'btn active',
                                action:function(){
                                        var table = $('#example').DataTable();
                                        var hide_them = [ 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36 ];


                                        table.columns().visible(true);
                                        table.columns(hide_them).visible(false);

                                        add_search_box();
                                }

                            },
                            {
                                text: 'Refresh',
                                className : 'refresh',
                                action:function(){
                                        var is_table_init = $.fn.dataTable.isDataTable("#example");
                                        load_data_datatable();

                                }

                            }

                      ],

            "columns": columns_defs,
            });


            //flag_dates();
            highlight_buttons();
            add_search_box();
            $( table.table().container() ).on( 'keyup', 'tfoot tr th input', function (index,element) {

            table.column($(this).parent().index()).search( this.value ).draw();

            } );
            table.draw();

            $('#example').on( 'click', 'tbody td', function () {
                var data = table.cell( this ).render( 'sort' );
            } );


            $('#example tbody').on( 'click', 'tr', function () {
                $(this).toggleClass('selected');
            });
            $('#delete_selected').click( function () {


                var count = table.rows('.selected').data().length;
                if (count == 0){
                    alert("You have not selected any record. Please select a record to delete.");
                }
                else{
                    var records = [];
                    for( i = 0; i < count; i++){
                        records[i] = (table.rows('.selected').data()[i]['_id']);
                    }

                   //console.log(records.length);
                    if(records.length == 1){
                        var result = confirm("Are you sure? You have selected " + records.length + " record to delete.");
                    }
                    else{
                        var result = confirm("Are you sure? You have selected " + records.length + " records to delete.");
                    }
                    if(result){
                        $.ajax({
                            type : "post",
                            url : "/mastersheet/delete_selected/",

                            data : JSON.stringify({"records": records}),
                            contentType : "json",
                            success: function(response){
                                alert(response.response);
                                //console.log(response);
                                //console.log(som);
                                //alert(response['response']);

                            }

                        });
                    }
                }
            });
        }

    }

    function add_hyperlink(){
        //console.log("in add_hyperlink...");
    }

    function select_rows(){
        //console.log("we are called...");
        $('#example tbody').on( 'click', 'tr', function () {
            $(this).toggleClass('selected');
            //console.log(this);
        });
    }

    $("#btnFetch").click(function(){
        load_data_datatable();
    });
    function flag_dates(){

        if( table != null){

            var data = table.rows().data();
            data.each(function (value, index) {



                var p1 = new Date(Date.parse(value['phase_one_material_date_str'], "yyyy-mm-dd HH:mm:ss"));
                var p2 = new Date(Date.parse(value['phase_two_material_date_str'], "yyyy-mm-dd HH:mm:ss"));
                var p3 = new Date(Date.parse(value['phase_three_material_date_str'], "yyyy-mm-dd HH:mm:ss"));
                var a_d =  new Date(Date.parse(value['agreement_date_str'], "yyyy-mm-dd HH:mm:ss"));
                var s_t_d = new Date(Date.parse(value['septic_tank_date_str'], "yyyy-mm-dd HH:mm:ss"))
                var c_d = new Date(Date.parse(value['completion_date_str'], "yyyy-mm-dd HH:mm:ss"));


                var ind = value['Household_number'] % 10;
                if (a_d != null){

                    if ( value['phase_one_material_date_str'] == null && Math.floor((today - a_d) / divider) > 8 ){
                        table.on("draw.dt", function(){
                            $('tr:eq('+ind+')').css('background-color', '#f9a4a4');
                        });
                    }
                    if ( value['phase_two_material_date_str'] == null && Math.floor((today - p1) / divider) > 8 ){
                        table.on("draw.dt", function(){
                            $('tr:eq('+ind+')').css('background-color', '#f2f29f');
                        });
                    }
                    if (value['phase_three_material_date_str'] == null && Math.floor((today - p2) / divider) > 8 ){
                        table.on("draw.dt", function(){
                            $('tr:eq('+ind+')').css('background-color', '#aaf9a4');
                        });
                    }
                    if (value['completion_date_str'] == null && Math.floor((today - p3) / divider) > 8 ){
                        table.on("draw.dt", function(){
                            $('tr:eq('+ind+')').css('background-color', '#aaa4f4');
                        });
                    }
                    /*if (value['phase_one_material_date_str'] - value['agreement_date_str'] > 8){

                    }*/
                }
                else{
                   console.log("agreement not done");
                }


            });

        }
        else{
           console.log("table is null");
        }


    }

    $("#btnSync").click(function(){
        let slum = $("#slum_form").find('input[type=text]').val();
        if (slum!=""){
        $.ajax({
            type : "get",
            url : "/mastersheet/sync/slum/"+slum,
            contentType : "json",
            success: function(response){
                alert(response.msg);
            }

        });
        }
        else{
            alert("Please select slum to sync.")
        }
    });

});

