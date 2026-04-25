$(document).ready(function(){
    if(window.location !== window.parent.location) {
        $('#navbar').hide();
    }

    function formatNumber(value) {
        var number = parseInt(value, 10);
        if (isNaN(number)) {
            return '0';
        }
        return number.toLocaleString('en-IN');
    }

    function add_cards(name, data){
        var card = $("div[name=section_card_clone]")[0].outerHTML;
        card = $(card).attr('name','card').removeClass('hide');
        card.find(".city_name")[0].innerHTML = name;
        card.find(".number-of-slums")[0].innerHTML = formatNumber(data['slum_count']) + " / " + formatNumber(data['total_slum_count']);
        card.find(".household-count")[0].innerHTML = formatNumber(data['household_count__sum']);
        card.find('.dashboard-url')[0].href = "/dashboard/"+ data['city_id'];
        card.find('.gis-url')[0].href = "/"+data['city_id'];
        $(".city-cards-list").append(card);
    }


    $.ajax({
       url : "/graphs/card/all/",
        type : "GET",
        contenttype : "json",
        success : function(json) {
          $.each(json['city'], function(key, value){
              if(value['household_count__sum'] > 0){
                add_cards(key, value);
              }
          });
          populate_top_bar(json['city']);
        },
    });
});
