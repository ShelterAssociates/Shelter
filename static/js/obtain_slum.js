$(document).ready(function(){



                $("#btnFetch").click(function(){
                    var form = $("#slum_form").serialize();

                    var csrf_token = document.getElementsByName("csrfmiddlewaretoken")[0].value;
                    $.ajax({
                            type:"POST",
                            url:"http://127.0.0.1:8000/mastersheet/list/show/",
                            data:{'form':form , 'csrfmiddlewaretoken':csrf_token},
                            dataType: "json",

                    });
                });
            });