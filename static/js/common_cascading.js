
function cityList(){
  $('#id_City').empty();
  var str='<option value="';
  str = str +'"'+'>' + "--Please select--" + '</option>';
  $('#id_City').append(str);
    $.ajax({
        url : city_url,
        //data : {},
        type: "GET",
        contenttype : "json",
        success : function(json){

            for (i = 0; i < json.nameArray.length; i++){
              $('#id_City').append($('<option>').val(json.idArray[i]).text(json.nameArray[i]));
           }
        },
        sync:false
    });
}

function administrativewardList(){
    $('#id_AdministrativeWard').empty();
    var str='<option value="';
    str = str +'"'+'>' + "--Please select--" + '</option>';
    $('#id_AdministrativeWard').append(str);
    var cityname = $("#id_City option:selected").text();
    var id = $("#id_City option:selected").val();
    $.ajax({
        url : administrative_url,
        data : { id : id},
        type: "POST",
        contenttype : "json",
        success : function(json){
        for (i = 0; i < json.nameArray.length; i++){
                $('#id_AdministrativeWard').append($('<option>').val(json.idArray[i]).text(json.nameArray[i]));
            }
        },
        async:false
    });
}

function electoralWardList(){
    $('#id_ElectoralWard').empty();
    var str='<option value="';
      str = str +'"'+'>' + "--Please select--" + '</option>';
    $('#id_ElectoralWard').append(str);
    var Administrativewardname = $("#id_AdministrativeWard option:selected").text();
    var id = $("#id_AdministrativeWard option:selected").val();

    $.ajax({
        url : electoral_url,
        data : { id : id},
        type: "POST",
        contenttype : "json",
        success : function(json){
        for (i = 0; i < json.nameArray.length; i++) {
            $('#id_ElectoralWard').append($('<option>').val(json.idArray[i]).text(json.nameArray[i]));
        }
        },
        async:false
    });
}
function slumList(){
    $('#id_slum_name').empty();
    var str='<option value="';
    str = str +'"'+'>' + "--Please select--" + '</option>';
    $('#id_slum_name').append(str);
    var Administrativewardname = $("#id_ElectoralWard option:selected").text();
    var id = $("#id_ElectoralWard option:selected").val();

    $.ajax({
        url : slum_url,
        data : { id : id},
        type: "POST",
        contenttype : "json",
        success : function(json){
        for (i = 0; i < json.nameArray.length; i++) {
            $('#id_slum_name').append($('<option>').val(json.idArray[i]).text(json.nameArray[i]));
            }
        },
        async:false
    });

}

$(document).ready(function(){

	 $("#AdministrativeWards").hide();
   $("#ElectoralWards").hide();
   $("#Slums").hide();

	 slumid=$('#id_slum_name').val();
   if(slumid)
   {
       $("#AdministrativeWards").show();
   	   $("#ElectoralWards").show();
       $("#Slums").show();
    }
    flag=false;
    $("#id_level").on('change', function(){
         $("#AdministrativeWards").hide();
            $("#ElectoralWards").hide();
            $("#Slums").hide();
        selection = $(this).val();
        flag=false;
        $("#id_City").val("");
        if(selection=="Slum"){
            flag=true;
        }
    });


    $("#id_City").on('change',function()
    {
        if(flag){
            $("#AdministrativeWards").show();
            $("#ElectoralWards").hide();
            $("#Slums").hide();
            administrativewardList();
       	}
    });

    $("#id_AdministrativeWard").on('change',function()
    {
        if(flag){
        $("#ElectoralWards").show();
        $("#Slums").hide();
        electoralWardList();
        }
    });

    $("#id_ElectoralWard").on('change',function()
    {
        if(flag){
        $("#Slums").show();
         slumList();
         }
    });

});
