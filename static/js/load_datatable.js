
var columns_defs;
var table = null;
$(document).ready(function() {



    console.log("loading table...");
    var csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;

    $.ajax({
            url:"http://127.0.0.1:8000/mastersheet/columns",
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
        }
        else{

            table = $("#example").DataTable( {
            "columnDefs": [
                            { "defaultContent": "-", "targets": "_all" } ,
                            {"footer":true},
                            {
                                "targets": [ 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36 ],
                                "visible": false,
                            },
                          ],

            "dom":"Bfrtip",
            "ajax" :  {

                            url : "http://127.0.0.1:8000/mastersheet/list/show/",
                            dataSrc:"",
                            data:{'form':$("#slum_form").serialize() , 'csrfmiddlewaretoken':csrf_token},
                            contentType : "application/json",

                      },

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
                                                            url: "http://127.0.0.1:8000/mastersheet/buttons",
                                                            type: "GET",
                                                            dataType : "json",
                                                            data : "",
                                                            contentType : "application/json",
                                                            success : function(data){
                                                                            var show_them = [];
                                                                            console.log(data['accounts']);
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
                                                            url: "http://127.0.0.1:8000/mastersheet/buttons",
                                                            type: "GET",
                                                            dataType : "json",
                                                            data : "",
                                                            contentType : "application/json",
                                                            success : function(data){
                                                                            var show_them = [];
                                                                            console.log(data['accounts']);
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
                                        console.log($.fn.dataTable.isDataTable("#example"));
                                        //table.ajax.reload();
                                        load_data_datatable();

                                }

                            }

                      ],

            "columns": columns_defs,
            });



            highlight_buttons();
            add_search_box();
            $( table.table().container() ).on( 'keyup', 'tfoot tr th input', function (index,element) {

            table.column($(this).parent().index()).search( this.value ).draw();

            } );
            table.draw();
        }

    }
    $("#btnFetch").click(function(){
        load_data_datatable();
    });

});