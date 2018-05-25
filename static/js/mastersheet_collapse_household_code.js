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
            $.each($('.field-household_number'), function(index, house){
                houses = $(house).html();
                $(house).html("<div class='lesslist' style='display:none;'>"+houses+"&nbsp;&nbsp;<b><a onclick='less_click(this);'>Less</a></b></div>");
                $(house).append("<div class='morelist'>"+houses.split(',').splice(0,10).join()+" ...<b><a onclick='more_click(this);'>More</a></b></div>");
            });
        }
    }
    update_view();
});