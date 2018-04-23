/*
*  Script for sponsor project household details expand to see all the household numbers.
*  Used only in the list view of sponsor project details
*/


function more_click(element){
    $(element).parent().parent().hide();
    $(element).parent().parent().parent().find('div.lesslist').show();
}
function less_click(element){
    $(element).parent().parent().hide();
    $(element).parent().parent().parent().find('div.morelist').show();
}
$(document).ready(function(){
    //Used for the list view for household codes
    function update_view(){
        if($('#result_list').length > 0){
            $.each($('.field-household_code'), function(index, house){
                houses = $(house).html();
                $(house).html("<div class='lesslist' style='display:none;'>"+houses+"&nbsp;&nbsp;<b><a onclick='less_click(this);'>Less</a></b></div>");
                $(house).append("<div class='morelist'>"+houses.split(',').splice(0,10).join()+" ...<b><a onclick='more_click(this);'>More</a></b></div>");
            });
        }
    }
    update_view();

    //Used for add/edit for sponsor project details page
    if ($("#id_sponsor option:selected").text() != "SBM Toilets" && $("#id_sponsor").val() != ""){
        $("textArea[name=household_code], div.field-household_code p.help").addClass('hide');
        var household = $("textArea[name=household_code]").val();
        $("textArea[name=household_code]").parent().append('<p class="householdcode">'+household+'</p>');
        $("input[name=_save]").click(function(){
            var data = [];
            $.each($("td.field-household_code"), function(index, element){
                var element_text = $(element).find('textArea')
                var d = eval(element_text.val());
                //var dup = check_for_duplicate(element_text);
                if (d!= undefined && d!="" && d.length>0){
                    data = data.concat(d);
                }
           });
           data.sort();
            $("textArea[name=household_code]").val("["+data.join(', ')+"]");
            $("textArea[name=household_code]").parent().find('p.householdcode').html('['+data.join(', ')+']');
            return false;
        });
    }
//Checking for duplicate values within the list.
    function check_for_duplicate(element){
       var check_houses = eval($(element).val());
       var duplicate = []
       if (check_houses.length > 0)
       {

         $.each($("td.field-household_code").find("textArea.vLargeTextField"), function(index, elem){
            var houses = eval($(elem).val());
            if(houses!=undefined && houses!="" && houses.length>0){
                duplicate[index]=[]
                if($(elem).attr('id')!=$(element).attr('id')){
                    $.each(check_houses, function(ind,val){

                        if (houses.indexOf(val)>-1){
                            duplicate[index].push(val);
                        }
                    });
                }
                else{
                    $.each(check_houses, function(ind,val){
                        var occurance =  houses.filter(function(elem){
                                return elem == val;
                              }).length;
                        if (occurance > 1){
                            duplicate[index].push(val);
                        }
                    });
                }
            }
         });
       }
       return duplicate;
    }
//    $("td.field-household_code").on('blur','textArea',function(element){
//       var duplicate = check_for_duplicate($($(element)[0].target));
//       if (duplicate.length > 0)
//       {
//        alert("The households "+duplicate.join(',') + " are duplicated.");
//       }
//
//    });
//$(document).on('blur','textArea.vLargeTextField',function(element){
//   var d = check_for_duplicate($(this));
//   var disp_msg = "";
//   $.each(d, function(i,v){
//       if(v.join(',') != ""){
//           v = $.grep(v, function(el, index) {
//                return index == $.inArray(el, v);
//            });
//            disp_msg += v.join(',')+" already present in record -";
//            disp_msg +=  (i+1) + '\n';
//        }
//   });
//   if(disp_msg){
//   alert("Below are the duplicate numbers :\n"+disp_msg);
//    }
// });
});
