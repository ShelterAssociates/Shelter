var columns_defs;
var table = null;
var divider = 1000 * 60 * 60 * 24;
var window = 8 * 1000 * 60 * 60 * 24;
var current_slum;

var today = Date.now();
var daily_reporting_columns = [];


$(document).ready(function() {

    $("#add_table_btn").hide();
    var btn_default=[
                        {
                            extend: 'excel',
                            text: 'Excel(Flagged records)',
                            exportOptions: {
                                rows:".redColor"
                            }
                        },
                        {
                            extend : 'excel',
                            text : 'Excel(ALL)'
                        }

                    ];
    if($("#export_mastersheet").val()=="False"){
        btn_default=[];
    }
    var csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;

    $.ajax({
            url:"/mastersheet/columns",
            type : "GET",
            dataType : "json",
            data : "",
            contentType : "application/json",
            success : function (data,type,row,meta) {
                columns_defs = data;

                // Adding hyperlinks to RHS data
                var tmp_RHS = columns_defs['buttons']['RHS'];
                for (i = 0 ; i < tmp_RHS.length ; i ++ ){
                    columns_defs['data'][tmp_RHS[i]]['render']= function ( data, type, row,meta ) {
                        if(typeof data != 'undefined') {
                            url_RHS = row['rhs_url']
                            if(type === 'display'){
                                        data = '<a href = "#" onclick="window.open(\''+url_RHS+'\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            return data;
                        }
                    }
                }

                // Adding family factsheet photo download URLs
                var tmp_download_TF = columns_defs['buttons']['Family factsheet'];
                for (i = 0 ; i < tmp_download_TF.length ; i ++ ){

                        //Toilet photo
                        columns_defs['data'][43]['render']= function ( data, type, row,meta ) {
                            if(typeof data != 'undefined'){
                                url_download_TF = row['toilet_photo_url'];
                                if(type === 'display'){
                                            data = '<a target="_blank" href = " '+url_download_TF+'" >Download Photo</a>';

                                }
                                return data;
                            }
                        }
                    
                    //Family photo
                        columns_defs['data'][42]['render']= function ( data, type, row,meta ) {
                            if(typeof data != 'undefined'){
                                url_download_FF = row['family_photo_url'];
                                if(type === 'display'){
                                            data = '<a target="_blank" href = "'+url_download_FF+'" >Download Photo</a>';

                                }
                                return data;
                            }
                        }
                }

                
                

                // Adding hyperlinks to community mobilization data
                var tmp_DR = columns_defs['buttons']['Community Mobilization'];
                for (i = 0 ; i < tmp_DR.length ; i ++ ){
                    columns_defs['data'][tmp_DR[i]]['render']= function ( data, type, row,meta ) {
                        if(typeof data != 'undefined') {
                            url_daily_reporting = String("/admin/master/mastersheet/communitymobilization/") + row[columns_defs['data'][meta.col]['title']+"_id"] + String("/");
                            if(type === 'display'){
                                        data = '<a href = "#" onclick="window.open(\''+url_daily_reporting+'\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";
                            }
                            return data;
                        }
                    }
                }

                // Adding hyperlinks to accounts data
                var tmp_ACC = columns_defs['buttons']['Accounts'];
                for (i = 0 ; i < tmp_ACC.length ; i ++ ){
                    columns_defs['data'][tmp_ACC[i]]['render']= function ( data, type, row,meta ) {
                        if(typeof data != 'undefined'){
                            url_accounts = String("/admin/master/mastersheet/vendorhouseholdinvoicedetail/") + row[columns_defs['data'][meta.col]['title']+"_id"] + String("/");
                            if(type === 'display'){
                                        data = '<a href = "#" onclick="window.open(\''+url_accounts+'\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";

                            }
                            return data;
                        }
                    }
                }

                // Adding hyperlinks to SBM data
                var tmp_SBM = columns_defs['buttons']['SBM'];
                
                for (i = 0 ; i < tmp_SBM.length ; i ++ ){
                    columns_defs['data'][tmp_SBM[i]]['render']= function ( data, type, row,meta ) {
                        if(typeof data != 'undefined'){
                            url_SBM = String("/admin/master/mastersheet/sbmupload/") + row['sbm_id_'+String(row.Household_number)] + String("/");
                            if(type === 'display'){
                                        data = '<a href = "#" onclick="window.open(\''+url_SBM+'\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";

                            }
                            return data;
                        }
                    }
                    columns_defs['data'][0]['render']= function ( data, type, row,meta ) {
                        if(typeof data != 'undefined'){
                            url_SBM = String("/admin/master/mastersheet/sbmupload/") + row['sbm_id_'+String(row.Household_number)] + String("/");
                            if(type === 'display'){
                                        data = '<a href = "#" onclick="window.open(\''+url_SBM+'\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";

                            }
                            return data;
                        }
                    }
                }

                

                // Adding hyperlinks to Toilet Construction data
                var tmp_TC = columns_defs['buttons']['Construction status'];
                for (i = 0 ; i < tmp_TC.length ; i ++ ){
		if (columns_defs['data'][tmp_TC[i]]['data']!= "Funder"){
                    columns_defs['data'][tmp_TC[i]]['render']= function ( data, type, row,meta ) {
                        if(typeof data != 'undefined'){
                            url_TC = String("/admin/master/mastersheet/toiletconstruction/") + row['tc_id_'+String(row.Household_number)] + String("/");
                            if(type === 'display'){
                                        data = '<a href = "#" onclick="window.open(\''+url_TC+'\', \'_blank\', \'width=850,height=750\');">' + data + "</a>";

                            }
                            return data;
                        }
                    }
	         }
                }
            }
    });
    $("#buttons").on("click","button",function(){

        $(this).toggleClass("active");
        flag = false;
        if ($(this).hasClass("active"))
        {
            flag = true;
        }
        section = $(this).attr('value');
        col = columns_defs['buttons'][section];
        table.columns(col).visible( flag );
        add_search_box();
    });
    $("#upload_file_1").on("click", function(){

        $(".overlay").show();
        var input = $("#upload_file")[0];
        var formData = new FormData(input);

        if(typeof input[1].files[0] == 'undefined' ){
            alert("No file selected. Please select a file.");
        }
        else{
            var fname = input[1].files[0].name;
            var re = /(\.xls|\.xlsx)$/i;

            if(!re.exec(fname)){
                alert("File extension not supported!");
            }
            else{
                $.ajax({
                        type : "post",
                        url : "/mastersheet/files/",
                        data :formData ,
                        dataType: 'json',
                        contentType : false,
                        processData: false,
                        success: function(response){
                            var total_updates = 0;
                            var total_new = 0;
                            
                            
                            jQuery.each(response, function (index, value) {

                                try{
                                    if( index.indexOf("updated") != -1)
                                    {
                                        total_updates = total_updates + value.length;
                                        
                                    }
                                }
                                catch(error)
                                {
                                    total_updates = 0;
                                }
                                try
                                {
                                    if( index.indexOf("newly") != -1)
                                    {
                                        total_new = total_new + value.length;
                                    }
                                 
                                }
                                catch(error)
                                {
                                    total_new = 0;
                                }
                                try
                                { 
                                    if(index.indexOf("error") != -1)   
                                    {
                                        var error_log = document.createElement('div');      
                                        error_log.innerHTML = "<p>" +index+": "+String(value)+"[ total:"+value.length+" ]</p>";
                                        $("#error_log").append(error_log);
                                        $('#error_log').addClass('error_display');
                                        $('#error_log').addClass('alert alert-danger');
                                    }
                                }
                                catch(error)
                                {

                                }

                                
                            });
                            var success_log = document.createElement('div');
                            success_log.innerHTML = "<p>Number of records in the uploaded sheet: "+response.total_records+ "<br>Total records updated: " + total_updates +"<br>Number of new records added: " +total_new+ "</p>";
                            $("#success_log").append(success_log);
                            
                            $('#success_log').addClass('alert alert-success');
                        },
                        complete:function(){
                            $(".overlay").hide();
                        },
                        error:function(response){
                            $(".overlay").hide();
                            if (response.responseText!=""){
                                alert(response.responseText);
                            }
                        }
                });
            }
        }
    });
    

    // Clearing modal after it is closed
    $("#btnUpload").on("click", function(){
        
        $('#myModal').on('hidden.bs.modal', function() {
            $(this).find("#error_log").html("");
            $(this).find("#error_log").remove();
            $(this).find("#success_log").html("");
            $(this).find("#success_log").remove();
            $("#upload_file")[0].reset();
        });
     });
    


    function load_data_datatable(){
        if (table != null )
        {
            $("#slum_form p").find("#slum_info").html("");
            $("#slum_form p").find("#slum_info").remove();
            $(".overlay").show();
            table.ajax.reload();
        }
        else
        {
                
                $(".overlay").show();
                $("#legend").show();
                buttons = '<div class="btn-group">';
                $.each(columns_defs['buttons'],function(index, button){
                    buttons += '<button type="button" class="active btn btn-default" value="'+index+'" id="'+index.replace(/ /g,'')+'">'+index+'</button>';
                });
                buttons += '</div>';
                $("#buttons").append(buttons);


                table = $("#example").DataTable( {
                //dom: 'Bfrtip',
                    "processing": true,
                    "sDom": '<"top"Bfl>r<"mid"t><"bottom"ip><"clear">',
                    "ajax" :  {
                                    url : "/mastersheet/list/show/",
                                    dataSrc:"",
                                    data: function(){

                                        return {'form':$("#slum_form").serialize() , 'csrfmiddlewaretoken':csrf_token}
                                        // NOTE : We could have assigned the variable itself to the 'data' attribute, instead
                                        // of writing  function. That method promotes the errorneous behaviour. The code would have been
                                        // unable to update the 'data' attribute on the call of 'table.ajax.reload()'. 
                                    },
                                    contentType : "application/json",
                                    complete: function(data){
                                        // Displaying the electoral ward and name of the slum besides the look-up box
                                        if (data.responseJSON != 'undefined'){
                                            var slum_info = document.createElement('div');
                                            slum_info.classList.add("display_line");
                                            slum_info.setAttribute("id" , "slum_info");
                                            slum_info.innerHTML = "<p>"+data.responseJSON[data.responseJSON.length-1]["Name of the slum"]+", "+data.responseJSON[data.responseJSON.length-1]["Electoral Ward"] +"</p>"; 
                                            //console.log(data.responseJSON[data.responseJSON.length-1]);
                                            $("#slum_form p").append(slum_info);
                                        }
                                        $(".overlay").hide();   
                                    },
                              },
                   
                    "columnDefs": [
                                    {   "defaultContent": "-",
                                        "targets": "_all",

                                    } ,
                                    {"footer":true},

                                  ],

                    "buttons":btn_default,

                    "columns": columns_defs['data'],
                    "fixedColumns":{
                                    leftColumns: 1,
                                    
                                },
                    "scrollCollapse": true,
                });



                $( table.table().container() ).on( 'keyup ','tfoot tr th input',function (index, element){
                    table.column($(this).attr('dt_index')).search( String(this.value) ).draw();
    
                } );

                

                
                $('#example').on("draw.dt", function(){
                    flag_dates();
                });


                
                //prints the data in the cell when we click it. USED FOR DEBUGGING!!
                /*$('#example').on( 'click', 'tbody td', function () {
                    var data = table.cell( this ).render( 'sort' );
                   
                } );*/


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

                        if(records.length == 1){
                            var result = confirm("Are you sure? You have selected " + records.length + " record to delete.");
                        }
                        else{
                            var result = confirm("Are you sure? You have selected " + records.length + " records to delete.");
                        }
                        if(result){
                            $(".overlay").show();
                            $.ajax({
                                type : "post",
                                url : "/mastersheet/delete_selected/",

                                data : JSON.stringify({"records": records, "slum":document.forms[0].slumname.value}),
                                contentType : "json",
                                success: function(data, textStatus, xhr){
                                    $(".overlay").hide();
                                    if (response.response != ""){
                                        alert(response.response);
                                        $("#btnFetch").click();
                                    }
                                },
                                error: function(resp){
                                    $(".overlay").hide();
                                    if(resp.responseText!=""){
                                        alert(resp.responseText);
                                    }
                                }

                            });
                        }
                    }
                });

                $.each(columns_defs['buttons'], function(key,val){
                    html_table = $("#example");
                    html_table.find("thead>tr>th:eq(0)").addClass("trFirst");
                    html_table.find("thead>tr>th:eq("+val.slice(0,1)[0]+")").addClass("trFirst");
                    $.each(val.slice(1,val.length-1),function(k,v){
                        html_table.find("thead>tr>th:eq("+v+")").addClass("trMiddle");
                        
                    });
                    $.each(val.slice(0,val.length),function(k,v){
                        if (String(key) === "RHS"){
                                html_table.find("thead>tr>th:eq("+v+")").css('background-color', '#d6d0dd');//
                                //background-color: lightblue;
                                //$("#" + key).css('background-color', '#ccc0d9');

                            }
                        if (String(key) === "Follow-up"){
                                html_table.find("thead>tr>th:eq("+v+")").css('background-color', '#ffe0f5');//
                                //$("#" + key).css('background-color', '#ccc0d9');
                            }
                        if (String(key) === "Family factsheet"){
                                html_table.find("thead>tr>th:eq("+v+")").css('background-color', '#e0f6ff');//
                                //$("#" + key.replace(/ /g,'')).css('background-color', '#c4bd97');
                                
                            }
                        if (String(key) === "SBM"){
                                html_table.find("thead>tr>th:eq("+v+")").css('background-color', '#fed9a6');//
                                //$("#" + key).css('background-color', '#fbd4b4');
                            }
                        if (String(key) === "Construction status"){
                                html_table.find("thead>tr>th:eq("+v+")").css('background-color', '#d2e2ce');//
                                //$("#" + key.replace(/ /g,'')).css('background-color', '#c4bd97');
                            } 
                        if (String(key) === "Community Mobilization"){
                                html_table.find("thead>tr>th:eq("+v+")").css('background-color', '#e5d8bd');//
                                //$("#" + key.replace(/ /g,'')).css('background-color', '#b8cce4');
                            }
                        if (String(key) === "Accounts"){
                                html_table.find("thead>tr>th:eq("+v+")").css('background-color', '#ffffb3');//
                                //$("#" + key).css('background-color', '#d8d8d8');
                            }

                    });
                    html_table.find("thead>tr>th:eq("+val.slice(val.length-1)[0]+")").addClass("trLast");
                });

                $("#buttons button")[0].click();
                $("#buttons button")[1].click();
                $("#buttons button")[2].click();
                $("#add_table_btn").show();
                //For excel button alignment.
                $("div.dt-buttons>button").addClass("pull-left");
            }


    }

    function select_rows(){
        $('#example tbody').on( 'click', 'tr', function () {
            $(this).toggleClass('selected');
        });
    }

    $("#btnFetch").click(function(){
        if(document.forms[0].slumname.value == ""){
            alert("Please select a slum");
        }
        else{
            load_data_datatable();
        }

    });

   

    function trim_space(str){
        if(str != null)
        {
            return str.trim();
        }
        else{
            return str;

        }
    }


    function flag_dates(){



        if( table != null){
            
            var data = table.rows({ page: 'current' }).data();
            var counter = 0;
            var selected_col = $("#example thead tr th:contains('Final Status')").index();
            var selected_col_agreement_date = $("#example thead tr th:contains('Date of Agreement')").index();
            var selected_col_p1 = $("#example thead tr th:contains('Date of first phase material')").index();
            var selected_col_p2 = $("#example thead tr th:contains('Date of second phase material')").index();
            var selected_col_p3 = $("#example thead tr th:contains('Date of third phase material')").index();
            var selected_col_c = $("#example thead tr th:contains('Construction Completion Date')").index();
            data.each(function (value, index) {
                counter = counter + 1;
                index = index+1;



                var ind = value['Household_number'] % 10;
                if(ind == 0){ind = 10;}


                if ( value['agreement_date_str'] != null && value['status'] != 'Agreement cancel'){

                    if ( value['phase_one_material_date_str'] == null && Math.floor((today - Date.parse(trim_space(value['agreement_date_str']))) / divider) > 8 ){
                            $('tr:eq('+index+')').find('td:eq('+selected_col+')').css('background-color', '#f9a4a4');//red
                            $('tr:eq('+index+')').addClass('redColor');

                    }
                    else if ( value['phase_two_material_date_str'] == null && Math.floor((today - Date.parse(trim_space(value['phase_one_material_date_str']))) / divider) > 8 ){
                            $('tr:eq('+index+')').find('td:eq('+selected_col+')').css('background-color', '#f2f29f');//yellow
                            $('tr:eq('+index+')').addClass('redColor');

                    }
                    else if (value['phase_three_material_date_str'] == null && Math.floor((today - Date.parse(trim_space(value['phase_two_material_date_str']))) / divider) > 8 ){
                            $('tr:eq('+index+')').find('td:eq('+selected_col+')').css('background-color', '#aaf9a4');//green
                            $('tr:eq('+index+')').addClass('redColor');

                    }
                    else if (value['completion_date_str'] == null){
                            if (Math.floor((Date.parse(trim_space(value['phase_one_material_date_str'])) - Date.parse(trim_space(value['phase_three_material_date_str']))) / divider) == 0){
                                if (Math.floor((today - Date.parse(trim_space(value['phase_two_material_date_str']))) / divider) > 8 ){
                                    $('tr:eq('+index+')').find('td:eq('+selected_col+')').css('background-color', '#aaa4f4');//blue
                                    $('tr:eq('+index+')').addClass('redColor');
                                }
                            }
                            else if(Math.floor((today - Date.parse(trim_space(value['phase_three_material_date_str']))) / divider) > 8 ){
                                $('tr:eq('+index+')').find('td:eq('+selected_col+')').css('background-color', '#aaa4f4');//blue
                                $('tr:eq('+index+')').addClass('redColor');
                            }
                    }
                    
                }
                //date ambiguity to be resolved
                /*if ( (value['agreement_date_str'] == null && value['phase_one_material_date_str'] != null)
                     || 
                     (value['phase_two_material_date_str'] != null && (value['phase_one_material_date_str'] == null ||                                              value['agreement_date_str'] == null) 
                     )
                     ||
                     (value['completion_date_str'] != null && (value['agreement_date_str'] == null ||
                                                                value['phase_one_material_date_str'] == null ||
                                                                value['phase_two_material_date_str'] == null ||
                                                                value['phase_three_material_date_str'] == null

                                                                    )
                     )
                   )
                {
                        $('tr:eq('+index+')').find('td:eq('+selected_col+')').css('background-color', '#c6c6c6')
                }*/
                if (value['status'] != 'Agreement cancel')
                {
                    
                    if ( value['phase_one_material_date_str'] != null && value['agreement_date_str'] == null )
                    {
                        $('tr:eq('+index+')').find('td:eq('+selected_col_agreement_date+')').css('background-color', '#c6c6c6');
                    }
                    if (value['phase_two_material_date_str'] != null)
                    {
                        if(value['phase_one_material_date_str'] == null)
                        {
                           $('tr:eq('+index+')').find('td:eq('+selected_col_p1+')').css('background-color', '#c6c6c6'); 
                        }
                        if(value['agreement_date_str'] == null)
                        {
                            $('tr:eq('+index+')').find('td:eq('+selected_col_agreement_date+')').css('background-color', '#c6c6c6'); 
                        }
                    }
                    if (value['completion_date_str'] != null)
                    {
                        if(value['phase_three_material_date_str'] == null)
                        {
                           $('tr:eq('+index+')').find('td:eq('+selected_col_p3+')').css('background-color', '#c6c6c6'); 
                        }
                        if(value['phase_two_material_date_str'] == null)
                        {
                           $('tr:eq('+index+')').find('td:eq('+selected_col_p2+')').css('background-color', '#c6c6c6'); 
                        }
                        if(value['phase_one_material_date_str'] == null)
                        {
                           $('tr:eq('+index+')').find('td:eq('+selected_col_p1+')').css('background-color', '#c6c6c6'); 
                        }
                        if(value['agreement_date_str'] == null)
                        {
                            $('tr:eq('+index+')').find('td:eq('+selected_col_agreement_date+')').css('background-color', '#c6c6c6'); 
                        }

                    }
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
        $(".overlay").show();
        $.ajax({
            type : "get",
            url : "/mastersheet/sync/slum/"+slum,
            contentType : "json",
            success: function(response){
                $(".overlay").hide();
                if (response.msg!=""){
                alert(response.msg);
                }
            },
            error : function(response){
                $(".overlay").hide();
                if (response.responseText!=""){
                    alert(response.responseText);
                }
            }

        });
        }
        else{
            alert("Please select slum to sync.")
        }
    });


    function add_search_box(){
        $('#example tfoot tr').empty();

        var visible_indices = $('#example').DataTable().columns(':visible')[0];//indices of visible columns
        var numCols = $('#example').DataTable().columns(':visible').nodes().length;
        var append_this = '<tfoot><tr>';
        for(i = 0; i < numCols; i++){
            append_this = append_this + '<th></th>';
        }
        append_this = append_this + '</tr></tfoot>';
        $('#example').each(function(){
            $(this).append(append_this);
        });
        $('#example tfoot th').each( function (index,element) {
            var title = $(this).text()  ;
            something = $(this).parent().parent().parent();
            title=(something.find('thead tr th:eq('+index+')')[0].innerText);
            $(this).html( '<input id = "search_box" dt_index = '+visible_indices[index]+'  type="text" placeholder="Search '+title+'" />' );
        } );


    }

});

