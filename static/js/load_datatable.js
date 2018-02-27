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

                                    var table = $("#example").DataTable( {
                                    "columnDefs": [ { "defaultContent": "-", "targets": "_all" } , {"footer":true}],
                                    "paging": false,

                                    "dom":"Bfrtip",
                                    "ajax" :  {
                                                    url : "http://127.0.0.1:8000/mastersheet/list/show/",
                                                    dataSrc:"",
                                                    contentType : "application/json",

                                              },

                                    "buttons":

                                              [

                                                     {
                                                        extend: 'excelHtml5',
                                                        text: 'Save current page',
                                                        exportOptions: {
                                                             columns: ':visible'
                                                        }
                                                    },
                                                    {

                                                        text: 'RHS',
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
                                                        action:function(){

                                                                var table = $('#example').DataTable();
                                                                table.columns().visible(true);
                                                                var show_them = [19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40];
                                                                table.columns().visible(false);
                                                                table.columns(show_them).visible(true);
                                                                table.columns(0).visible(true);
                                                                add_search_box();
                                                        }
                                                    },
                                                    {
                                                        text: 'Family Factsheet',
                                                        action:function(){

                                                                var table = $('#example').DataTable();
                                                                table.columns().visible(true);
                                                                var show_them = [41,42,43,44,45];
                                                                table.columns().visible(false);
                                                                table.columns(show_them).visible(true);
                                                                table.columns(0).visible(true);
                                                                add_search_box();
                                                        }
                                                    },
                                                    {
                                                        text: 'Daily Reporting',
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
                                                                                                    for ( i = 57; i < (57 + data['daily_reporting']); i++){
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
                                                                                                    for ( i = (57 + data['daily_reporting']); i < (57 + data['daily_reporting'] + data['accounts']); i++){
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
                                                        action:function(){

                                                                var table = $('#example').DataTable();
                                                                table.columns().visible(true);
                                                                var show_them = [46,47,48];
                                                                table.columns().visible(false);
                                                                table.columns(show_them).visible(true);
                                                                table.columns(0).visible(true);
                                                                add_search_box();
                                                        }
                                                    },
                                                    {
                                                        text: 'Show all',
                                                        action:function(){
                                                                var table = $('#example').DataTable();
                                                                table.columns().visible(true);
                                                                add_search_box();
                                                        }

                                                    }

                                              ],

                                    "columns": data
                                    });


                                    add_search_box();
                                    $( table.table().container() ).on( 'keyup', 'tfoot tr th input', function (index,element) {

                                    table.column($(this).parent().index()).search( this.value ).draw();

                                    } );
                             }
            });
        });