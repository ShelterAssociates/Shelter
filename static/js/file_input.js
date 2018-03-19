/*$(document).ready(function(){

    $("#file_input").click(function(){
        var file = $('#file_input')[0].files;
        console.log(file);

        var fd = new FormData();
        fd.append('username', 'pyaar ek dokha hai');
        $.ajax({
            type : "POST",
            url : "http://127.0.0.1:8000/mastersheet/files/",
            data : fd,
            processData: false,
            contentType: false,
            success: function(){
                console.log("in ajax...");
            }

        });
    });
});*/