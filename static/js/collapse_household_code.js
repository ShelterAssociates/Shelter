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
            var data = "";
            var flag = false;
            $.each($("td.field-household_code"), function(index, element){
                   var element_text = $(element).find('textArea')
                   var d = element_text.val();
                   var duplicate = check_for_duplicate(element_text);
                   if (duplicate.length > 0){
                    flag=true;
                   }
                   if (d != "")
                   {
                        data += d.slice(d.indexOf('[')+1, d.indexOf(']')) + ',';
                   }
           });
            $("textArea[name=household_code]").val("["+data.slice(0,data.length-1)+"]");
            if (flag){
             return false;
            }
        });
    }
//Checking for duplicate values within the list.
//    function check_for_duplicate(element){
//       var d = $(element).val();
//       var data = null;
//       var duplicate = []
//       if (d != "")
//       {
//         data = d.slice(d.indexOf('[')+1, d.indexOf(']'));
//         data = data.split(',')
//         house = household.slice(household.indexOf('[')+1, household.indexOf(']'));
//         house = house.replace(' ','').split(',')
//         $.each(data, function(index, val){
//            val = val.replace('\n','').replace(' ', '');
//            if (val in house){
//                duplicate.append(val);
//            }
//         });
//       }
//       return duplicate;
//    }
//    $("td.field-household_code").on('blur','textArea',function(element){
//       var duplicate = check_for_duplicate($($(element)[0].target));
//       if (duplicate.length > 0)
//       {
//        alert("The households "+duplicate.join(',') + " are duplicated.");
//       }
//
//    });

});
