$(document).ready(function(){
    modal_upload = `
    <style>
        #loading-img {
        background: url(/static/images/spinner.gif) center center no-repeat;
        height: 100%;
        width: 100%;
        z-index: 20;
        }

        .display_line{
            display: inline-block;
        }
        .error_display{

            overflow-y:scroll;height:150px;
        }
        .overlay {
            background: #e9e9e9;
            display: none;
            position: fixed;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            opacity: 0.5;
            z-index: 2000;
        }
    </style>
    <div class="overlay">
        <div id="loading-img"></div>
    </div>
    <div class="modal fade" id="kmlModal" tabindex="-1" role="dialog" aria-labelledby="kmlModalLabel">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
            <h4 class="modal-title" id="kmlModalLabel">Upload KML file</h4>
          </div>
          <form id="upload_file" method = "POST" enctype="multipart/form-data" action="">
          <div id = "upload_file_field" class="modal-body">
                <input type="hidden" id="fieldURL"/>
                <input name="file" class="button" type="file">
                <p class="help">supports .kml file.</p>
                <div>
                <input name="chkdelete" class="button" type="checkbox">Do you want to delete the records before uploading?</input>
                </div>
          </div>
          <div id = "success_log">

          </div>
          <div id = "error_log" >
            <!--
                The error msg for the file upload modal is to be displayed in the modal
                instead of alert
            -->
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
            <button id = "btn_upload_file" type="button" class="btn btn-primary">Upload</button>
          </div>
          </form>
        </div>
      </div>
    </div>`;
    $('body').append(modal_upload);


    $("button[data-target='#kmlModal']").click(function(){
        $("input[name=file]").val('');
        $("input[name=chkdelete]")[0].checked = false;
        $("#kmlModal").modal('show');
        $("#kmlModalLabel").html("Upload "+$(this).html()+" KML file")
        $("#fieldURL").val($(this).attr('href'));
        $("input[name=chkdelete]").parent().show();
        if ($(this).html() == "Slum" || $(this).html() == "City")
        {
            $("input[name=chkdelete]").parent().hide();
        }
    });

    $("#btn_upload_file").click(function(){
        var input = $("#upload_file")[0];
        var formData = new FormData(input);
        formData.append('chk_delete',$("input[name=chkdelete]").is(":checked"));
        if(typeof input[1].files[0] == 'undefined' ){
            alert("No file selected. Please select a file.");
        }
        else{
            var fname = input[1].files[0].name;
            var re = /(\.kml)$/i;

            if(!re.exec(fname)){
                alert("File extension not supported!");
            }
            else{
                var csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;
                formData.append('csrfmiddlewaretoken',csrf_token);
                $(".overlay").show();
                $.ajax({
                    url:$("#fieldURL").val(),
                    data:formData,
                    type:"post",
                    dataType: 'json',
                    processData: false,
                    contentType: false,
                    success:function(response){
                        $(".overlay").hide();
                        if (response.message != ""){
                            if (response.status == true){
                                alert("SUCCESS : \n"+response.message);
                            }
                            else{
                                alert("ERROR : \n"+response.message);
                            }
                        }
                    },
                    error:function(){
                        $(".overlay").hide();
                        if(resp.responseText!=""){
                            alert(resp.responseText);
                        }
                    },
                });
            }
        }
    });

});