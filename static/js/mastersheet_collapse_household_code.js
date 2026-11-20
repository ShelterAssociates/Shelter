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
                houses = $(house).text();
                $(house).empty().append(
                    $("<div class='lesslist' style='display:none;'>").text(houses).append("&nbsp;&nbsp;<b><a onclick='less_click(this);'>Less</a></b>"),
                    $("<div class='morelist'>").text(houses.split(',').splice(0,10).join() + " ...").append("<b><a onclick='more_click(this);'>More</a></b>")
                );
            });
        }
    }
    update_view();
});