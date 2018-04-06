function add_search_box(){

                $("#example").on("draw.dt", function(){
                    console.log("in search box...");
                    $('#example tfoot tr').empty();
                    var numCols = table.columns(':visible').count()//$('#example thead th').length;
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
                        $(this).html( '<input type="text" placeholder="Search '+title+'" />' );
                    } );
                });

            }